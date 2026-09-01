#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
recompute_ci.py
===============
CI-friendly refresh of the Onivà dashboard. Updates ONLY the contracts (RAW)
and bank (BANK) data blocks, leaving the cashflow (CF) block FROZEN exactly as
it is in the current HTML (the cashflow source is not yet automatable).

Reads the two source spreadsheets (exported from the live Google Sheets by
fetch_sheets.py) from $ONIVA_SRC, and rewrites the dashboard HTML in place.

Env vars:
  ONIVA_SRC   folder containing the .xlsx sources and the dashboard HTML
              (default: current dir)
  ONIVA_HTML  path to the dashboard HTML to update in place
              (default: $ONIVA_SRC/oniva_dashboard.html)

Exit code 0 on success, non-zero if the contracts/bank data could not be
computed (so the GitHub Action fails loudly instead of publishing garbage).
"""

import os
import sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))

# Import the full recompute engine living next to this file.
_spec = importlib.util.spec_from_file_location(
    "recompute_dashboard", os.path.join(HERE, "recompute_dashboard.py"))
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)

SRC = os.environ.get("ONIVA_SRC", os.getcwd())
HTML = os.environ.get("ONIVA_HTML", os.path.join(SRC, "oniva_dashboard.html"))

# Point the engine's file discovery at our source folder.
R.SRC_DIR = SRC


def main():
    contracts = R.find_contracts()
    bank_f = R.find_bank()
    print("Sources:")
    print(f"  contracts: {os.path.basename(contracts)}")
    print(f"  bank     : {os.path.basename(bank_f)}")

    raw, keyed = R.compute_raw(contracts)
    bank = R.compute_bank(bank_f)
    analysis = R.compute_analysis(contracts)
    forecast = R.compute_forecast(contracts)

    # ---- Banner dates -----------------------------------------------------
    # Use the DATA's own as-of date, not the file timestamp:
    #   contracts -> most recent signing date found in the sheets
    #   bank      -> the "SALDO al" date written inside DATI BANCARI_CONTO
    # (cashflow is frozen, its date is left untouched)
    import datetime

    def mtime(p):
        return datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%d.%m.%Y")

    def fmt(d):
        return d.strftime("%d.%m.%Y")

    contracts_date = fmt(datetime.date.fromisoformat(forecast["asOf"])) if forecast else mtime(contracts)
    # Bank date: prefer Drive's own modifiedTime for the source sheet (written
    # by fetch_sheets.py into sources_meta.json). The "SALDO al" cell inside
    # DATI BANCARI_CONTO is typed by hand and is often NOT updated when the
    # balances are: on 01.09.2026 the amounts changed while the cell still read
    # 14.08.2026, making the dashboard look staler than it was. Drive's
    # timestamp cannot be forgotten. Fallbacks: the cell, then the file mtime.
    bank_date = None
    try:
        import json
        with open(os.path.join(SRC, "sources_meta.json"), encoding="utf-8") as fh:
            stamp = json.load(fh).get(os.path.basename(bank_f))
        if stamp:
            dt = datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            try:
                from zoneinfo import ZoneInfo
                dt = dt.astimezone(ZoneInfo("Europe/Rome"))
            except Exception:
                pass
            bank_date = fmt(dt.date())
            print(f"  bank date from Drive modifiedTime: {bank_date}")
    except Exception as exc:
        print(f"  (sources_meta.json unusable: {exc})")
    if not bank_date:
        try:
            bank_date = R.banner_dates(contracts, bank_f, bank_f)["bank"]
            print(f"  bank date from 'SALDO al' cell (fallback): {bank_date}")
        except Exception:
            bank_date = mtime(bank_f)
            print(f"  bank date from file mtime (last fallback): {bank_date}")

    html = open(HTML, encoding="utf-8").read()

    # Sanity: refuse to publish empty/degenerate data.
    if sum(raw["viaggi"]) < 100:
        print("ERROR: contracts total looks wrong (<100). Aborting.", file=sys.stderr)
        return 2
    if not bank.get("totale"):
        print("ERROR: bank total is empty. Aborting.", file=sys.stderr)
        return 2

    out = html
    out = R.replace_const(out, "RAW", R.serialize_raw(raw))
    out = R.replace_const(out, "BANK", R.serialize_bank(bank))
    if "const ANALYSIS" in out:
        out = R.replace_const(out, "ANALYSIS", R.serialize_analysis(analysis))
    if "const FORECAST" in out and forecast:
        out = R.replace_const(out, "FORECAST", R.serialize_forecast(forecast))
    # CF block is intentionally left untouched (frozen).

    # Update only the contracts + bank banner dates.
    import re
    out = re.sub(r"(Contratti agg\. <b>)[^<]*(</b>)",
                 lambda m: m.group(1) + contracts_date + m.group(2), out)
    out = re.sub(r"(Saldi bancari agg\. <b>)[^<]*(</b>)",
                 lambda m: m.group(1) + bank_date + m.group(2), out)

    with open(HTML, "w", encoding="utf-8") as fh:
        fh.write(out)

    # NOTE: we update ONLY oniva_dashboard.html (the file served by Pages).
    # The repo's index.html is a separate landing/portal page and is left alone.

    nan = sum(len(v) for v in analysis["firmato"].values())
    print(f"\nUpdated (RAW + BANK + ANALYSIS): {HTML}")
    print(f"  viaggi total: {sum(raw['viaggi'])}  | bank totale: {bank['totale']}")
    print(f"  analysis: firmato years {sorted(analysis['firmato'])} "
          f"({nan} year-dest cells)")
    print("  cashflow (CF): FROZEN — left unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
