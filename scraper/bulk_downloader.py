"""Descarga y procesa los ficheros mensuales de datos abiertos del PLACSP.

La Plataforma de Contratación del Sector Público publica mensualmente
ficheros ATOM/XML con todas las licitaciones agregadas. Esta es la vía
oficial y recomendada para reutilización (Ley 37/2007).

URL pattern (verificar contra la última publicación oficial):
  https://contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_643/
  licitacionesPerfilesContratanteCompleto3_YYYYMM.zip
"""
from __future__ import annotations

import logging
import time
import zipfile
from pathlib import Path
from typing import Iterator

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from config import (
    DOWNLOADS_DIR,
    MAX_DOWNLOAD_SIZE_BYTES,
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT,
    USER_AGENT,
)

log = logging.getLogger(__name__)

# Rutas base conocidas para los datasets mensuales
BULK_URL_TEMPLATE = (
    "https://contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_643/"
    "licitacionesPerfilesContratanteCompleto3_{year}{month:02d}.zip"
)


@retry(stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=2, min=4, max=30))
def _download(url: str, dest: Path) -> Path:
    log.info("Descargando %s", url)
    headers = {"User-Agent": USER_AGENT}
    with requests.get(url, headers=headers, stream=True,
                      timeout=REQUEST_TIMEOUT) as r:
        r.raise_for_status()
        content_length = r.headers.get("Content-Length")
        if content_length is not None:
            size = int(content_length)
            if size > MAX_DOWNLOAD_SIZE_BYTES:
                raise ValueError(
                    f"Descarga rechazada: Content-Length {size:,} bytes "
                    f"supera el límite de {MAX_DOWNLOAD_SIZE_BYTES:,} bytes."
                )
        with open(dest, "wb") as f:
            downloaded = 0
            for chunk in r.iter_content(chunk_size=8192):
                downloaded += len(chunk)
                if downloaded > MAX_DOWNLOAD_SIZE_BYTES:
                    dest.unlink(missing_ok=True)
                    raise ValueError(
                        f"Descarga abortada: tamaño real supera "
                        f"{MAX_DOWNLOAD_SIZE_BYTES:,} bytes."
                    )
                f.write(chunk)
    return dest


def download_month(year: int, month: int,
                   force: bool = False) -> Path | None:
    """Descarga el ZIP mensual. Devuelve la ruta o None si no existe."""
    url = BULK_URL_TEMPLATE.format(year=year, month=month)
    dest = DOWNLOADS_DIR / f"placsp_{year}{month:02d}.zip"

    if dest.exists() and not force:
        log.info("Ya existe %s, saltando", dest.name)
        return dest

    try:
        time.sleep(REQUEST_DELAY_SECONDS)
        return _download(url, dest)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            log.warning("No publicado aún: %s-%02d", year, month)
            return None
        raise


def iter_xml_files(zip_path: Path) -> Iterator[tuple[str, bytes]]:
    """Itera sobre los XML contenidos en el ZIP descargado."""
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.lower().endswith(".atom") or name.lower().endswith(".xml"):
                with zf.open(name) as f:
                    yield name, f.read()
