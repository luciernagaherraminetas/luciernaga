from flask import (
    Flask, render_template, request, jsonify,
    send_file, abort, session, redirect
)
from functools import wraps
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
import mercadopago
import os, time, secrets, zipfile, json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from PIL import Image
import io

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
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024 * 1024

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax"
)

@app.template_filter("datetimeformat")
def datetimeformat(value):
    try:
        return datetime.fromtimestamp(int(value)).strftime("%d/%m/%Y %H:%M")
    except:
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
    try:
        with open(ALBUMS_JSON, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_albums(data):
    os.makedirs(os.path.dirname(ALBUMS_JSON), exist_ok=True)
    tmp = ALBUMS_JSON + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, ALBUMS_JSON)

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
        if (
            request.form.get("usuario") == ADMIN_USER and
            check_password_hash(ADMIN_PASSWORD_HASH, request.form.get("password"))
        ):
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

@app.route("/crear-preferencia", methods=["POST"])
def crear_preferencia():
    data = request.json
    fotos = data.get("seleccionadas", [])
    email = data.get("email")

    if not fotos or not email:
        return jsonify(error="Datos incompletos"), 400

    preference = {
        "items": [{
            "title": "Fotos del evento",
            "quantity": len(fotos),
            "unit_price": PRECIO_FOTO
        }],
        "payer": {"email": email},
        "external_reference": ",".join(fotos),
        "back_urls": {
            "success": "/gracias",
            "failure": "/",
            "pending": "/"
        },
        "auto_return": "approved"
    }

    res = sdk.preference().create(preference)
    return jsonify(init_point=res["response"]["init_point"])

# ==========================
# ADMIN
# ==========================
@app.route("/admin")
@admin_required
def admin_dashboard():
    pagos = Pago.query.order_by(Pago.created_at.desc()).all()
    return render_template(
        "admin.html",
        pagos=pagos,
        total_pagos=len(pagos),
        total_fotos=sum(len(p.fotos or []) for p in pagos),
        precio=PRECIO_FOTO
    )

@app.route("/admin/zip/<token>")
@admin_required
def admin_zip(token):
    pago = Pago.query.filter_by(token=token).first_or_404()

    zip_buffer = io.BytesIO()
    found = False

    albums = load_albums()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for foto in pago.fotos:
            # buscar la foto en TODOS los álbumes
            for slug in albums.keys():
                path = os.path.join(
                    BASE_ALBUMS_PATH,
                    slug,
                    "originales",
                    foto
                )
                if os.path.exists(path):
                    zipf.write(path, arcname=foto)
                    found = True
                    break

    zip_buffer.seek(0)

    if not found:
        abort(404)

    pago.descargado = True
    db.session.commit()

    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="fotos.zip"
    )
# ==========================
# ALBUMS
# ==========================
@app.route("/admin/albums")
@admin_required
def admin_albums():
    return render_template("admin_albums_dashboard.html", albums=load_albums())

@app.route("/admin/albums/new")
@admin_required
def admin_new_album():
    return render_template("admin_album_new.html")

@app.route("/admin/albums/preview/<slug>")
@admin_required
def admin_album_preview(slug):
    preview_path = os.path.join(BASE_ALBUMS_PATH, slug, "preview")
    if not os.path.exists(preview_path):
        return redirect("/admin/albums")

    fotos = sorted(os.listdir(preview_path))
    return render_template(
        "admin_album_preview.html",
        fotos=fotos,
        carpeta=slug
    )

