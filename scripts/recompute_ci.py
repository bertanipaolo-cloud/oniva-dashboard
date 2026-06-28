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

    # Banner dates: contracts + bank only (leave cashflow date frozen).
    def mtime(p):
        import datetime
        return datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%d.%m.%Y")

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
    # CF block is intentionally left untouched (frozen).

    # Update only the contracts + bank banner dates.
    import re
    out = re.sub(r"(Contratti agg\. <b>)[^<]*(</b>)",
                 lambda m: m.group(1) + mtime(contracts) + m.group(2), out)
    out = re.sub(r"(Saldi bancari agg\. <b>)[^<]*(</b>)",
                 lambda m: m.group(1) + mtime(bank_f) + m.group(2), out)

    with open(HTML, "w", encoding="utf-8") as fh:
        fh.write(out)

    # NOTE: we update ONLY oniva_dashboard.html (the file served by Pages).
    # The repo's index.html is a separate landing/portal page and is left alone.

    print(f"\nUpdated (RAW + BANK): {HTML}")
    print(f"  viaggi total: {sum(raw['viaggi'])}  | bank totale: {bank['totale']}")
    print("  cashflow (CF): FROZEN — left unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
