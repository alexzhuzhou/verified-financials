"""Upload-your-own-data flow: validation + compute equivalence."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

from verified_financials import datagen
from verified_financials.api.app import app
from verified_financials.loaders.validate import REQUIRED_FILES, validate_upload

client = TestClient(app)


def _baseline_files(tmp_path):
    """Generate the baseline CSVs and return them as multipart file tuples."""
    datagen.generate(data_dir=tmp_path, scenario="baseline")
    files = []
    for name in REQUIRED_FILES:
        data = (tmp_path / name).read_bytes()
        files.append(("files", (name, io.BytesIO(data), "text/csv")))
    return files


def test_validate_upload_missing_column(tmp_path):
    datagen.generate(data_dir=tmp_path, scenario="baseline")
    # corrupt one file by dropping the 90_plus column from the header
    ar = tmp_path / "ar_aging.csv"
    lines = ar.read_text().splitlines()
    lines[0] = lines[0].replace(",90_plus", "")
    ar.write_text("\n".join(lines) + "\n")
    errors = validate_upload(tmp_path)
    assert any("ar_aging.csv" in e and "90_plus" in e for e in errors)


def test_validate_upload_missing_file(tmp_path):
    datagen.generate(data_dir=tmp_path, scenario="baseline")
    (tmp_path / "inventory.csv").unlink()
    errors = validate_upload(tmp_path)
    assert any("inventory.csv" in e and "not found" in e for e in errors)


def test_upload_then_compute_reproduces_baseline(tmp_path):
    """Uploading the baseline CSVs must reproduce the built-in baseline numbers."""
    resp = client.post("/uploads", files=_baseline_files(tmp_path))
    assert resp.status_code == 200, resp.text
    upload_id = resp.json()["upload_id"]

    out = client.post("/compute", json={"upload_id": upload_id, "config_overrides": {}})
    assert out.status_code == 200, out.text
    body = out.json()
    assert body["borrowing_base"]["borrowing_base"] == "27327500.00"
    assert body["fccr"]["fccr"] == "1.20"


def test_upload_compute_with_overrides(tmp_path):
    upload_id = client.post("/uploads", files=_baseline_files(tmp_path)).json()["upload_id"]
    out = client.post(
        "/compute",
        json={
            "upload_id": upload_id,
            "config_overrides": {"borrowing_base": {"accounts_receivable": {"advance_rate": "0.90"}}},
        },
    )
    assert out.json()["borrowing_base"]["accounts_receivable"]["availability"] == "19935000.00"


def test_upload_facts_provenance(tmp_path):
    upload_id = client.post("/uploads", files=_baseline_files(tmp_path)).json()["upload_id"]
    facts = client.get("/facts", params={"upload_id": upload_id, "dataset": "ar_aging", "metric": "total"})
    names = {f["entity"] for f in facts.json()}
    assert "Lone Star Grocery Group" in names


def test_upload_rejects_unexpected_file(tmp_path):
    resp = client.post("/uploads", files=[("files", ("budget.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv"))])
    assert resp.status_code == 400


def test_template_download():
    resp = client.get("/templates/ar_aging.csv")
    assert resp.status_code == 200
    assert "90_plus" in resp.text.splitlines()[0]  # header has the expected columns
