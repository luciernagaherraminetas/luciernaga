from flask import (
    Flask, render_template, request, jsonify,
    send_file, abort, session, redirect, url_for
)
from functools import wraps
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
import mercadopago
import os
import time
import secrets
import io
import zipfile
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from PIL import Image

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
        return datetime.fromtimestamp(value).strftime("%d/%m/%Y %H:%M")
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

    albums[slug]["ventas"] = albums[slug].get("ventas", 0) + (fotos_count * PRECIO_FOTO)
    albums[slug]["fotos_vendidas"] = albums[slug].get("fotos_vendidas", 0) + fotos_count
    save_albums(albums)

def clean_slug(slug):
    return "".join(c for c in slug.lower() if c.isalnum() or c in "-_")

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ==========================
# ADMIN LOGIN
# ==========================
ADMIN_USER = "luciernaga"
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged"):
            return redirect("/admin/login")
        return f(*args, **kwargs)
    return wrapper

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        user = (request.form.get("usuario") or "").strip()
        password = request.form.get("password") or ""
        if user == ADMIN_USER and ADMIN_PASSWORD_HASH and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session.clear()
            session["admin_logged"] = True
            return redirect("/admin")
        error = "Credenciales incorrectas"
    return render_template("admin_login.html", error=error)

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/admin/login")

# ==========================
# DATABASE
# ==========================
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Pago(db.Model):
    __tablename__ = "pago"
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(255))
    fotos = db.Column(db.JSON)
    token = db.Column(db.String(64), unique=True)
    expira = db.Column(db.Integer)
    descargado = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.Integer)

    def __init__(self, payment_id, email, fotos, token, expira):
        self.payment_id = payment_id
        self.email = email
        self.fotos = fotos
        self.token = token
        self.expira = expira
        self.created_at = int(time.time())

# ==========================
# MERCADO PAGO
# ==========================
sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

# ==========================
# WEBHOOK (AQUÍ SE SUMAN LAS VENTAS)
# ==========================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}
    payment_id = None

    if "resource" in data and str(data["resource"]).isdigit():
        payment_id = data["resource"]
    elif "data" in data and "id" in data["data"]:
        payment_id = data["data"]["id"]

    if not payment_id:
        return jsonify({"ok": True}), 200

    payment_id = str(payment_id)

    if Pago.query.filter_by(payment_id=payment_id).first():
        return jsonify({"ok": True}), 200

    pago_mp = sdk.payment().get(payment_id)
    info = pago_mp.get("response", {})

    if info.get("status") != "approved":
        return jsonify({"ok": True}), 200

    fotos = info.get("external_reference", "").split(",")
    email = info.get("payer", {}).get("email")

    token = secrets.token_urlsafe(32)
    expira = int((datetime.utcnow() + timedelta(hours=DESCARGA_HORAS)).timestamp())

    pago = Pago(payment_id, email, fotos, token, expira)
    db.session.add(pago)
    db.session.commit()

    # 💰 SUMAR VENTA AL EVENTO ACTIVO
    albums = load_albums()
    activo = next((k for k, v in albums.items() if v.get("activo")), None)
    if activo:
        sumar_venta_evento(activo, len(fotos))

    return jsonify({"ok": True}), 200

# ==========================
# ADMIN DASHBOARD (PAGOS)
# ==========================
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

# ==========================
# ADMIN ÁLBUMES
# ==========================
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

@app.route("/admin/albums/upload", methods=["POST"])
@admin_required
def upload_album():
    nombre = request.form.get("nombre")
    lugar = request.form.get("lugar")
    carpeta = clean_slug(request.form.get("carpeta"))
    zip_file = request.files.get("zip")

    if not nombre or not lugar or not carpeta or not zip_file:
        return redirect("/admin/albums")

    album_path = os.path.join(BASE_ALBUMS_PATH, carpeta)
    originals = os.path.join(album_path, "originales")
    previews = os.path.join(album_path, "preview")

    if os.path.exists(album_path):
        return redirect("/admin/albums")

    os.makedirs(originals, exist_ok=True)
    os.makedirs(previews, exist_ok=True)

    temp_zip = f"/tmp/{secure_filename(zip_file.filename)}"
    zip_file.save(temp_zip)

    watermark = Image.open(WATERMARK_PATH).convert("RGBA")
    fotos_count = 0

    with zipfile.ZipFile(temp_zip, "r") as zip_ref:
        for file in zip_ref.namelist():
            if file.startswith("__MACOSX") or file.endswith("/"):
                continue

            filename = secure_filename(os.path.basename(file))
            if not allowed_file(filename):
                continue

            extracted = zip_ref.extract(file, "/tmp")
            img = Image.open(extracted).convert("RGB")

            img.save(os.path.join(originals, filename), quality=95)

            img.thumbnail((MAX_PREVIEW_SIZE, MAX_PREVIEW_SIZE))
            preview = img.convert("RGBA")

            wm = watermark.resize((preview.width // 3, preview.height // 3))
            pos = ((preview.width - wm.width)//2, (preview.height - wm.height)//2)
            preview.alpha_composite(wm, pos)

            preview.convert("RGB").save(
                os.path.join(previews, filename),
                quality=85
            )

            os.remove(extracted)
            fotos_count += 1

    os.remove(temp_zip)

    albums = load_albums()
    albums[carpeta] = {
        "nombre": nombre,
        "lugar": lugar,
        "activo": False,
        "fotos": fotos_count,
        "vistas": 0,
        "ventas": 0,
        "fotos_vendidas": 0,
        "created_at": int(time.time())
    }
    save_albums(albums)

    return redirect("/admin/albums")

@app.route("/admin/albums/toggle/<slug>")
@admin_required
def toggle_album(slug):
    albums = load_albums()
    if slug in albums:
        albums[slug]["activo"] = not albums[slug]["activo"]
        save_albums(albums)
    return redirect("/admin/albums")

import shutil

@app.route("/admin/albums/delete/<slug>")
@admin_required
def delete_album(slug):
    albums = load_albums()

    if slug not in albums:
        return redirect("/admin/albums")

    # 🗂 borrar carpeta física
    album_path = os.path.join(BASE_ALBUMS_PATH, slug)
    if os.path.exists(album_path):
        shutil.rmtree(album_path)

    # 🧾 borrar del JSON
    del albums[slug]
    save_albums(albums)

    return redirect("/admin/albums")

@app.route("/admin/albums/view/<slug>")
@admin_required
def admin_view_album(slug):
    albums = load_albums()
    if slug not in albums:
        return redirect("/admin/albums")

    preview_path = os.path.join(BASE_ALBUMS_PATH, slug, "preview")
    fotos = []

    if os.path.exists(preview_path):
        fotos = sorted(
            f for f in os.listdir(preview_path)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        )

    return render_template(
        "admin_album_view.html",
        album=albums[slug],
        slug=slug,
        fotos=fotos
    )

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
