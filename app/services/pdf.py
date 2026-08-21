import base64
import os

from flask import render_template
from weasyprint import HTML


def render_pdf(template_name, **context):
    html_string = render_template(template_name, **context)
    return HTML(string=html_string).write_pdf()


_MIME_BY_EXTENSION = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}


def file_data_uri(upload_folder, relative_path):
    if not relative_path:
        return None
    abs_path = os.path.join(upload_folder, relative_path)
    if not os.path.exists(abs_path):
        return None
    _, ext = os.path.splitext(relative_path)
    mime_type = _MIME_BY_EXTENSION.get(ext.lower(), "application/octet-stream")
    with open(abs_path, "rb") as handle:
        encoded = base64.b64encode(handle.read()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"
