from flask import (
    Flask, render_template, request, jsonify,
    send_file, abort, session, redirect
)
from functools import wraps
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
import mercadopago
import os, time, secrets, io, zipfile, json, shutil, re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from PIL import Image
import pytesseract

Image.MAX_IMAGE_PIXELS = None

# ==========================
# ENV
# ==========================
load_dotenv("/var/www/maraton_fotos/backend/.env", override=True)

# ==========================
# APP
# ==========================
app = Flask(__name__)
app.secret_key = "luciernaga_super_secret_key"

@app.template_filter("datetimeformat")
def datetimeformat(value):
    try:
        return datetime.fromtimestamp(int(value)).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return value

# ==========================
# CONFIG
# ==========================
PRECIO_FOTO = 5.0
DESCARGA_HORAS = 48

BASE_ALBUMS_PATH = "/var/www/maraton_fotos/backend/static/fotos_evento"
ALBUMS_JSON = "/var/www/maraton_fotos/backend/data/albums.json"

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_PREVIEW_SIZE = 1600
WATERMARK_PATH = "/var/www/maraton_fotos/backend/static/watermark/logo.png"

# ==========================
# HELPERS
# ==========================
def load_albums():
    if not os.path.exists(ALBUMS_JSON):
        return {}
    with open(ALBUMS_JSON, "r") as f:
        return json.load(f)

def save_albums(data):
    with open(ALBUMS_JSON, "w") as f:
        json.dump(data, f, indent=2)

def sumar_venta_evento(slug, fotos_count):
    albums = load_albums()
    if slug not in albums:
        return
    albums[slug]["ventas"] = albums[slug].get("ventas", 0) + fotos_count * PRECIO_FOTO
    albums[slug]["fotos_vendidas"] = albums[slug].get("fotos_vendidas", 0) + fotos_count
    save_albums(albums)

def clean_slug(slug):
    return "".join(c for c in slug.lower() if c.isalnum() or c in "-_")

def allowed_file(name):
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ==========================
# OCR – DORSALES
# ==========================
def detectar_dorsales(path):
    try:
        img = Image.open(path)
        texto = pytesseract.image_to_string(img, config="--psm 6 digits")
        return list(set(re.findall(r"\b\d{1,4}\b", texto)))
    except Exception:
        return []

# ==========================
# BUSCAR POR DORSAL
# ==========================
@app.route("/buscar-dorsal/<dorsal>")
def buscar_dorsal(dorsal):
    albums = load_albums()
    activo = next((k for k,v in albums.items() if v.get("activo")), None)
    if not activo:
        return jsonify({"fotos": []})

    album_path = os.path.join(BASE_ALBUMS_PATH, activo, "originales")
    cache = load_dorsales_cache(activo)

    if dorsal in cache:
        return jsonify({"fotos": cache[dorsal]})

    fotos = []
    for f in os.listdir(album_path):
        path = os.path.join(album_path, f)
        dorsales = []
        for d in dorsales:
            cache.setdefault(d, []).append(f)
            if d == dorsal:
                fotos.append(f)

    save_dorsales_cache(activo, cache)
    return jsonify({"fotos": fotos})
# ==========================
# ADMIN LOGIN
# ==========================
ADMIN_USER = "luciernaga"
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")

def admin_required(f):
    @wraps(f)
    def wrapper(*a, **k):
        if not session.get("admin_logged"):
            return redirect("/admin/login")
        return f(*a, **k)
    return wrapper

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if (
            request.form.get("usuario") == ADMIN_USER
            and ADMIN_PASSWORD_HASH
            and check_password_hash(ADMIN_PASSWORD_HASH, request.form.get("password"))
        ):
            session.clear()
            session["admin_logged"] = True
            return redirect("/admin")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/admin/login")

@app.route("/admin")
@admin_required
def admin_dashboard():
    pagos = Pago.query.order_by(Pago.created_at.desc()).all()
    total_pagos = len(pagos)
    total_fotos = sum(len(p.fotos or []) for p in pagos)

    return render_template(
        "admin.html",
        pagos=pagos,
        total_pagos=total_pagos,
        total_fotos=total_fotos,
        precio=PRECIO_FOTO
    )

@app.route("/admin/albums")
@admin_required
def admin_albums():
    return render_template(
        "admin_albums_dashboard.html",
        albums=load_albums()
    )

@app.route("/admin/albums/new")
@admin_required
def admin_new_album():
    return render_template("admin_album_new.html")

# ==========================
# DATABASE
# ==========================
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Pago(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.String(64), unique=True)
    email = db.Column(db.String(255))
    fotos = db.Column(db.JSON)
    token = db.Column(db.String(64), unique=True)
    expira = db.Column(db.Integer)
    descargado = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.Integer, default=lambda: int(time.time()))

# ==========================
# MERCADO PAGO
# ==========================
sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

# ==========================
# WEBHOOK
# ==========================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}
    pid = data.get("resource") or data.get("data", {}).get("id")
    if not pid:
        return jsonify(ok=True)

    pid = str(pid)
    if Pago.query.filter_by(payment_id=pid).first():
        return jsonify(ok=True)

    info = sdk.payment().get(pid).get("response", {})
    if info.get("status") != "approved":
        return jsonify(ok=True)

    fotos = info.get("external_reference", "").split(",")
    pago = Pago(
        payment_id=pid,
        email=info.get("payer", {}).get("email"),
        fotos=fotos,
        token=secrets.token_urlsafe(32),
        expira=int((datetime.utcnow() + timedelta(hours=DESCARGA_HORAS)).timestamp())
    )
    db.session.add(pago)
    db.session.commit()

    albums = load_albums()
    activo = next((k for k, v in albums.items() if v.get("activo")), None)
    if activo:
        sumar_venta_evento(activo, len(fotos))

    return jsonify(ok=True)

# ==========================
# HOME
# ==========================
@app.route("/")
def index():
    albums = load_albums()
    activo = next((k for k, v in albums.items() if v.get("activo")), None)
    if not activo:
        return "⏳ Próximo evento"

    albums[activo]["vistas"] = albums[activo].get("vistas", 0) + 1
    save_albums(albums)

    preview = os.path.join(BASE_ALBUMS_PATH, activo, "preview")
    fotos = sorted(
        f for f in os.listdir(preview)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ) if os.path.exists(preview) else []

    return render_template(
        "index.html",
        fotos=fotos,
        evento={"carpeta": activo},
        precio=PRECIO_FOTO
    )
