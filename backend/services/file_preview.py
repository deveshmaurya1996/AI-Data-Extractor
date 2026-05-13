from __future__ import annotations

import csv
import io
import json
from typing import Any

from fastapi import UploadFile

from services.upload_persist import MAX_ROWS_PER_UPLOADED_FILE

PREVIEW_ROWS_PER_FILE = 20
COMBINED_PREVIEW_CAP = 100


def parse_file_bytes(filename: str, file_bytes: bytes) -> dict[str, Any] | None:

    name = filename.lower()

    if name.endswith((".csv", ".txt")):
        text = file_bytes.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        columns = list(reader.fieldnames or [])
        rows: list[dict[str, Any]] = []
        for row in reader:
            rows.append(
                {str(k): ("" if v is None else v) for k, v in row.items()}
            )
        return {"row_count": len(rows), "columns": columns, "rows": rows}

    if name.endswith((".xlsx", ".xls")):
        try:
            openpyxl = __import__("openpyxl")
        except Exception:
            return None
        wb = openpyxl.load_workbook(
            filename=io.BytesIO(file_bytes), read_only=True, data_only=True
        )
        sheet = wb.active
        it = sheet.iter_rows(values_only=True)
        headers_row = next(it, None)
        if headers_row is None:
            return {"row_count": 0, "columns": [], "rows": []}
        headers = [
            str(c).strip() if c not in (None, "") else f"column_{i + 1}"
            for i, c in enumerate(headers_row)
        ]
        rows = []
        for values in it:
            record: dict[str, Any] = {}
            for i, header in enumerate(headers):
                v = values[i] if i < len(values) else None
                record[header] = "" if v is None else v
            rows.append(record)
        return {"row_count": len(rows), "columns": headers, "rows": rows}

    if name.endswith(".json"):
        data = json.loads(file_bytes.decode("utf-8", errors="replace"))
        if isinstance(data, dict):
            for key in ("data", "rows", "items", "records"):
                if key in data and isinstance(data[key], list):
                    rows = [x for x in data[key] if isinstance(x, dict)]
                    cols = list(rows[0].keys()) if rows else []
                    return {"row_count": len(rows), "columns": cols, "rows": rows}
            row = {str(k): v for k, v in data.items()}
            return {"row_count": 1, "columns": list(row.keys()), "rows": [row]}
        if isinstance(data, list):
            rows = [x for x in data if isinstance(x, dict)]
            cols = list(rows[0].keys()) if rows else []
            return {"row_count": len(rows), "columns": cols, "rows": rows}

    return None


async def build_upload_preview(
    uploads: list[UploadFile],
    _user_query: str,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, Any]]]:

    parsed: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for upload in uploads:
        fname = upload.filename or "unknown"
        try:
            raw = await upload.read()
            if not raw:
                errors.append({"file": fname, "error": "File is empty"})
                continue
            result = parse_file_bytes(fname, raw)
            if result is None:
                errors.append({"file": fname, "error": "Unsupported file format"})
                continue

            all_rows: list[dict[str, Any]] = result["rows"]
            total = int(result["row_count"])
            capped = all_rows[:MAX_ROWS_PER_UPLOADED_FILE]
            preview = [
                {"__source_file": fname, **row}
                for row in all_rows[:PREVIEW_ROWS_PER_FILE]
            ]
            parsed.append(
                {
                    "file": fname,
                    "row_count": total,
                    "columns": result["columns"],
                    "rows": capped,
                    "preview": preview,
                }
            )
        except Exception as e:
            errors.append({"file": fname, "error": str(e)})

    combined: list[dict[str, Any]] = []
    for item in parsed:
        combined.extend(item["preview"])
    return parsed, errors, combined[:COMBINED_PREVIEW_CAP]
