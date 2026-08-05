#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tabify.py — restructure oniva_dashboard.html into 3 tabs
(Contratti / Cashflow / Banche) WITHOUT touching the RAW/CF/BANK const blocks
or the banner update dates (so the weekly recompute keeps working).

Idempotent: if the file is already tabbed (contains 'id="tab-contratti"'),
it does nothing.

Usage: python3 tabify.py path/to/oniva_dashboard.html
"""
import sys

TAB_CSS = """
/* ---- Tabs ---- */
.tabs { display:flex; gap:4px; margin-bottom:1.25rem; border-bottom:1px solid var(--oni-line); flex-wrap:wrap; }
.tab-btn { appearance:none; border:none; background:none; cursor:pointer; font-family:inherit; font-size:13px; font-weight:600; color:var(--oni-tx2); padding:10px 18px; border-bottom:2px solid transparent; margin-bottom:-1px; letter-spacing:.02em; transition:color .15s; }
.tab-btn:hover { color:var(--oni-ink); }
.tab-btn.active { color:var(--oni-ink); border-bottom-color:var(--oni-gold); }
.tab-panel { display:none; }
.tab-panel.active { display:block; }
"""

TAB_NAV = """<nav class="tabs">
  <button class="tab-btn active" data-tab="contratti" onclick="showTab('contratti')">Contratti</button>
  <button class="tab-btn" data-tab="previsionale" onclick="showTab('previsionale')">Previsionale</button>
  <button class="tab-btn" data-tab="cashflow" onclick="showTab('cashflow')">Cashflow</button>
  <button class="tab-btn" data-tab="banche" onclick="showTab('banche')">Banche</button>
  <button class="tab-btn" data-tab="bilanci" onclick="showTab('bilanci')">Bilanci</button>
</nav>
"""

SHOWTAB_JS = """
function showTab(name){
  document.querySelectorAll('.tab-panel').forEach(function(p){ p.classList.toggle('active', p.id === 'tab-' + name); });
  document.querySelectorAll('.tab-btn').forEach(function(b){ b.classList.toggle('active', b.dataset.tab === name); });
  renderAll(); // re-render so charts in the now-visible panel size correctly
}
showTab('contratti');
"""


def transform(html: str) -> str:
    if 'id="tab-contratti"' in html:
        return html  # already tabbed

    # --- boundaries (anchors chosen to be stable across data versions) ---
    i_contratti = html.index('<div class="filter-row">')
    i_cf_title = html.index('<div class="sec-title">Cashflow 2026')
    i_cashflow = html.rindex('<div class="section">', 0, i_cf_title)
    i_bankgrid = html.index('<div class="bank-grid">')
    i_banche = html.rindex('<div class="section">', 0, i_bankgrid)
    i_script = html.index('<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js')
    i_dashclose = html.rindex('</div>', 0, i_script)  # the .dash closing </div>

    head = html[:i_contratti]
    contratti = html[i_contratti:i_cashflow]
    cashflow = html[i_cashflow:i_banche]
    banche = html[i_banche:i_dashclose]
    tail = html[i_dashclose:]  # '</div>' (.dash close) + scripts

    body = (
        head
        + TAB_NAV
        + '<div class="tab-panel active" id="tab-contratti">\n' + contratti + '</div><!--/contratti-->\n'
        + '<div class="tab-panel" id="tab-previsionale">\n</div><!--/previsionale-->\n'
        + '<div class="tab-panel" id="tab-cashflow">\n' + cashflow + '</div><!--/cashflow-->\n'
        + '<div class="tab-panel" id="tab-banche">\n' + banche + '</div><!--/banche-->\n'
        + '<div class="tab-panel" id="tab-bilanci">\n</div><!--/bilanci-->\n'
        + tail
    )

    # CSS: insert before the first </style>
    body = body.replace('</style>', TAB_CSS + '</style>', 1)

    # JS: replace the final init call with the showTab function + default tab
    assert body.rstrip().endswith('</script>')
    idx = body.rindex('renderAll();')
    body = body[:idx] + SHOWTAB_JS.strip() + body[idx + len('renderAll();'):]

    return body


def main():
    path = sys.argv[1]
    html = open(path, encoding="utf-8").read()
    out = transform(html)
    if out == html:
        print("Already tabbed — no change.")
        return
    open(path, "w", encoding="utf-8").write(out)
    print("Tabified:", path)


if __name__ == "__main__":
    main()
