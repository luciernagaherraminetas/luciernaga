import face_recognition
import os
import json

BASE_PATH = "/var/www/maraton_fotos/backend/static/fotos_evento"
ROSTROS_PATH = "/var/www/maraton_fotos/backend/data/rostros/rostros.json"

rostros = []

for root, dirs, files in os.walk(BASE_PATH):
    for f in files:

        if not f.lower().endswith((".jpg",".jpeg",".png")):
            continue

        ruta = os.path.join(root,f)

        try:

            img = face_recognition.load_image_file(ruta)

            encodings = face_recognition.face_encodings(img)

            for e in encodings:

                rostros.append({
                    "foto": f,
                    "descriptor": e.tolist()
                })

        except:
            continue

with open(ROSTROS_PATH,"w") as f:
    json.dump(rostros,f)

print("Indexado terminado:",len(rostros),"rostros")
