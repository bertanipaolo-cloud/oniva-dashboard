#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bilanci_data.py — static financial-statement data (2023-2025) extracted from:
  - "Bilancio 09062026-1.pdf"        -> 31/12/2025 vs 31/12/2024
  - "15255931006.xbrl-5-1.pdf"       -> 31/12/2024 vs 31/12/2023
The 2024 column was cross-checked between both documents and matches exactly.

This is ANNUAL data: it is not refreshed by the weekly job. Update once a year
by re-running the extraction against the new bilancio PDF.
"""

ANNI = [2023, 2024, 2025]

# --- Conto economico -------------------------------------------------------
CE = {
    "ricaviVendite":  [2201776, 2624310, 3653573],
    "altriRicavi":    [233, 13014, 10417],
    "valoreProd":     [2202009, 2637324, 3663990],
    "materiePrime":   [1649153, 2036789, 2859703],
    "servizi":        [159776, 180496, 218399],
    "godimentoBeni":  [13934, 37690, 13201],
    "personale":      [340669, 342342, 477968],
    "ammortamenti":   [13329, 15739, 0],
    "oneriDiversi":   [19327, 11648, 8944],
    "costiProd":      [2196188, 2624704, 3578215],
    "ebit":           [5821, 12620, 85775],
    "gestFin":        [92, 961, 180],
    "anteImposte":    [5913, 13581, 85955],
    "imposte":        [5327, 8584, 15079],
    "utile":          [586, 4997, 70876],
}

# --- Stato patrimoniale ----------------------------------------------------
SP = {
    "immobilizz":     [87749, 83455, 84893],
    "rimanenze":      [1731, 0, 882863],
    "crediti":        [33041, 68704, 38596],
    "liquidita":      [61377, 84560, 177338],
    "attivoCircol":   [96149, 153264, 1098797],
    "rateiAttivi":    [397006, 579417, 0],
    "totAttivo":      [580904, 816136, 1183690],
    "patrimonioNetto":[2011, 10003, 77883],
    "tfr":            [29773, 36586, 29042],
    "debiti":         [307836, 376767, 1076765],
    "rateiPassivi":   [241284, 392780, 0],
    "totPassivo":     [580904, 816136, 1183690],
}

NOTE = (
    "Fonte: bilanci depositati (2025 e 2024; il 2024 combacia esattamente nei due documenti). "
    "ATTENZIONE alla comparabilità: nel 2025 cambia la rappresentazione degli acconti sui viaggi "
    "non ancora partiti — compaiono 883k di rimanenze e i debiti salgono a 1,08 mln, mentre ratei e "
    "risconti (attivi 579k e passivi 393k nel 2024) vanno a zero. Le voci patrimoniali 2025 non sono "
    "quindi direttamente confrontabili con gli anni precedenti. Il bilancio 2025 non espone "
    "ammortamenti (0 contro 15.739 del 2024)."
)


def js():
    def arr(a):
        return "[" + ",".join(str(x) for x in a) + "]"
    L = ["{", f"  anni: {arr(ANNI)},", "  ce: {"]
    L += [f"    {k}: {arr(v)}," for k, v in CE.items()]
    L.append("  },")
    L.append("  sp: {")
    L += [f"    {k}: {arr(v)}," for k, v in SP.items()]
    L.append("  },")
    L.append(f"  nota: {NOTE!r}".replace("'", '"', 1)[:-1] + '"'
             if False else f'  nota: "{NOTE}"')
    L.append("}")
    return "\n".join(L)


if __name__ == "__main__":
    print(js())
