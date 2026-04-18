"""Configuración global del proyecto."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data"))
DOWNLOADS_DIR = DATA_DIR / "downloads"
DB_PATH = Path(os.environ.get("DB_PATH", DATA_DIR / "licitaciones.db"))

# Contraseña para proteger el dashboard (vacío = sin autenticación)
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "")

# Turso (libSQL cloud) — si están definidas, se usa réplica embebida
TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")
# Archivo local distinto para la réplica embebida de Turso
TURSO_LOCAL_DB = Path(os.environ.get(
    "TURSO_LOCAL_DB", DATA_DIR / "licitaciones_replica.db"))

DATA_DIR.mkdir(exist_ok=True)
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Palabras clave para filtrar licitaciones SAP
SAP_KEYWORDS = [
    # Plataforma principal
    "sap",
    "s/4hana",
    "s4hana",
    "s/4 hana",
    "hana",
    "abap",
    "fiori",
    # Módulos funcionales
    "sap erp",
    "sap ecc",
    "sap basis",
    "sap mm",
    "sap fi",
    "sap fi/co",
    "sap co",
    "sap sd",
    "sap hcm",
    "sap hr",
    "sap pi",
    "sap po",
    "sap pm",
    "sap ps",
    "sap qm",
    "sap wm",
    "sap ewm",
    "sap tm",
    "sap srm",
    "sap crm",
    "sap ssm",
    "sap bi",
    "sap bo",
    "sap bw",
    "sap bpc",
    "sap grc",
    "sap mdg",
    "sap mdm",
    "sap isu",
    "sap is-u",
    "sap re-fx",
    "sap refx",
    "sap re/fx",
    "sap apo",
    "sap scm",
    "sap ibp",
    "sap slm",
    "sap clm",
    "sap ariba",
    "sap fieldglass",
    "sap concur",
    "sap analytics cloud",
    "sac sap",
    # Suite cloud
    "successfactors",
    "ariba",
    "concur",
    "fieldglass",
    "sap cx",
    "sap customer experience",
    # Infraestructura / tecnología
    "netweaver",
    "bw/4hana",
    "bw4hana",
    "sap solution manager",
    "solman",
    "businessobjects",
    "business objects",
    "crystal reports",
    "sap oss",
    "sap early watch",
    "sap lumira",
    "sap build",
    "sap integration suite",
    "sap btp",
    "business technology platform",
    "sap cloud platform",
    # Términos genéricos asociados
    "implantación sap",
    "migración sap",
    "mantenimiento sap",
    "soporte sap",
    "consultoría sap",
    "formación sap",
    "licencias sap",
    "upgrade sap",
    "actualización sap",
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
USER_AGENT = "LicitacionesSAP-Bot/1.0"

REQUEST_TIMEOUT = 30
REQUEST_DELAY_SECONDS = 1.5  # delay entre requests para no saturar

# Límites de tamaño para descargas (defensa contra recursos excesivos)
MAX_DOWNLOAD_SIZE_BYTES = 1 * 1024 * 1024 * 1024   # 1 GB por ZIP mensual
MAX_XML_SIZE_BYTES = 500 * 1024 * 1024              # 500 MB por fichero XML
