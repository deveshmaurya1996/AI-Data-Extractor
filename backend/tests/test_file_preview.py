import io

import pytest
from fastapi import UploadFile

from services.file_preview import build_upload_preview, parse_file_bytes


def test_parse_csv_basic():
    raw = b"name,score\nAlice,10\nBob,20\n"
    out = parse_file_bytes("data.csv", raw)
    assert out is not None
    assert out["row_count"] == 2
    assert out["columns"] == ["name", "score"]
    assert out["rows"][0]["name"] == "Alice"


def test_parse_json_list():
    raw = b'[{"a":1},{"a":2}]'
    out = parse_file_bytes("x.json", raw)
    assert out is not None
    assert out["row_count"] == 2
    assert out["rows"][0]["a"] == 1


def test_parse_unsupported():
    assert parse_file_bytes("f.bin", b"abc") is None


@pytest.mark.asyncio
async def test_build_upload_preview_csv():
    buf = io.BytesIO(b"k,v\n1,a\n2,b\n")
    up = UploadFile(file=buf, filename="t.csv")
    parsed, errors, combined = await build_upload_preview([up], "")
    assert not errors
    assert len(parsed) == 1
    assert parsed[0]["file"] == "t.csv"
    assert parsed[0]["row_count"] == 2
    assert len(parsed[0]["rows"]) == 2
    assert len(combined) >= 1
    assert "__source_file" in combined[0]
