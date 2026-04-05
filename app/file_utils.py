from fastapi import UploadFile


def decode_uploaded_gpx(upload: UploadFile, raw_bytes: bytes) -> str:
    if not upload.filename or not upload.filename.lower().endswith(".gpx"):
        raise ValueError("El archivo debe tener extensión .gpx")

    encodings_to_try = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]

    for encoding in encodings_to_try:
        try:
            text = raw_bytes.decode(encoding)
            if "<gpx" in text.lower():
                return text
        except UnicodeDecodeError:
            continue

    raise ValueError("No se pudo decodificar el archivo GPX. Revisa su codificación.")