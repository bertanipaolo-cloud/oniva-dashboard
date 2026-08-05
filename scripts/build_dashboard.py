#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_dashboard.py — one-time structural upgrade of oniva_dashboard.html:
  1) split into 3 tabs (Contratti / Cashflow / Banche)   [via tabify]
  2) add the "Analisi economica" block inside the Contratti tab
     (Firmato/Competenza toggle + KPI cards + per-destination table)
  3) add a `const ANALYSIS = {...};` placeholder + render JS

Does NOT touch the RAW/CF/BANK const blocks or banner dates. The weekly
recompute_ci then fills ANALYSIS (and RAW/BANK) with fresh numbers.

Idempotent. Usage: python3 build_dashboard.py path/to/oniva_dashboard.html
"""
import sys
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("tabify", os.path.join(HERE, "tabify.py"))
tabify = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tabify)

ANALYSIS_CSS = """
/* ---- Analisi economica ---- */
.an-controls { display:flex; align-items:center; gap:14px; flex-wrap:wrap; margin-bottom:12px; }
.seg { display:inline-flex; border:1px solid var(--oni-line); border-radius:9px; overflow:hidden; }
.seg-btn { appearance:none; border:none; background:var(--oni-card); cursor:pointer; font-family:inherit; font-size:12px; font-weight:600; color:var(--oni-tx2); padding:7px 16px; }
.seg-btn + .seg-btn { border-left:1px solid var(--oni-line); }
.seg-btn.active { background:var(--oni-ink); color:#fff; }
.an-hint { font-size:11px; color:var(--oni-tx3); max-width:520px; line-height:1.5; }
.badge { display:inline-block; font-size:10.5px; font-weight:700; letter-spacing:.06em; text-transform:uppercase; padding:3px 9px; border-radius:999px; background:var(--oni-ink); color:#fff; margin-left:8px; vertical-align:middle; }
.badge.alt { background:var(--oni-gold); color:var(--oni-ink-2); }
.badge.sub { background:var(--oni-card-2); color:var(--oni-tx2); border:1px solid var(--oni-line); }

/* Brand: verde Onivà — impostato sulle variabili :root (vedi sotto), così si
   propaga a testata, tabelle, tab attivo, barre e badge in modo coerente. */
.dest-fill { background: linear-gradient(90deg, var(--oni-ink), var(--oni-ink-2)); }
"""

ANALYSIS_UI = """<div class="section">
  <div class="sec-title">Analisi economica <span id="anBadge"></span></div>
  <div class="an-controls">
    <div class="seg">
      <button class="seg-btn active" data-basis="firmato" onclick="setBasis('firmato')">Firmato</button>
      <button class="seg-btn" data-basis="competenza" onclick="setBasis('competenza')">Competenza</button>
    </div>
    <div class="seg" id="anStatoSeg" style="display:none">
      <button class="seg-btn active" data-stato="tutti" onclick="setStato('tutti')">Tutti</button>
      <button class="seg-btn" data-stato="partiti" onclick="setStato('partiti')">Già partiti</button>
      <button class="seg-btn" data-stato="dapartire" onclick="setStato('dapartire')">Da partire</button>
    </div>
    <span class="an-hint">Spesa = valore contratto · Fee = fee al netto IVA · Mark Up = margine Onivà. Dati economici dal 2023. L'anno segue il filtro in alto; “Firmato” = anno di firma, “Competenza” = anno del viaggio.</span>
  </div>
  <div class="metrics" id="anKpi"></div>
  <div class="chart-box" style="margin-top:14px">
    <div class="ctitle">Dettaglio per destinazione</div>
    <div class="cf-table-wrap"><table class="cf-table" id="anTable"></table></div>
  </div>
</div>
"""

FORECAST_UI = """<div class="section">
  <div class="sec-title">Previsionale</div>
  <div class="an-controls">
    <div class="seg">
      <button class="seg-btn" data-sc="0.9" onclick="setScen(0.9)">Prudente −10%</button>
      <button class="seg-btn active" data-sc="1" onclick="setScen(1)">Base</button>
      <button class="seg-btn" data-sc="1.1" onclick="setScen(1.1)">Ottimistico +10%</button>
    </div>
    <span class="an-hint" id="fcHint"></span>
  </div>
  <div class="metrics" id="fcKpi"></div>
</div>

<div class="chart-row">
  <div class="chart-box">
    <div class="ctitle">Firme per mese — effettive vs stimate</div>
    <div class="legend">
      <span><b style="background:#143C3A"></b>Effettive</span>
      <span><b style="background:#D9B86A"></b>Stimate</span>
    </div>
    <div style="position:relative;width:100%;height:220px"><canvas id="chartFcMesi"></canvas></div>
  </div>
  <div class="chart-box">
    <div class="ctitle">Viaggi per anno — storico e stima</div>
    <div class="legend">
      <span><b style="background:#143C3A"></b>Firme</span>
      <span><b style="background:#2A6B66"></b>Partenze</span>
    </div>
    <div style="position:relative;width:100%;height:220px"><canvas id="chartFcAnni"></canvas></div>
  </div>
</div>

<div class="section">
  <div class="chart-box">
    <div class="ctitle" id="fcOrigTitle">Partenze per anno di firma</div>
    <div class="cf-table-wrap"><table class="cf-table" id="fcOrigTable"></table></div>
    <div class="note">Quanti dei viaggi in partenza erano già stati firmati negli anni precedenti (portafoglio ereditato) e quanti sono stati firmati nell'anno stesso.</div>
  </div>
</div>

<div class="section">
  <div class="chart-box">
    <div class="ctitle">Composizione della stima</div>
    <div class="cf-table-wrap"><table class="cf-table" id="fcTable"></table></div>
    <div class="note" id="fcNote"></div>
  </div>
</div>

<div class="section">
  <div class="sec-title">Confronto anni <span id="cmpBadge"></span></div>
  <div class="an-controls">
    <div class="seg">
      <button class="seg-btn active" data-cmp="firmato" onclick="setCmp('firmato')">Firmato</button>
      <button class="seg-btn" data-cmp="competenza" onclick="setCmp('competenza')">Competenza</button>
    </div>
    <span class="an-hint">Totali per anno: valore viaggi, fee e mark up, con variazione sull'anno precedente. Gli ultimi due anni sono stime.</span>
  </div>
  <div class="chart-box">
    <div class="cf-table-wrap"><table class="cf-table" id="cmpTable"></table></div>
    <div class="note" id="cmpNote"></div>
  </div>
</div>

<div class="chart-row">
  <div class="chart-box">
    <div class="ctitle">Valore viaggi per anno (€)</div>
    <div style="position:relative;width:100%;height:220px"><canvas id="chartCmpVal"></canvas></div>
  </div>
  <div class="chart-box">
    <div class="ctitle">Fee e Mark Up per anno (€)</div>
    <div class="legend">
      <span><b style="background:#143C3A"></b>Fee</span>
      <span><b style="background:#D9B86A"></b>Mark Up</span>
    </div>
    <div style="position:relative;width:100%;height:220px"><canvas id="chartCmpFee"></canvas></div>
  </div>
</div>
"""

ANALYSIS_JS = """
let anBasis = 'firmato';
let anStato = 'tutti';
function setBasis(b){
  anBasis = b;
  document.querySelectorAll('.seg-btn[data-basis]').forEach(function(x){ x.classList.toggle('active', x.dataset.basis === b); });
  var seg = document.getElementById('anStatoSeg');
  if(seg) seg.style.display = (b === 'competenza') ? '' : 'none';
  renderAnalysis();
}
function setStato(s){
  anStato = s;
  document.querySelectorAll('.seg-btn[data-stato]').forEach(function(x){ x.classList.toggle('active', x.dataset.stato === s); });
  renderAnalysis();
}
function anAggregate(){
  var yr = document.getElementById('yearFilter').value;
  var src = (typeof ANALYSIS !== 'undefined' && ANALYSIS[anBasis]) ? ANALYSIS[anBasis] : {};
  var years = (yr === 'all') ? Object.keys(src) : [yr];
  var useStato = (anBasis === 'competenza' && anStato !== 'tutti');
  var agg = {};
  years.forEach(function(y){
    var yd = src[y]; if(!yd) return;
    Object.keys(yd).forEach(function(d){
      var a = yd[d]; var r = agg[d] || (agg[d] = [0,0,0,0]);
      for(var i=0;i<4;i++){
        var val = a[i];
        if(useStato && a.length >= 8){
          val = (anStato === 'partiti') ? a[i+4] : (a[i] - a[i+4]);
        }
        r[i] += val;
      }
    });
  });
  var rows = Object.keys(agg).map(function(d){ return [d].concat(agg[d]); })
                   .filter(function(r){ return r[1] > 0; })
                   .sort(function(x,y){ return y[2] - x[2]; });
  var tot = [0,0,0,0];
  rows.forEach(function(r){ for(var i=0;i<4;i++) tot[i] += r[i+1]; });
  return { tot: tot, rows: rows };
}
function renderAnalysis(){
  var kpi = document.getElementById('anKpi'); if(!kpi) return;
  var tbl = document.getElementById('anTable');
  var badge = document.getElementById('anBadge');
  if(badge){
    var lbl = (anBasis === 'firmato') ? 'Firmato · anno di firma' : 'Competenza · anno del viaggio';
    var extra = '';
    if(anBasis === 'competenza' && anStato !== 'tutti'){
      extra = '<span class="badge sub">' + (anStato === 'partiti' ? 'solo già partiti' : 'solo da partire') + '</span>';
    }
    badge.innerHTML = '<span class="badge' + (anBasis === 'competenza' ? ' alt' : '') + '">' + lbl + '</span>' + extra;
  }
  var a = anAggregate();
  var n = a.tot[0], sp = a.tot[1], fe = a.tot[2], mk = a.tot[3];
  if(n === 0){
    var yrSel = document.getElementById('yearFilter').value;
    var msg = (anBasis === 'firmato' && yrSel === '2027')
      ? ['Nessun contratto firmato nel 2027', 'passa a “Competenza” per i viaggi già programmati']
      : ['Nessun dato economico', 'disponibile dal 2023'];
    kpi.innerHTML = '<div class="metric"><div class="label">' + msg[0] + '</div><div class="val">—</div><div class="sub">' + msg[1] + '</div></div>';
    if(tbl) tbl.innerHTML = '';
    return;
  }
  var avg = function(v){ return n > 0 ? v / n : 0; };
  var cards = [
    ['Spesa totale', eur(sp)], ['Spesa media', eur(avg(sp))],
    ['Fee totali', eur(fe)], ['Fee media', eur(avg(fe))],
    ['Mark Up totale', eur(mk)], ['Mark Up media', eur(avg(mk))],
    ['Fee + Mark Up', eur(fe + mk)], ['Fee + MK media', eur(avg(fe + mk))]
  ];
  kpi.innerHTML = cards.map(function(c){
    return '<div class="metric"><div class="label">' + c[0] + '</div><div class="val">' + c[1] + '</div></div>';
  }).join('');
  var h = '<thead><tr><th>Destinazione</th><th>N</th><th>Spesa tot</th><th>Spesa media</th><th>Fee tot</th><th>Fee media</th><th>Mark Up</th><th>Fee+MK</th></tr></thead><tbody>';
  a.rows.forEach(function(r){
    var d = r[0], cn = r[1], csp = r[2], cfe = r[3], cmk = r[4];
    h += '<tr><td>' + d + '</td><td>' + cn + '</td><td>' + eur(csp) + '</td><td>' + eur(csp/cn) + '</td><td>' + eur(cfe) + '</td><td>' + eur(cfe/cn) + '</td><td>' + eur(cmk) + '</td><td>' + eur(cfe + cmk) + '</td></tr>';
  });
  h += '<tr class="sep"><td>Totale</td><td>' + n + '</td><td>' + eur(sp) + '</td><td>' + eur(avg(sp)) + '</td><td>' + eur(fe) + '</td><td>' + eur(avg(fe)) + '</td><td>' + eur(mk) + '</td><td>' + eur(fe + mk) + '</td></tr>';
  h += '</tbody>';
  if(tbl) tbl.innerHTML = h;
}
"""


FORECAST_JS = """
let fcScen = 1;
function setScen(s){
  fcScen = s;
  document.querySelectorAll('.seg-btn[data-sc]').forEach(function(x){ x.classList.toggle('active', parseFloat(x.dataset.sc) === s); });
  renderForecast();
}
function renderForecast(){
  var host = document.getElementById('fcKpi');
  if(!host || typeof FORECAST === 'undefined' || !FORECAST || !FORECAST.anno) return;
  var F = FORECAST, k = fcScen;
  var Y = F.anno, N = F.prossimo.anno;
  var sc = function(o){ return { n: o.n * k, v: o.v * k, fee: (o.fee||0) * k, mk: (o.mk||0) * k }; };
  var firmeAnno = { n: F.firme.ytd.n + F.firme.resto.n * k,
                    v: F.firme.ytd.v + F.firme.resto.v * k,
                    fee: F.firme.ytd.fee + F.firme.resto.fee * k,
                    mk: F.firme.ytd.mk + F.firme.resto.mk * k };
  var partAnno = { n: F.partenze.fatte.n + F.partenze.portafoglio.n + F.partenze.daNuove.n * k,
                   v: F.partenze.fatte.v + F.partenze.portafoglio.v + F.partenze.daNuove.v * k };
  var partAnnoFee = F.partenze.fatte.fee + F.partenze.portafoglio.fee + F.partenze.daNuove.fee * k;
  var partAnnoMk  = F.partenze.fatte.mk  + F.partenze.portafoglio.mk  + F.partenze.daNuove.mk  * k;
  var prox = { n: F.prossimo.portafoglio.n + (F.prossimo.daFirmeAnno.n + F.prossimo.daFirmeProssimo.n) * k,
               v: F.prossimo.portafoglio.v + (F.prossimo.daFirmeAnno.v + F.prossimo.daFirmeProssimo.v) * k,
               fee: F.prossimo.portafoglio.fee + (F.prossimo.daFirmeAnno.fee + F.prossimo.daFirmeProssimo.fee) * k,
               mk: F.prossimo.portafoglio.mk + (F.prossimo.daFirmeAnno.mk + F.prossimo.daFirmeProssimo.mk) * k };
  var n0 = function(x){ return Math.round(x).toLocaleString('it'); };
  host.innerHTML =
    '<div class="metric"><div class="label">Firme ' + Y + ' (stima anno)</div><div class="val">' + n0(firmeAnno.n) + '</div><div class="sub">' + n0(F.firme.ytd.n) + ' fatte + ' + n0(F.firme.resto.n*k) + ' stimate</div></div>' +
    '<div class="metric"><div class="label">Valore firmato ' + Y + '</div><div class="val">' + eurK(firmeAnno.v) + '</div><div class="sub">media ' + eur(firmeAnno.v/Math.max(firmeAnno.n,1)) + '/viaggio</div></div>' +
    '<div class="metric"><div class="label">Fee ' + Y + ' (stima)</div><div class="val">' + eurK(firmeAnno.fee) + '</div><div class="sub">media ' + eur(firmeAnno.fee/Math.max(firmeAnno.n,1)) + '/viaggio</div></div>' +
    '<div class="metric"><div class="label">Fee + Mark Up ' + Y + '</div><div class="val">' + eurK(firmeAnno.fee + firmeAnno.mk) + '</div><div class="sub">di cui mark up ' + eurK(firmeAnno.mk) + '</div></div>' +
    '<div class="metric"><div class="label">Partenze ' + Y + ' (stima anno)</div><div class="val">' + n0(partAnno.n) + '</div><div class="sub">' + n0(F.partenze.fatte.n) + ' fatte + ' + n0(F.partenze.portafoglio.n) + ' in portafoglio</div></div>' +
    '<div class="metric"><div class="label">Fee + MK partenze ' + Y + '</div><div class="val">' + eurK(partAnnoFee + partAnnoMk) + '</div><div class="sub">media ' + eur((partAnnoFee + partAnnoMk)/Math.max(partAnno.n,1)) + '/viaggio</div></div>' +
    '<div class="metric"><div class="label">Partenze ' + N + ' (stima)</div><div class="val">' + n0(prox.n) + '</div><div class="sub">valore ' + eurK(prox.v) + '</div></div>' +
    '<div class="metric"><div class="label">Fee + MK ' + N + ' (stima)</div><div class="val">' + eurK(prox.fee + prox.mk) + '</div><div class="sub">media ' + eur((prox.fee + prox.mk)/Math.max(prox.n,1)) + '/viaggio</div></div>';

  var hint = document.getElementById('fcHint');
  if(hint) hint.textContent = 'Stima su stagionalità 2023–2025 (quota firme per mese e probabilità di partire nell\\'anno di firma). Dati al ' + F.asOf.split('-').reverse().join('.') + '.';

  var tbl = document.getElementById('fcTable');
  if(tbl){
    var E = function(o, f){ return [o.n * f, o.v * f, (o.fee||0) * f, (o.mk||0) * f]; };
    var rows = [
      ['Firme ' + Y + ' — già acquisite', E(F.firme.ytd,1), 'effettivo'],
      ['Firme ' + Y + ' — stimate da qui a fine anno', E(F.firme.resto,k), 'stima'],
      ['TOT|Totale firme ' + Y, [F.firme.ytd.n + F.firme.resto.n*k, F.firme.ytd.v + F.firme.resto.v*k, F.firme.ytd.fee + F.firme.resto.fee*k, F.firme.ytd.mk + F.firme.resto.mk*k], ''],
      ['Partenze ' + Y + ' — già effettuate', E(F.partenze.fatte,1), 'effettivo'],
      ['Partenze ' + Y + ' — già firmate, da partire', E(F.partenze.portafoglio,1), 'in portafoglio'],
      ['Partenze ' + Y + ' — da firme future', E(F.partenze.daNuove,k), 'stima'],
      ['TOT|Totale partenze ' + Y, [partAnno.n, partAnno.v, partAnnoFee, partAnnoMk], ''],
      ['Partenze ' + N + ' — già firmate', E(F.prossimo.portafoglio,1), 'in portafoglio'],
      ['Partenze ' + N + ' — da firme ' + Y + ' (2° semestre)', E(F.prossimo.daFirmeAnno,k), 'stima'],
      ['Partenze ' + N + ' — da firme ' + N, E(F.prossimo.daFirmeProssimo,k), 'stima'],
      ['TOT|Totale partenze ' + N, [prox.n, prox.v, prox.fee, prox.mk], '']
    ];
    var h = '<thead><tr><th>Voce</th><th>Viaggi</th><th>Valore</th><th>Valore medio</th><th>Fee</th><th>Fee media</th><th>Mark Up</th><th>Fee+MK</th><th>Fee+MK media</th><th>Tipo</th></tr></thead><tbody>';
    rows.forEach(function(r){
      var isTot = r[0].indexOf('TOT|') === 0;
      var label = isTot ? r[0].slice(4) : r[0];
      var d = r[1], nn = Math.max(d[0], 1);
      h += '<tr' + (isTot ? ' class="sep"' : '') + '><td>' + (isTot ? '<b>' + label + '</b>' : label) + '</td>' +
           '<td>' + n0(d[0]) + '</td><td>' + eur(d[1]) + '</td><td>' + eur(d[1]/nn) + '</td>' +
           '<td>' + eur(d[2]) + '</td><td>' + eur(d[2]/nn) + '</td>' +
           '<td>' + eur(d[3]) + '</td><td>' + eur(d[2] + d[3]) + '</td><td>' + eur((d[2]+d[3])/nn) + '</td>' +
           '<td>' + r[2] + '</td></tr>';
    });
    h += '</tbody>';
    tbl.innerHTML = h;
  }
  var note = document.getElementById('fcNote');
  if(note && F.ipotesi){
    note.innerHTML = 'Ipotesi: valore medio per viaggio <b>' + eur(F.ipotesi.avgValore) + '</b>, fee media <b>' + eur(F.ipotesi.avgFee) + '</b>, mark up <b>' + (F.ipotesi.mkRatio*100).toFixed(1) + '%</b> del valore. Storicamente il <b>' + Math.round(F.ipotesi.quotaStessoAnno*100) + '%</b> dei viaggi parte nell\\'anno di firma, il resto l\\'anno successivo. Le firme di ' + N + ' sono ipotizzate pari alla stima ' + Y + ', scalate dallo scenario scelto.';
  }

  // table: departures by signing year
  var ot = document.getElementById('fcOrigTable');
  if(ot && F.partenzePerFirma){
    var ti = document.getElementById('fcOrigTitle');
    if(ti) ti.textContent = 'Partenze ' + Y + ' per anno di firma';
    var keys = Object.keys(F.partenzePerFirma).sort();
    var oh = '<thead><tr><th>Firmati nel</th><th>Viaggi</th><th>di cui già partiti</th><th>Valore</th><th>Valore medio</th><th>Fee</th><th>Fee media</th><th>Mark Up</th><th>Fee+MK</th></tr></thead><tbody>';
    var ot_t = [0,0,0,0,0];
    keys.forEach(function(sy){
      var d = F.partenzePerFirma[sy], nn = Math.max(d.n, 1);
      ot_t[0]+=d.n; ot_t[1]+=d.nPartiti; ot_t[2]+=d.v; ot_t[3]+=d.fee; ot_t[4]+=d.mk;
      var lab = (parseInt(sy) < Y) ? sy + ' <span style="color:var(--oni-tx3)">(portafoglio ereditato)</span>' : sy + ' <span style="color:var(--oni-tx3)">(stesso anno)</span>';
      oh += '<tr><td>' + lab + '</td><td>' + n0(d.n) + '</td><td>' + n0(d.nPartiti) + '</td><td>' + eur(d.v) + '</td><td>' + eur(d.v/nn) + '</td><td>' + eur(d.fee) + '</td><td>' + eur(d.fee/nn) + '</td><td>' + eur(d.mk) + '</td><td>' + eur(d.fee + d.mk) + '</td></tr>';
    });
    var tn = Math.max(ot_t[0], 1);
    oh += '<tr class="sep"><td><b>Totale già firmate</b></td><td>' + n0(ot_t[0]) + '</td><td>' + n0(ot_t[1]) + '</td><td>' + eur(ot_t[2]) + '</td><td>' + eur(ot_t[2]/tn) + '</td><td>' + eur(ot_t[3]) + '</td><td>' + eur(ot_t[3]/tn) + '</td><td>' + eur(ot_t[4]) + '</td><td>' + eur(ot_t[3]+ot_t[4]) + '</td></tr>';
    oh += '</tbody>';
    ot.innerHTML = oh;
  }
  renderCmp();

  // chart: monthly signings actual vs forecast
  if(charts.fcMesi) charts.fcMesi.destroy();
  var cvM = document.getElementById('chartFcMesi');
  if(cvM){
    charts.fcMesi = new Chart(cvM, {
      type:'bar',
      data:{ labels: CF.mesi, datasets:[
        { label:'Effettive', data: F.firme.mesi.map(function(m){ return m.act; }), backgroundColor: ONI.ink, borderRadius:3, borderSkipped:false },
        { label:'Stimate', data: F.firme.mesi.map(function(m){ return Math.round(m.fc * k); }), backgroundColor: ONI.gold, borderRadius:3, borderSkipped:false }
      ]},
      options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}},
        scales:{ x:{ stacked:true, ticks:{color:'#888',font:{size:11}}, grid:{display:false} },
                 y:{ stacked:true, ticks:{color:'#888',font:{size:11}}, grid:{color:'rgba(128,128,128,0.1)'} } } }
    });
  }
  // chart: yearly history + estimate
  if(charts.fcAnni) charts.fcAnni.destroy();
  var cvY = document.getElementById('chartFcAnni');
  if(cvY){
    var labels = F.storico.anni.concat([Y + ' (stima)', N + ' (stima)']);
    var firme = F.storico.firme.concat([Math.round(firmeAnno.n), Math.round(F.firme.anno.n * k)]);
    var part  = F.storico.partenze.concat([Math.round(partAnno.n), Math.round(prox.n)]);
    charts.fcAnni = new Chart(cvY, {
      type:'bar',
      data:{ labels: labels, datasets:[
        { label:'Firme', data: firme, backgroundColor: ONI.ink, borderRadius:4, borderSkipped:false },
        { label:'Partenze', data: part, backgroundColor: ONI.ink2, borderRadius:4, borderSkipped:false }
      ]},
      options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}},
        scales:{ x:{ ticks:{color:'#888',font:{size:10}}, grid:{display:false} },
                 y:{ ticks:{color:'#888',font:{size:11}}, grid:{color:'rgba(128,128,128,0.1)'} } } }
    });
  }
}
"""


CMP_JS = """
let cmpBasis = 'firmato';
function setCmp(b){
  cmpBasis = b;
  document.querySelectorAll('.seg-btn[data-cmp]').forEach(function(x){ x.classList.toggle('active', x.dataset.cmp === b); });
  renderCmp();
}
function cmpYearTotals(basis, y){
  var src = (typeof ANALYSIS !== 'undefined' && ANALYSIS[basis]) ? ANALYSIS[basis][y] : null;
  if(!src) return null;
  var t = [0,0,0,0];
  Object.keys(src).forEach(function(d){ for(var i=0;i<4;i++) t[i] += src[d][i]; });
  return { n: t[0], v: t[1], fee: t[2], mk: t[3] };
}
function renderCmp(){
  var tbl = document.getElementById('cmpTable');
  if(!tbl || typeof FORECAST === 'undefined' || !FORECAST.anno) return;
  var F = FORECAST, k = fcScen, Y = F.anno, N = F.prossimo.anno;
  var cb = document.getElementById('cmpBadge');
  if(cb){
    cb.innerHTML = '<span class="badge' + (cmpBasis === 'competenza' ? ' alt' : '') + '">' +
      (cmpBasis === 'firmato' ? 'Firmato · anno di firma' : 'Competenza · anno del viaggio') + '</span>';
  }
  var rows = [];
  [Y-3, Y-2, Y-1].forEach(function(y){
    var t = cmpYearTotals(cmpBasis, String(y));
    if(t) rows.push({ label: String(y), d: t, est: false });
  });
  if(cmpBasis === 'firmato'){
    rows.push({ label: Y + ' (stima)', est: true, d: {
      n: F.firme.ytd.n + F.firme.resto.n*k, v: F.firme.ytd.v + F.firme.resto.v*k,
      fee: F.firme.ytd.fee + F.firme.resto.fee*k, mk: F.firme.ytd.mk + F.firme.resto.mk*k } });
    rows.push({ label: N + ' (stima)', est: true, d: {
      n: F.firmeProssimo.n*k, v: F.firmeProssimo.v*k, fee: F.firmeProssimo.fee*k, mk: F.firmeProssimo.mk*k } });
  } else {
    var pf = F.partenze;
    rows.push({ label: Y + ' (stima)', est: true, d: {
      n: pf.fatte.n + pf.portafoglio.n + pf.daNuove.n*k,
      v: pf.fatte.v + pf.portafoglio.v + pf.daNuove.v*k,
      fee: pf.fatte.fee + pf.portafoglio.fee + pf.daNuove.fee*k,
      mk: pf.fatte.mk + pf.portafoglio.mk + pf.daNuove.mk*k } });
    var px = F.prossimo;
    rows.push({ label: N + ' (stima)', est: true, d: {
      n: px.portafoglio.n + (px.daFirmeAnno.n + px.daFirmeProssimo.n)*k,
      v: px.portafoglio.v + (px.daFirmeAnno.v + px.daFirmeProssimo.v)*k,
      fee: px.portafoglio.fee + (px.daFirmeAnno.fee + px.daFirmeProssimo.fee)*k,
      mk: px.portafoglio.mk + (px.daFirmeAnno.mk + px.daFirmeProssimo.mk)*k } });
  }
  var n0 = function(x){ return Math.round(x).toLocaleString('it'); };
  var pct = function(cur, prev){
    if(!prev) return '<td>—</td>';
    var p = (cur - prev) / prev * 100;
    var cls = p >= 0 ? 'pos' : 'neg';
    return '<td class="' + cls + '">' + (p >= 0 ? '+' : '') + p.toFixed(1) + '%</td>';
  };
  var cov = F.mkCoverage || {};
  var partial = [];
  var h = '<thead><tr><th>Anno</th><th>Viaggi</th><th>Valore viaggi</th><th>Valore medio</th><th>Fee</th><th>Fee media</th><th>Mark Up</th><th>Fee+MK</th><th>Fee+MK media</th><th>Δ Fee</th></tr></thead><tbody>';
  rows.forEach(function(r, i){
    var d = r.d, prev = i > 0 ? rows[i-1].d : null;
    var fm = d.fee + d.mk;
    var yKey = r.label.slice(0,4);
    var c = cov[yKey];
    var mkCell;
    if(!r.est && c !== undefined && c < 0.05){
      mkCell = '<td style="color:var(--oni-tx3)">n/d</td>';
      partial.push(yKey + ' (non rilevato)');
    } else if(!r.est && c !== undefined && c < 0.95){
      mkCell = '<td>' + eur(d.mk) + ' <span style="color:var(--oni-tx3)">(' + Math.round(c*100) + '%)</span></td>';
      partial.push(yKey + ' (' + Math.round(c*100) + '% compilato)');
    } else {
      mkCell = '<td>' + eur(d.mk) + '</td>';
    }
    var nn = Math.max(d.n, 1);
    h += '<tr' + (r.est ? ' class="sep"' : '') + '><td>' + (r.est ? '<b>' + r.label + '</b>' : r.label) + '</td>' +
      '<td>' + n0(d.n) + '</td><td>' + eur(d.v) + '</td><td>' + eur(d.v/nn) + '</td>' +
      '<td>' + eur(d.fee) + '</td><td>' + eur(d.fee/nn) + '</td>' + mkCell +
      '<td>' + eur(fm) + '</td><td>' + eur(fm/nn) + '</td>' +
      pct(d.fee, prev ? prev.fee : 0) + '</tr>';
  });
  h += '</tbody>';
  tbl.innerHTML = h;
  var cn = document.getElementById('cmpNote');
  if(cn){
    cn.innerHTML = 'Il <b>mark up</b> viene inserito a consuntivo: negli anni evidenziati la colonna è incompleta' +
      (partial.length ? ' — ' + partial.join(', ') : '') +
      '. Il confronto più affidabile è quindi sul <b>valore viaggi</b> e sulle <b>fee</b>; nelle stime il mark up è modellato al ' +
      ((F.ipotesi ? F.ipotesi.mkRatio : 0)*100).toFixed(1) + '% del valore.';
  }

  var labels = rows.map(function(r){ return r.label; });
  if(charts.cmpVal) charts.cmpVal.destroy();
  var c1 = document.getElementById('chartCmpVal');
  if(c1){
    charts.cmpVal = new Chart(c1, {
      type:'bar',
      data:{ labels: labels, datasets:[{ data: rows.map(function(r){ return Math.round(r.d.v); }),
        backgroundColor: rows.map(function(r){ return r.est ? ONI.gold : ONI.ink; }), borderRadius:4, borderSkipped:false }]},
      options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false},
        tooltip:{callbacks:{label:function(c){ return ' ' + eur(c.raw); }}}},
        scales:{ x:{ ticks:{color:'#888',font:{size:10}}, grid:{display:false} },
                 y:{ ticks:{color:'#888',font:{size:11},callback:function(v){ return eurK(v); }}, grid:{color:'rgba(128,128,128,0.1)'} } } }
    });
  }
  if(charts.cmpFee) charts.cmpFee.destroy();
  var c2 = document.getElementById('chartCmpFee');
  if(c2){
    charts.cmpFee = new Chart(c2, {
      type:'bar',
      data:{ labels: labels, datasets:[
        { label:'Fee', data: rows.map(function(r){ return Math.round(r.d.fee); }), backgroundColor: ONI.ink, borderRadius:3, borderSkipped:false },
        { label:'Mark Up', data: rows.map(function(r){ return Math.round(r.d.mk); }), backgroundColor: ONI.gold, borderRadius:3, borderSkipped:false }
      ]},
      options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false},
        tooltip:{callbacks:{label:function(c){ return ' ' + c.dataset.label + ': ' + eur(c.raw); }}}},
        scales:{ x:{ stacked:true, ticks:{color:'#888',font:{size:10}}, grid:{display:false} },
                 y:{ stacked:true, ticks:{color:'#888',font:{size:11},callback:function(v){ return eurK(v); }}, grid:{color:'rgba(128,128,128,0.1)'} } } }
    });
  }
}
"""


BILANCI_UI = """<div class="section">
  <div class="sec-title">Bilanci a confronto <span class="badge">2023 · 2024 · 2025</span></div>
  <div class="metrics" id="bilKpi"></div>
