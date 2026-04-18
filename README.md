# Licitaciones SAP — Sector Público España

Aplicación que extrae automáticamente las licitaciones publicadas en la
**Plataforma de Contratación del Sector Público (PLACSP)** relacionadas
con proyectos **SAP** y muestra estadísticas en un dashboard.

## Arquitectura

```
┌─────────────────────────┐       ┌──────────────────┐
│ PLACSP open data (ZIP)  │──────▶│ scraper/pipeline │
│ hacienda.gob.es         │       │ (descarga+parse) │
└─────────────────────────┘       └────────┬─────────┘
                                           │
                                  filtra SAP keywords
                                           ▼
                                  ┌──────────────────┐
                                  │ SQLite (upsert)  │
                                  └────────┬─────────┘
                                           │
                          ┌────────────────┼─────────────┐
                          ▼                              ▼
                ┌──────────────────┐           ┌──────────────────┐
                │ Task Scheduler   │           │ Streamlit UI     │
                │ (diario 03:00)   │           │ KPIs + gráficos  │
                └──────────────────┘           └──────────────────┘
```

## Estructura

```
licitaciones-sap/
├── config.py                # Keywords SAP, rutas, URLs
├── requirements.txt
├── db/
│   └── database.py          # SQLite + upsert + log de extracciones
├── scraper/
│   ├── bulk_downloader.py   # Descarga ZIPs mensuales del PLACSP
│   ├── codice_parser.py     # Parser ATOM/CODICE (UBL)
│   ├── filters.py           # Detección de keywords SAP
│   └── pipeline.py          # Orquestación end-to-end
├── dashboard/
│   ├── stats.py             # Cálculos (KPIs, agrupaciones)
│   └── app.py               # Streamlit dashboard
├── scheduler/
│   ├── run_update.py        # Entry point para cron/Task Scheduler
│   └── register_task_windows.ps1
└── data/                    # BD SQLite + ZIPs descargados
```

## Instalación

```bash
cd licitaciones-sap
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

## Uso

### 1. Primera carga histórica (ej. desde enero 2024)
```bash
python -m scheduler.run_update --backfill 2024 1
```

### 2. Actualización incremental (últimos 3 meses)
```bash
python -m scheduler.run_update
```
Es **idempotente**: usa upsert por `id_externo`, así que ejecutarlo
varias veces no duplica registros.

### 3. Lanzar el dashboard
```bash
streamlit run dashboard/app.py
```
Abre http://localhost:8501

### 4. Programar actualización automática (Windows)
```powershell
# Como administrador:
.\scheduler\register_task_windows.ps1
```
Esto crea una tarea diaria a las 03:00. Ver en *Programador de tareas*
o:
```powershell
Get-ScheduledTask -TaskName LicitacionesSAP-Update
```

## Personalizar las keywords SAP

Editar `config.py` → `SAP_KEYWORDS`. Por defecto incluye:
SAP, S/4HANA, ABAP, Fiori, SuccessFactors, Ariba, Concur, módulos
funcionales (FI, CO, MM, SD, HCM, …), etc.

## Marco legal

Los datos se reutilizan al amparo de:
- **Ley 37/2007** de reutilización de información del sector público
- **RD 1495/2011**
- **Ley 9/2017** de Contratos del Sector Público

Fuente oficial: Plataforma de Contratación del Sector Público
(https://contrataciondelestado.es).

Esta aplicación **no suplanta** a la fuente oficial; sirve únicamente
para fines de análisis estadístico.

## Limitaciones conocidas

- La URL de los ZIP mensuales (`BULK_URL_TEMPLATE` en
  `scraper/bulk_downloader.py`) puede cambiar; verificar contra
  hacienda.gob.es si fallan las descargas.
- El parser CODICE asume estructura estándar; si algún XML viene
  malformado, los entries problemáticos se loggean y se omiten.
- Los datos de meses muy recientes pueden tardar en publicarse
  (típicamente el ZIP del mes M aparece a mediados del mes M+1).

## Despliegue (Streamlit Cloud + GitHub Actions)

Setup recomendado, gratis y sin servidores:

- **Dashboard** corriendo en [Streamlit Community Cloud](https://share.streamlit.io)
- **Scraping diario** en GitHub Actions, que commitea la BD actualizada
- Streamlit Cloud detecta el push y refresca

### 1. Conectar el repo a Streamlit Cloud
1. https://share.streamlit.io → "New app"
2. Repo: `Dkalds/Licitaciones_SAP_DASHBOARD`, branch `master`
3. Main file path: `dashboard/app.py`
4. Deploy. Se instalará desde `requirements.txt` automáticamente.

### 2. Cron diario en GitHub Actions
Ya configurado en [`.github/workflows/scrape.yml`](.github/workflows/scrape.yml):
- Diario a las 06:00 UTC
- Lanza `python -m scheduler.run_update --months 3`
- Hace `git commit + push` de `data/licitaciones.db` si ha cambiado

Para que el workflow tenga permiso de push:
1. Repo → Settings → Actions → General
2. *Workflow permissions* → seleccionar **Read and write permissions**

Lanzar manualmente: pestaña *Actions* → "Scrape PLACSP daily" → *Run workflow*.

### Limitaciones de este setup
- La BD vive en el repo (público) → cualquiera puede descargarla. Como
  los datos ya son públicos en PLACSP no es problema legal, pero
  conviene saberlo.
- Si la BD supera ~50 MB, GitHub avisa; >100 MB rechaza el push.
  Al ritmo SAP actual (~ +30 licitaciones/mes), tardarías años.
- Cada commit del bot añade peso al historial git. Si crece mucho,
  squash-merge anual o `git lfs` para el `.db`.

## Próximos pasos sugeridos

- Migrar SQLite → Supabase Postgres si crecéis a multi-usuario con
  escritura concurrente.
- Añadir alertas (email/Slack) cuando aparezca una licitación SAP
  por encima de cierto importe.
- Auth (Cloudflare Access / streamlit-authenticator) si pasa a uso
  interno empresa.
