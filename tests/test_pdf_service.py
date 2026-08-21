import os

from app.services.pdf import file_data_uri


def test_file_data_uri_returns_none_for_empty_path(app):
    assert file_data_uri("/tmp", "") is None
    assert file_data_uri("/tmp", None) is None


def test_file_data_uri_returns_none_for_missing_file(app, tmp_path):
    assert file_data_uri(str(tmp_path), "does/not/exist.png") is None


def test_file_data_uri_encodes_existing_file_with_correct_mime(app, tmp_path):
    branding_dir = tmp_path / "branding"
    branding_dir.mkdir()
    logo_path = branding_dir / "logo.png"
    logo_path.write_bytes(b"\x89PNG\r\n\x1a\nfake-png-bytes")

    uri = file_data_uri(str(tmp_path), os.path.join("branding", "logo.png"))
    assert uri.startswith("data:image/png;base64,")


def test_file_data_uri_unknown_extension_falls_back_to_octet_stream(app, tmp_path):
    weird_path = tmp_path / "file.xyz"
    weird_path.write_bytes(b"data")

    uri = file_data_uri(str(tmp_path), "file.xyz")
    assert uri.startswith("data:application/octet-stream;base64,")
