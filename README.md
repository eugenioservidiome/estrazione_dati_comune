# Estrazione Dati Comune

Notebook Google Colab per l'estrazione automatica di dati mancanti da CSV di Comuni italiani.

## Descrizione

Questo progetto fornisce un notebook Jupyter (Google Colab) completo per:

1. **Montare Google Drive** e leggere CSV da `/content/drive/MyDrive/vigone_csv/`
2. **Crawling del sito comunale** con parsing di robots.txt, sitemap.xml e download PDF
3. **Generazione automatica di query** (8-20 per cella mancante) usando template avanzati con operatori Google (site:, filetype:, inurl:, ecc.)
4. **Retrieval documenti** tramite indicizzazione TF-IDF locale
5. **Estrazione valori** e compilazione automatica dei CSV
6. **Salvataggio tracciabilità** con fonti, snippet e audit completo delle query

## File Principale

**`estrazione_dati_comune.ipynb`** - Notebook Google Colab completo (20 celle)

## Caratteristiche Principali

### QueryBuilder Automatico
- **23 categorie interne** di template query (Delibere CC/GC, Sedute, Personale, Patrimonio, Rifiuti, ecc.)
- **7 categorie esterne** per fonti ufficiali (ISTAT, ISPRA, MEF, BDAP) - solo se abilitato
- **104+ template totali** con placeholder dinamici
- **Priorità automatica** (1-10) basata su specificity e affidabilità

### Funzionalità Avanzate
- Parsing robusto CSV con detection automatica colonne anno e sezioni
- Estrazione testo da HTML (trafilatura) e PDF (pdfplumber)
- Matching fuzzy e ranking documenti con cosine similarity
- Supporto formati italiani (numeri, valute, percentuali)
- Gestione anni target: **2023 e 2024** (YEARS_TO_FILL)

### Output Generati
Tutti salvati in `/content/drive/MyDrive/vigone_output/`:

1. **`*_filled.csv`** - CSV originali con celle compilate
2. **`sources_long.csv`** - Tracciabilità completa (URL fonte + snippet per ogni valore)
3. **`queries_generated.csv`** - Audit di tutte le query generate (input_file, section, row_label, col_year, query, priority, notes)
4. **`run_report.md`** - Report di esecuzione con coverage e item NOT_FOUND

## Utilizzo

### 1. Aprire in Google Colab
Carica il file `estrazione_dati_comune.ipynb` su Google Colab.

### 2. Input Richiesti
Il notebook richiederà:
- **`base_url`**: URL del sito Comune (es. `https://comune.vigone.to.it/`)
- **`nome_comune`**: Nome del comune (es. "Vigone") - facoltativo
- **`ALLOW_EXTERNAL_OFFICIAL`**: `True` per abilitare fonti esterne ufficiali (ISTAT, MEF, ISPRA), `False` (default) per usare solo dominio comunale

**Nota**: `YEARS_TO_FILL = [2023, 2024]` è hardcodato nel notebook.

### 3. Esecuzione
Esegui tutte le celle in sequenza. Il notebook:
1. Monta Google Drive
2. Esegue crawling del sito
3. Processa tutti i CSV trovati
4. Salva gli output

## Requisiti Tecnici

### Librerie Python
- pandas
- requests
- beautifulsoup4
- trafilatura
- scikit-learn
- rapidfuzz
- pdfplumber
- tqdm
- lxml

Tutte installate automaticamente nella cella di setup.

### Struttura Directory Google Drive

```
/content/drive/MyDrive/
├── vigone_csv/          # INPUT: CSV da elaborare
│   ├── cartel1.csv
│   ├── cartel2.csv
│   └── ...
└── vigone_output/       # OUTPUT: risultati (creata automaticamente)
    ├── cartel1_filled.csv
    ├── cartel2_filled.csv
    ├── sources_long.csv
    ├── queries_generated.csv
    └── run_report.md
```

## Categorie Query Supportate

### A) Governo
- Deliberazioni Consiglio/Giunta Comunale
- Sedute Consiglio/Giunta
- Personale/Dipendenti
- Struttura organizzativa/Organigramma
- Servizio Civile
- Fasce età/genere personale

### B) Territorio e Popolazione (con ISTAT se abilitato)
- Popolazione residente
- Nati/Morti
- Stranieri residenti

### C) Risultati Economici
- Patrimonio netto
- Debiti
- Risultato economico
- Investimenti per Missione

### D) Servizi Civici
- Polizia Locale
- Art. 208 CDS
- Edilizia (CILA, SCIA, PDC)
- Manutenzioni
- Biblioteca

### E) Rifiuti Urbani
- Raccolta differenziata totale
- Frazioni specifiche (umido, carta, vetro, plastica, ecc.)
- Con supporto ISPRA se abilitato

### F) Progetti
- PNRR
- Opere pubbliche
- Programma triennale

## Sicurezza e Privacy

- **NO API a pagamento** (solo crawling locale + TF-IDF)
- **Scope fonti controllato**: di default solo dominio comunale
- **Fonti esterne limitate**: solo ufficiali (ISTAT, MEF, ISPRA, BDAP) se esplicitamente abilitato
- **Tracciabilità completa**: ogni valore estratto è linkato alla fonte

## Limitazioni

- Richiede Google Colab (o Jupyter con Google Drive montato)
- Performance dipende da dimensione sito e numero CSV
- Estrazione valore basata su pattern: può richiedere validazione manuale
- Crawling può essere lento per siti molto grandi (default max 500 pagine)

## Contributi

Questo è un progetto per l'estrazione dati da siti della Pubblica Amministrazione italiana. Ogni contributo per migliorare accuracy, template query o gestione edge case è benvenuto.

## Licenza

Progetto open source per scopi di trasparenza e civic tech.