</div>

<div class="chart-row">
  <div class="chart-box">
    <div class="ctitle">Ricavi, EBITDA e utile netto (€)</div>
    <div class="legend">
      <span><b style="background:#143C3A"></b>Ricavi</span>
      <span><b style="background:#D9B86A"></b>EBITDA</span>
      <span><b style="background:#1D7A5A"></b>Utile netto</span>
    </div>
    <div style="position:relative;width:100%;height:220px"><canvas id="chartBilCE"></canvas></div>
  </div>
  <div class="chart-box">
    <div class="ctitle">Struttura dei costi sui ricavi (%)</div>
    <div class="legend">
      <span><b style="background:#143C3A"></b>Acquisti viaggi</span>
      <span><b style="background:#2A6B66"></b>Personale</span>
      <span><b style="background:#D9B86A"></b>Servizi e altri</span>
      <span><b style="background:#1D7A5A"></b>Margine</span>
    </div>
    <div style="position:relative;width:100%;height:220px"><canvas id="chartBilCosti"></canvas></div>
  </div>
</div>

<div class="section">
  <div class="chart-box">
    <div class="ctitle">Conto economico riclassificato</div>
    <div class="cf-table-wrap"><table class="cf-table" id="bilCeTable"></table></div>
  </div>
</div>

