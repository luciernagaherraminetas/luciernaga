from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os

SERVICE_ACCOUNT_FILE = "luciernaga-485607.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]

ROOT_FOLDER_NAME = "Luciernaga"

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)

def get_or_create_folder(service, name, parent=None):
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent:
        query += f" and '{parent}' in parents"

    results = service.files().list(q=query).execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder"
    }
    if parent:
        metadata["parents"] = [parent]

    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]

def subir_zip_a_drive(zip_path, event_name, payment_id):
    service = get_drive_service()

    root_id = get_or_create_folder(service, ROOT_FOLDER_NAME)
    eventos_id = get_or_create_folder(service, "eventos", root_id)
    evento_id = get_or_create_folder(service, event_name, eventos_id)

    file_metadata = {
        "name": f"pago_{payment_id}.zip",
        "parents": [evento_id]
    }

    media = MediaFileUpload(zip_path, mimetype="application/zip")

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink"
    ).execute()

    return file["id"], file["webViewLink"]

