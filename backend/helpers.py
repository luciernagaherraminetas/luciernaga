import os
import json
from flask_mail import Message

from config import ALBUMS_JSON


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
    return "".join(
        c for c in slug.lower()
        if c.isalnum() or c in "-_"
    )


def allowed_file(filename):
    return filename.lower().endswith(
        (
            ".jpg",
            ".jpeg",
            ".png"
        )
    )


def enviar_correo(mail, app, destino, link):

    try:

        msg = Message(
            subject="Tus fotos están listas 📸",
            sender=app.config["MAIL_USERNAME"],
            recipients=[destino]
        )

        msg.body = f"""
📸 ¡Gracias por tu compra!

Descarga tus fotos aquí:

{link}

⏳ Disponible por 48 horas

Luciérnaga
"""

        mail.send(msg)

    except Exception as e:
        print("Error correo:", e)
