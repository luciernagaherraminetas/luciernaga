import os

# ==========================
# FLASK
# ==========================

SECRET_KEY = "luciernaga_super_secret_key"

MAX_CONTENT_LENGTH = 15 * 1024 * 1024 * 1024

# ==========================
# MAIL
# ==========================

MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = "jmanuelphotographe@gmail.com"

# ==========================
# ALBUMS
# ==========================

BASE_ALBUMS_PATH = "/var/www/maraton_fotos/backend/static/fotos_evento"

ALBUMS_JSON = "/var/www/maraton_fotos/backend/data/albums.json"

ROSTROS_PATH = "/var/www/maraton_fotos/backend/data/rostros"

WATERMARK_PATH = "/var/www/maraton_fotos/backend/static/watermark/logo.png"

# ==========================
# IMAGES
# ==========================

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png"
}

MAX_PREVIEW_SIZE = 1600

# ==========================
# NEGOCIO
# ==========================

PRECIO_FOTO = 100.0

DESCARGA_HORAS = 48
