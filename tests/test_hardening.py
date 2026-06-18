"""Demo-hardening at the API edge: bad data → friendly 4xx, never a raw 500."""

from __future__ import annotations

import io
import shutil

from fastapi.testclient import TestClient

from verified_financials import datagen
from verified_financials.api.app import app
from verified_financials.api.routes import UPLOADS_DIR
from verified_financials.loaders.validate import REQUIRED_FILES

client = TestClient(app)


def _files_from(dir_path):
    return [
        ("files", (name, io.BytesIO((dir_path / name).read_bytes()), "text/csv"))
        for name in REQUIRED_FILES
    ]


def test_uploads_rejects_bad_value(tmp_path):
    """A file with valid columns but a garbled value is rejected at upload time."""
    datagen.generate(data_dir=tmp_path, scenario="baseline")
    ar = tmp_path / "ar_aging.csv"
    ar.write_text(ar.read_text() + "BadCo,Foodservice,US,false,false,soon,0,0,0,0,0,0\n")

    resp = client.post("/uploads", files=_files_from(tmp_path))
    assert resp.status_code == 400, resp.text
    errors = resp.json()["detail"]["errors"]
    assert any("days_past_due" in e and "whole number" in e for e in errors), errors


def test_compute_bad_upload_returns_422(tmp_path):
    """If malformed data reaches compute (e.g. a hand-placed dir), it 422s — not 500."""
    upload_id = "test_bad_upload_dir"
    dest = UPLOADS_DIR / upload_id
    try:
        dest.mkdir(parents=True, exist_ok=True)
        datagen.generate(data_dir=dest, scenario="baseline")  # valid CSVs
        inv = dest / "inventory.csv"
        inv.write_text(inv.read_text() + "BadItem,Grocery,Dry,abc,10,false\n")

        out = client.post("/compute", json={"upload_id": upload_id, "config_overrides": {}})
        assert out.status_code == 422, out.text
        detail = out.json()["detail"]
        assert "inventory.csv" in detail and "abc" in detail, detail
    finally:
        shutil.rmtree(dest, ignore_errors=True)