@app.route("/admin/albums/upload", methods=["POST"])
@admin_required
def upload_album():
    nombre = request.form.get("nombre")
    lugar = request.form.get("lugar")
    carpeta = clean_slug(request.form.get("carpeta"))
    zip_file = request.files.get("zip")

    if not nombre or not lugar or not carpeta or not zip_file:
        return ("", 204)

    albums = load_albums()
    if carpeta in albums:
        return ("", 204)

    albums[carpeta] = {
        "nombre": nombre,
        "lugar": lugar,
        "activo": False,
        "fotos": 0,
        "vistas": 0
    }
    save_albums(albums)

    album_path = os.path.join(BASE_ALBUMS_PATH, carpeta)
    originals = os.path.join(album_path, "originales")
    previews = os.path.join(album_path, "preview")

    os.makedirs(originals, exist_ok=True)
    os.makedirs(previews, exist_ok=True)

    temp_zip = f"/tmp/{secure_filename(zip_file.filename)}"
    zip_file.save(temp_zip)

    fotos_count = 0
    watermark = Image.open(WATERMARK_PATH).convert("RGBA")

    try:
        with zipfile.ZipFile(temp_zip, "r") as zip_ref:
            for member in zip_ref.infolist():
                if member.is_dir():
                    continue

                base = secure_filename(os.path.basename(member.filename))
                if not base or not allowed_file(base):
                    continue

                name, _ = os.path.splitext(base)
                filename = f"{name}_{fotos_count}.jpg"

                try:
                    with zip_ref.open(member) as file:
                        img = Image.open(file).convert("RGBA")

                        orig_path = os.path.join(originals, filename)
                        prev_path = os.path.join(previews, filename)

                        img.convert("RGB").save(orig_path, format="JPEG", quality=92)

                        img.thumbnail((MAX_PREVIEW_SIZE, MAX_PREVIEW_SIZE))
                        ratio = img.width * 0.30 / watermark.width
                        wm = watermark.resize(
                            (int(watermark.width * ratio),
                             int(watermark.height * ratio)),
                            Image.LANCZOS
                        )
                        pos = (
                            (img.width - wm.width) // 2,
                            (img.height - wm.height) // 2
                        )
                        img.alpha_composite(wm, pos)

                        img.convert("RGB").save(prev_path, format="JPEG", quality=82)

                        fotos_count += 1
                except:
                    continue
    finally:
        if os.path.exists(temp_zip):
            os.remove(temp_zip)

    albums = load_albums()
    albums[carpeta]["fotos"] = fotos_count
    save_albums(albums)

    return ("", 204)

@app.route("/admin/albums/toggle/<slug>")
@admin_required
def toggle_album(slug):
    albums = load_albums()
    if slug in albums:
        albums[slug]["activo"] = not albums[slug]["activo"]
        save_albums(albums)
    return redirect("/admin/albums")

@app.route("/admin/albums/delete/<slug>")
@admin_required
def delete_album(slug):
    albums = load_albums()
    if slug not in albums:
        return redirect("/admin/albums")

    album_path = os.path.join(BASE_ALBUMS_PATH, slug)
    if os.path.exists(album_path):
        for root, dirs, files in os.walk(album_path, topdown=False):
            for f in files:
                os.remove(os.path.join(root, f))
            for d in dirs:
                os.rmdir(os.path.join(root, d))
        os.rmdir(album_path)

    albums.pop(slug, None)
    save_albums(albums)

    return redirect("/admin/albums")

# ==========================
# HOME
# ==========================
@app.route("/")
def index():
    albums = load_albums()
    activo = next((k for k, v in albums.items() if v.get("activo")), None)

    if not activo:
        return "⏳ Próximo evento"

    # 🔥 CONTAR VISTA
    albums[activo]["vistas"] = albums[activo].get("vistas", 0) + 1
    save_albums(albums)

    preview = os.path.join(BASE_ALBUMS_PATH, activo, "preview")
    fotos = sorted(os.listdir(preview))

    return render_template(
        "index.html",
        fotos=fotos,
        evento={"carpeta": activo},
        precio=PRECIO_FOTO
    )

# 🔎 BUSCAR POR DORSAL
@app.route("/buscar-dorsal/<dorsal>")
def buscar_dorsal(dorsal):
    albums = load_albums()
    activo = next((k for k, v in albums.items() if v.get("activo")), None)
    if not activo:
        return jsonify(fotos=[])

    preview_path = os.path.join(BASE_ALBUMS_PATH, activo, "preview")
    if not os.path.exists(preview_path):
        return jsonify(fotos=[])

    fotos = [f for f in os.listdir(preview_path) if f.startswith(dorsal)]
    return jsonify(fotos=fotos)

@app.route("/gracias")
def gracias():
    token = request.args.get("token")
    pago = Pago.query.filter_by(token=token).first()
    return render_template("gracias.html", fotos=len(pago.fotos), token=token)
