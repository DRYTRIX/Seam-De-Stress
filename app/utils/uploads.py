import os
import uuid

from PIL import Image, ImageOps

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_DIMENSION = 1600
THUMBNAIL_SIZE = (400, 400)


def allowed_file(filename):
    return bool(filename) and "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_garment_photo(file_storage, garment_id, upload_folder):
    """Save an uploaded garment photo (re-orienting via EXIF, capped to a sane
    resolution) plus a thumbnail. Returns (filename, thumbnail_filename), both
    relative to ``upload_folder``."""
    subdir = os.path.join("garments", str(garment_id))
    abs_subdir = os.path.join(upload_folder, subdir)
    os.makedirs(abs_subdir, exist_ok=True)

    unique = uuid.uuid4().hex
    filename = f"{unique}.jpg"
    thumbnail_filename = f"{unique}_thumb.jpg"

    with Image.open(file_storage.stream) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")

        full = img.copy()
        full.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
        full.save(os.path.join(abs_subdir, filename), "JPEG", quality=88)

        thumb = img.copy()
        thumb.thumbnail(THUMBNAIL_SIZE)
        thumb.save(os.path.join(abs_subdir, thumbnail_filename), "JPEG", quality=82)

    return os.path.join(subdir, filename), os.path.join(subdir, thumbnail_filename)


def delete_garment_photo_files(photo, upload_folder):
    for rel_path in (photo.filename, photo.thumbnail_filename):
        abs_path = os.path.join(upload_folder, rel_path)
        if os.path.exists(abs_path):
            os.remove(abs_path)


LOGO_MAX_DIMENSION = 600


def save_logo(file_storage, upload_folder):
    """Save the shop logo as ``branding/logo.<ext>``, replacing any previous
    one. Keeps the original format (unlike garment photos) so a PNG logo's
    transparency survives for letterhead use."""
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    abs_subdir = os.path.join(upload_folder, "branding")
    os.makedirs(abs_subdir, exist_ok=True)

    for existing_ext in ALLOWED_EXTENSIONS:
        stale = os.path.join(abs_subdir, f"logo.{existing_ext}")
        if os.path.exists(stale):
            os.remove(stale)

    filename = f"logo.{ext}"
    abs_path = os.path.join(abs_subdir, filename)
    with Image.open(file_storage.stream) as img:
        img = ImageOps.exif_transpose(img)
        img.thumbnail((LOGO_MAX_DIMENSION, LOGO_MAX_DIMENSION))
        save_kwargs = {"quality": 90} if ext in ("jpg", "jpeg") else {}
        img.save(abs_path, **save_kwargs)

    return os.path.join("branding", filename)