<div class="section">
  <div class="chart-box">
    <div class="ctitle">Stato patrimoniale</div>
    <div class="cf-table-wrap"><table class="cf-table" id="bilSpTable"></table></div>
    <div class="note" id="bilNota"></div>
  </div>
</div>

<div class="section">
  <div class="chart-box">
    <div class="ctitle">Indici</div>
    <div class="cf-table-wrap"><table class="cf-table" id="bilIdxTable"></table></div>
  </div>
</div>

<div class="section">
  <div class="sec-title">Raccordo bilancio ↔ gestionale</div>
  <div class="chart-box">
    <div class="cf-table-wrap"><table class="cf-table" id="bilRacTable"></table></div>
    <div class="note">I ricavi di bilancio seguono la <b>competenza economica</b> (viaggio effettuato), quindi si avvicinano al gestionale “Competenza” più che al “Firmato”. Differenze residue derivano da acconti, storni, assicurazioni e servizi fatturati separatamente. Nel 2023 il gestionale ha molte date di viaggio non compilate, quindi il confronto per quell'anno è meno affidabile.</div>
  </div>
</div>
"""

BILANCI_JS = """
function renderBilanci(){
  var host = document.getElementById('bilKpi');
  if(!host || typeof BILANCI === 'undefined' || !BILANCI.anni) return;
  var B = BILANCI, A = B.anni, ce = B.ce, sp = B.sp, L = A.length - 1;
  var ebitda = A.map(function(_,i){ return ce.ebit[i] + ce.ammortamenti[i]; });
  var pctv = function(x, base){ return base ? (x/base*100).toFixed(1) + '%' : '—'; };
  var dlt = function(cur, prev){
    if(!prev) return '';
    var p = (cur - prev) / Math.abs(prev) * 100;
    return '<div class="sub" style="color:' + (p>=0?'#1D7A5A':'#C0392B') + '">' + (p>=0?'+':'') + p.toFixed(0) + '% vs ' + A[L-1] + '</div>';
  };
  host.innerHTML =
    '<div class="metric"><div class="label">Ricavi ' + A[L] + '</div><div class="val">' + eurK(ce.ricaviVendite[L]) + '</div>' + dlt(ce.ricaviVendite[L], ce.ricaviVendite[L-1]) + '</div>' +
    '<div class="metric"><div class="label">EBITDA ' + A[L] + '</div><div class="val">' + eurK(ebitda[L]) + '</div>' + dlt(ebitda[L], ebitda[L-1]) + '</div>' +
    '<div class="metric"><div class="label">Utile netto ' + A[L] + '</div><div class="val">' + eur(ce.utile[L]) + '</div>' + dlt(ce.utile[L], ce.utile[L-1]) + '</div>' +
    '<div class="metric"><div class="label">Patrimonio netto ' + A[L] + '</div><div class="val">' + eur(sp.patrimonioNetto[L]) + '</div>' + dlt(sp.patrimonioNetto[L], sp.patrimonioNetto[L-1]) + '</div>';

  var hdr = function(){ return '<thead><tr><th>Voce</th>' + A.map(function(y){ return '<th>' + y + '</th>'; }).join('') + '<th>Δ ' + A[L-1] + '→' + A[L] + '</th></tr></thead><tbody>'; };
  var row = function(label, vals, bold){
    var d = '';
    if(vals[L-1]) { var p = (vals[L]-vals[L-1])/Math.abs(vals[L-1])*100;
      d = '<td class="' + (p>=0?'pos':'neg') + '">' + (p>=0?'+':'') + p.toFixed(1) + '%</td>'; }
    else d = '<td>—</td>';
    return '<tr' + (bold?' class="sep"':'') + '><td>' + (bold?'<b>'+label+'</b>':label) + '</td>' +
      vals.map(function(v){ return '<td>' + eur(v) + '</td>'; }).join('') + d + '</tr>';
  };
  var t1 = document.getElementById('bilCeTable');
  if(t1){
    t1.innerHTML = hdr() +
      row('Ricavi delle vendite', ce.ricaviVendite) +
      row('Altri ricavi', ce.altriRicavi) +
      row('Valore della produzione', ce.valoreProd, true) +
      row('Acquisti viaggi e materie', ce.materiePrime) +
      row('Servizi', ce.servizi) +
      row('Godimento beni di terzi', ce.godimentoBeni) +
      row('Personale', ce.personale) +
      row('Oneri diversi', ce.oneriDiversi) +
      row('EBITDA', ebitda, true) +
      row('Ammortamenti', ce.ammortamenti) +
      row('EBIT (A−B)', ce.ebit, true) +
      row('Gestione finanziaria', ce.gestFin) +
      row('Risultato ante imposte', ce.anteImposte) +
      row('Imposte', ce.imposte) +
      row('Utile netto', ce.utile, true) + '</tbody>';
  }
  var t2 = document.getElementById('bilSpTable');
  if(t2){
    t2.innerHTML = hdr() +
      row('Immobilizzazioni', sp.immobilizz) +
      row('Rimanenze', sp.rimanenze) +
      row('Crediti', sp.crediti) +
      row('Disponibilità liquide', sp.liquidita) +
      row('Ratei e risconti attivi', sp.rateiAttivi) +
      row('Totale attivo', sp.totAttivo, true) +
      row('Patrimonio netto', sp.patrimonioNetto) +
      row('TFR', sp.tfr) +
      row('Debiti', sp.debiti) +
      row('Ratei e risconti passivi', sp.rateiPassivi) +
      row('Totale passivo', sp.totPassivo, true) + '</tbody>';
  }
  var nb = document.getElementById('bilNota');
  if(nb) nb.innerHTML = B.nota;

  var t3 = document.getElementById('bilIdxTable');
  if(t3){
    var idx = [
      ['Margine EBITDA', A.map(function(_,i){ return pctv(ebitda[i], ce.ricaviVendite[i]); })],
      ['Margine EBIT', A.map(function(_,i){ return pctv(ce.ebit[i], ce.ricaviVendite[i]); })],
      ['Utile netto / ricavi', A.map(function(_,i){ return pctv(ce.utile[i], ce.ricaviVendite[i]); })],
      ['Costo acquisti / ricavi', A.map(function(_,i){ return pctv(ce.materiePrime[i], ce.ricaviVendite[i]); })],
      ['Costo personale / ricavi', A.map(function(_,i){ return pctv(ce.personale[i], ce.ricaviVendite[i]); })],
      ['ROE (utile / patrimonio netto)', A.map(function(_,i){ return pctv(ce.utile[i], sp.patrimonioNetto[i]); })],
      ['Patrimonio netto / totale attivo', A.map(function(_,i){ return pctv(sp.patrimonioNetto[i], sp.totAttivo[i]); })],
      ['Liquidità / debiti', A.map(function(_,i){ return pctv(sp.liquidita[i], sp.debiti[i]); })]
    ];
    t3.innerHTML = '<thead><tr><th>Indice</th>' + A.map(function(y){ return '<th>' + y + '</th>'; }).join('') + '</tr></thead><tbody>' +
      idx.map(function(r){ return '<tr><td>' + r[0] + '</td>' + r[1].map(function(v){ return '<td>' + v + '</td>'; }).join('') + '</tr>'; }).join('') + '</tbody>';
  }

  // raccordo bilancio <-> gestionale
  var t4 = document.getElementById('bilRacTable');
  if(t4 && typeof ANALYSIS !== 'undefined'){
    var g = function(basis, y){
      var d = ANALYSIS[basis] ? ANALYSIS[basis][y] : null;
      if(!d) return null;
      var t = [0,0,0,0];
      Object.keys(d).forEach(function(k){ for(var i=0;i<4;i++) t[i] += d[k][i]; });
      return t;
    };
    var h = '<thead><tr><th>Anno</th><th>Ricavi bilancio</th><th>Gestionale competenza</th><th>Δ</th><th>Gestionale firmato</th><th>Fee gestionale</th></tr></thead><tbody>';
    A.forEach(function(y, i){
      var gc = g('competenza', String(y)), gf = g('firmato', String(y));
      var dv = gc ? ce.ricaviVendite[i] - gc[1] : null;
      h += '<tr><td>' + y + '</td><td>' + eur(ce.ricaviVendite[i]) + '</td>' +
        '<td>' + (gc ? eur(gc[1]) : '—') + '</td>' +
        '<td class="' + (dv >= 0 ? 'pos' : 'neg') + '">' + (dv === null ? '—' : (dv >= 0 ? '+' : '') + eur(dv)) + '</td>' +
        '<td>' + (gf ? eur(gf[1]) : '—') + '</td>' +
        '<td>' + (gc ? eur(gc[2]) : '—') + '</td></tr>';
    });
    t4.innerHTML = h + '</tbody>';
  }

  if(charts.bilCE) charts.bilCE.destroy();
  var c1 = document.getElementById('chartBilCE');
  if(c1){
    charts.bilCE = new Chart(c1, { type:'bar',
      data:{ labels:A, datasets:[
        { label:'Ricavi', data: ce.ricaviVendite, backgroundColor: ONI.ink, borderRadius:4, borderSkipped:false },
        { label:'EBITDA', data: ebitda, backgroundColor: ONI.gold, borderRadius:4, borderSkipped:false },
        { label:'Utile', data: ce.utile, backgroundColor: ONI.green, borderRadius:4, borderSkipped:false }
      ]},
      options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false},
        tooltip:{callbacks:{label:function(c){ return ' ' + c.dataset.label + ': ' + eur(c.raw); }}}},
        scales:{ x:{ ticks:{color:'#888',font:{size:11}}, grid:{display:false} },
                 y:{ ticks:{color:'#888',font:{size:11},callback:function(v){ return eurK(v); }}, grid:{color:'rgba(128,128,128,0.1)'} } } } });
  }
  if(charts.bilCosti) charts.bilCosti.destroy();
  var c2 = document.getElementById('chartBilCosti');
  if(c2){
    var pc = function(arr){ return A.map(function(_,i){ return +(arr[i]/ce.ricaviVendite[i]*100).toFixed(1); }); };
    var altri = A.map(function(_,i){ return ce.servizi[i] + ce.godimentoBeni[i] + ce.oneriDiversi[i]; });
    var marg = A.map(function(_,i){ return ce.ricaviVendite[i] - ce.materiePrime[i] - ce.personale[i] - altri[i]; });
    charts.bilCosti = new Chart(c2, { type:'bar',
      data:{ labels:A, datasets:[
        { label:'Acquisti viaggi', data: pc(ce.materiePrime), backgroundColor: ONI.ink },
        { label:'Personale', data: pc(ce.personale), backgroundColor: ONI.ink2 },
        { label:'Servizi e altri', data: pc(altri), backgroundColor: ONI.gold },
        { label:'Margine', data: pc(marg), backgroundColor: ONI.green }
      ]},
      options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false},
        tooltip:{callbacks:{label:function(c){ return ' ' + c.dataset.label + ': ' + c.raw + '%'; }}}},
        scales:{ x:{ stacked:true, ticks:{color:'#888',font:{size:11}}, grid:{display:false} },
                 y:{ stacked:true, max:100, ticks:{color:'#888',font:{size:11},callback:function(v){ return v + '%'; }}, grid:{color:'rgba(128,128,128,0.1)'} } } } });
  }
}
"""


def build(html: str) -> str:
    html = tabify.transform(html)              # ensure 3 tabs (idempotent)
    if 'id="anKpi"' in html:
        return html                            # analysis already added

    # CSS
    html = html.replace('</style>', ANALYSIS_CSS + '</style>', 1)
    # year filter: add 2027 (trips already scheduled for that year)
    if '<option value="2027">' not in html:
        html = html.replace('<option value="2026">2026</option>',
                            '<option value="2026">2026</option>\n'
                            '    <option value="2027">2027</option>', 1)
    # UI inside the Contratti panel (just before it closes)
    html = html.replace('</div><!--/contratti-->', ANALYSIS_UI + '</div><!--/contratti-->', 1)
    # Forecast tab content
    html = html.replace('</div><!--/previsionale-->', FORECAST_UI + '</div><!--/previsionale-->', 1)
    # Bilanci tab content
    html = html.replace('</div><!--/bilanci-->', BILANCI_UI + '</div><!--/bilanci-->', 1)
    # placeholder consts (filled by recompute_ci) + static BILANCI data
    import importlib.util as _il
    import os as _os
    _s = _il.spec_from_file_location("bilanci_data", _os.path.join(HERE, "bilanci_data.py"))
    _bd = _il.module_from_spec(_s)
    _s.loader.exec_module(_bd)
    html = html.replace('const TIPO_COLORS =',
                        'const ANALYSIS = {firmato:{},competenza:{}};\n\n'
                        'const FORECAST = {};\n\n'
                        'const BILANCI = ' + _bd.js() + ';\n\nconst TIPO_COLORS =', 1)
    # brand green: rewrite the root palette (verde Onivà from company materials)
    html = html.replace('--oni-ink: #143C3A;        /* deep teal */',
                        '--oni-ink: #2F6B58;        /* verde Onivà */', 1)
    html = html.replace('--oni-ink-2: #0C2A28;      /* darker teal */',
                        '--oni-ink-2: #1F4A3E;      /* verde Onivà scuro */', 1)
    # brand green in charts too (ONI.ink drives most chart series)
    html = html.replace("const ONI = { ink:'#143C3A', ink2:'#2A6B66'",
                        "const ONI = { ink:'#2F6B58', ink2:'#4E8C77'", 1)
    html = html.replace("HONEYMOON:'#143C3A','MULTI-TRAVELER':'#2A6B66'",
                        "HONEYMOON:'#2F6B58','MULTI-TRAVELER':'#4E8C77'", 1)
    # legend swatches that were hardcoded to the old teal
    html = html.replace('background:#143C3A', 'background:#2F6B58')
    html = html.replace('background:#2A6B66', 'background:#4E8C77')
    # render JS (define before renderAll) + wire into renderAll
    html = html.replace('function renderAll() {',
                        ANALYSIS_JS + FORECAST_JS + CMP_JS + BILANCI_JS + '\nfunction renderAll() {', 1)
    html = html.replace('  renderBank();\n}',
                        '  renderBank();\n  renderAnalysis();\n  renderForecast();\n  renderBilanci();\n}', 1)
    return html


def main():
    path = sys.argv[1]
    html = open(path, encoding="utf-8").read()
    out = build(html)
    if out == html:
        print("Already built — no change.")
        return
    open(path, "w", encoding="utf-8").write(out)
    print("Built (tabs + analisi economica):", path)


if __name__ == "__main__":
    main()
