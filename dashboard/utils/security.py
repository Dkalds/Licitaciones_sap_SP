from __future__ import annotations


def safe_url(url: str | None) -> str:
    """Devuelve la URL solo si usa esquema http/https; en caso contrario devuelve "#".

    Previene la inyección de esquemas peligrosos como ``javascript:`` o ``data:``.
    No realiza validación de dominio: la responsabilidad de que el destino sea
    legítimo recae en el código que genera la URL (p. ej. solo deben pasarse
    URLs procedentes de la API de PLACE, nunca de entrada libre del usuario).
    """
    if not url or not isinstance(url, str):
        return "#"
    stripped = url.strip()
    if stripped.lower().startswith(("http://", "https://")):
        return stripped
    return "#"
