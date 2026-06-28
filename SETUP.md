# Onivà dashboard — aggiornamento automatico settimanale

Questa cartella contiene tutto il necessario per far aggiornare il dashboard
**ogni lunedì** in automatico su GitHub, e pubblicarlo su GitHub Pages.

Cosa fa, ogni settimana e da solo (anche a computer spento):
1. Scarica le versioni aggiornate dei Google Sheet **Contratti** e **Banca**.
2. Ricalcola i dati e rigenera il dashboard.
3. Pubblica la pagina su GitHub Pages.

> Il **cashflow è congelato**: resta com'è adesso. Si aggiornano solo contratti
> e banca. (Lo riattiviamo quando decidiamo come trattare il Cruscotto.)

## Struttura
```
.github/workflows/update-dashboard.yml   il "robot" settimanale
scripts/fetch_sheets.py                  scarica i 2 Google Sheet
scripts/recompute_ci.py                  aggiorna contratti+banca, congela cashflow
scripts/recompute_dashboard.py           motore di calcolo (completo)
oniva_dashboard.html                     dashboard (sorgente)
index.html                               pagina pubblicata (generata, si autoaggiorna)
.gitignore
```

## Setup una tantum (~15 min)

### 1. Carica i file nel tuo repo
Copia tutto il contenuto di questa cartella nella radice del tuo repository
GitHub e fai commit + push.

### 2. Crea un "service account" Google (l'identità che leggerà i fogli)
1. Vai su https://console.cloud.google.com/ (con un account Google qualsiasi).
2. In alto, crea un nuovo progetto (es. "oniva-dashboard").
3. Cerca **"Google Drive API"** → **Abilita**.
4. Menu → **IAM e amministrazione → Account di servizio → Crea account di servizio**.
   Dagli un nome (es. "dashboard-reader") → **Fine**.
5. Apri l'account creato → scheda **Chiavi → Aggiungi chiave → Crea nuova chiave → JSON**.
   Scarica il file JSON (è la "password" del robot: tienilo riservato).
6. Copia l'indirizzo email dell'account di servizio (tipo
   `dashboard-reader@oniva-dashboard.iam.gserviceaccount.com`).

### 3. Condividi i 2 fogli con quell'email
Apri ciascuno di questi Google Sheet → **Condividi** → incolla l'email del
service account → ruolo **Visualizzatore**:
- **ELENCO CONTRATTI ONIVA' - DAL 2021** (proprietaria: eleonora@oniva.it)
- **DATI BANCARI_Amministrazione** (proprietaria: francesca@oniva.it)

Se non hai i permessi di condivisione, chiedi a Eleonora / Francesca di farlo.

### 4. Metti la chiave nel repo come "secret"
Nel repo GitHub: **Settings → Secrets and variables → Actions →
New repository secret**.
- Name: `GOOGLE_SA_KEY`
- Secret: incolla **tutto il contenuto** del file JSON scaricato al passo 2.

### 5. GitHub Pages
Pages è **già attivo** su questo repo (serve `oniva_dashboard.html` dal branch).
Non devi cambiare nulla: il workflow aggiorna il file e Pages lo ripubblica da
solo. L'indirizzo del dashboard resta lo stesso.

### 6. Prova subito
**Actions → "Update Onivà dashboard" → Run workflow**.
Se è tutto verde, dopo 1-2 minuti il dashboard online mostra i dati aggiornati.
Da lì in poi parte da solo ogni lunedì.

## Se qualcosa va storto
- Errore "export … suspiciously small / permission": il foglio non è condiviso
  con l'email del service account (passo 3).
- Errore "GOOGLE_SA_KEY not valid JSON": il secret non contiene il JSON intero.
- Pagina non si aggiorna: verifica che il workflow sia andato a buon fine
  (Actions) e che Settings → Pages punti al branch corretto.
