# Calendario Stagionale — Paniere Globale

Genera ogni settimana un calendario di **stagionalità azionaria** (lun–ven della settimana entrante)
per un paniere di 34 titoli globali (USA, Europa, Italia, Asia), scaricando i prezzi da Yahoo Finance
e selezionando per ogni giorno il titolo con il pattern statisticamente più solido
(analisi de-trendizzata + t-test).

Il file `calendario.html` viene rigenerato **automaticamente ogni domenica** da GitHub Actions
e pubblicato su GitHub Pages: il link resta sempre lo stesso.

> Studio statistico retrospettivo a fini informativi/educativi. **Non** è consulenza finanziaria.

---

## ⚙️ Setup (una sola volta, ~5 minuti)

### 1. Crea il repository
- Vai su https://github.com → accedi (o crea un account gratuito).
- In alto a destra: **+** → **New repository**.
- Nome a piacere (es. `calendario-stagionale`), lascialo **Public**, clicca **Create repository**.

### 2. Carica questi file
- Nella pagina del nuovo repository, clicca **"uploading an existing file"**.
- Trascina dentro **tutti** i file di questa cartella, **mantenendo le sottocartelle**:
  ```
  seasonal_all.py
  README.md
  .github/workflows/weekly.yml
  ```
  ⚠️ La cartella `.github/workflows/` deve essere caricata così com'è (GitHub la riconosce da sola
  se trascini l'intera struttura; in alternativa crea i file col pulsante "Create new file" e scrivi
  il percorso `.github/workflows/weekly.yml` nel nome).
- Clicca **Commit changes**.

### 3. Attiva GitHub Pages
- Nel repository: **Settings** → **Pages** (menu a sinistra).
- Alla voce **Source**, scegli **GitHub Actions**. Salva.

### 4. Attiva ed esegui la prima volta
- Vai nella scheda **Actions** del repository.
- Se chiede di abilitare i workflow, clicca **"I understand my workflows, enable them"**.
- Seleziona **"Calendario Stagionale Settimanale"** → **Run workflow** → **Run workflow**.
- Attendi ~2 minuti (diventa verde ✅).

### 5. Apri il tuo calendario
- Il link sarà: `https://TUONOME.github.io/calendario-stagionale/`
  (lo trovi anche in **Settings → Pages**, in alto, dopo il primo deploy).
- **Salvalo nei preferiti**: da qui in poi si aggiorna da solo ogni domenica.

---

## Come cambiarlo
- **Paniere titoli**: modifica la lista `BASKET` in cima a `seasonal_all.py`.
- **Orario/giorno**: modifica la riga `cron:` in `.github/workflows/weekly.yml`
  (formato UTC; `0 16 * * 0` = domenica 16:00 UTC).
- Dopo ogni modifica, il workflow si riesegue e ripubblica.

## Fonte dati
Yahoo Finance (prezzi giornalieri *adjusted*, ~25 anni di storico).
