#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_sheets.py
===============
Exports the two live Google Sheets (contracts + bank) to .xlsx files so the
recompute step can read them. Runs on the GitHub Actions runner (which has
internet + Google API access).

Auth: a Google service-account JSON, provided via the GOOGLE_SA_KEY env var
(the whole JSON as a string — store it as a GitHub Actions secret). The two
sheets must be SHARED (at least "Viewer") with the service-account email.

Output: writes the .xlsx files into $ONIVA_SRC (default: current dir) using the
exact filenames the recompute glob patterns expect.
"""

import os
import io
import sys
import json

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# --- The live Google Sheets to export (stable IDs) --------------------------
SHEETS = {
    # file_id : output filename (must match recompute_dashboard glob patterns)
    "1QxLKtHmJxgCBJI6GxwCVHB2bwslo4mIbsKz9C7zicPc":
        "ELENCO CONTRATTI ONIVA' - DAL 2021.xlsx",
    "1PVKOJ7O0HAnszn42fkFQnCsfqHh2xHbYdQo25zQc0qM":
        "DATI BANCARI_Amministrazione.xlsx",
}

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def creds_from_env():
    raw = os.environ.get("GOOGLE_SA_KEY")
    if not raw:
        sys.exit("ERROR: GOOGLE_SA_KEY env var is empty.")
    try:
        info = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: GOOGLE_SA_KEY is not valid JSON: {e}")
    return Credentials.from_service_account_info(info, scopes=SCOPES)


def export_sheet(service, file_id, out_path):
    request = service.files().export_media(fileId=file_id, mimeType=XLSX_MIME)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    data = buf.getvalue()
    if len(data) < 5000:
        sys.exit(f"ERROR: export of {file_id} is suspiciously small "
                 f"({len(data)} bytes) — check sharing/permissions.")
    with open(out_path, "wb") as fh:
        fh.write(data)
    print(f"  exported {os.path.basename(out_path)}  ({len(data):,} bytes)")


def sheet_modified_time(service, file_id):
    """Drive's own last-modified timestamp (RFC3339, UTC) for the file.

    Used for the dashboard's "Saldi bancari agg." date: the "SALDO al" cell
    inside the bank sheet is typed by hand and is often NOT updated when the
    balances are, so it understates how fresh the data really is.
    """
    try:
        info = service.files().get(fileId=file_id, fields="modifiedTime").execute()
        return info.get("modifiedTime")
    except Exception as exc:  # non-fatal: recompute falls back to the cell
        print(f"  WARN: could not read modifiedTime for {file_id}: {exc}")
        return None


def main():
    dest = os.environ.get("ONIVA_SRC", os.getcwd())
    os.makedirs(dest, exist_ok=True)
    service = build("drive", "v3", credentials=creds_from_env(), cache_discovery=False)
    print(f"Exporting {len(SHEETS)} sheets to {dest}")
    meta = {}
    for file_id, name in SHEETS.items():
        export_sheet(service, file_id, os.path.join(dest, name))
        meta[name] = sheet_modified_time(service, file_id)
    meta_path = os.path.join(dest, "sources_meta.json")
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    print(f"  wrote sources_meta.json -> {meta}")
    print("Done.")


if __name__ == "__main__":
    main()
