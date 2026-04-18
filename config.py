"""Configuración global del proyecto."""
import os
from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data"))
DOWNLOADS_DIR = DATA_DIR / "downloads"
DB_PATH = Path(os.environ.get("DB_PATH", DATA_DIR / "licitaciones.db"))

DATA_DIR.mkdir(exist_ok=True)
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Palabras clave para filtrar licitaciones SAP
SAP_KEYWORDS = [
    "sap",
    "s/4hana",
    "s4hana",
    "hana",
    "abap",
    "fiori",
    "successfactors",
    "ariba",
    "concur",
    "netweaver",
    "bw/4hana",
    "sap erp",
    "sap basis",
    "sap mm",
    "sap fi",
    "sap co",
    "sap sd",
    "sap hcm",
    "sap pi",
    "sap po",
    "sap pm",
    "sap ps",
    "sap qm",
    "sap wm",
    "sap ewm",
    "sap tm",
    "SAP SSM",
    "sap srm",
    "sap crm",
    "sap bi",
    "sap bo",
    "sap solution manager",
    "businessobjects",
]

# CPV codes relevantes (servicios TI / software)
CPV_PREFIXES_TI = [
    "72",   # Servicios TI
    "48",   # Paquetes de software
]

# URL base de la Plataforma de Contratación
PLACE_BASE_URL = "https://contrataciondelestado.es"
PLACE_SYNDICATION_BASE = f"{PLACE_BASE_URL}/sindicacion"

# Endpoint de búsqueda (form-based)
PLACE_SEARCH_URL = (
    f"{PLACE_BASE_URL}/wps/portal/plataforma/buscadores/busqueda/"
)

# User agent identificable (buena práctica scraping ético)
USER_AGENT = (
    "LicitacionesSAP-Bot/1.0 "
    "(+contacto: usuario@ejemplo.com; uso: análisis estadístico, "
    "datos abiertos Ley 37/2007)"
)

REQUEST_TIMEOUT = 30
REQUEST_DELAY_SECONDS = 1.5  # delay entre requests para no saturar
