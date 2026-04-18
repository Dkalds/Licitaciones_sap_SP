from __future__ import annotations


def safe_url(url: str | None) -> str:
    """Valida que la URL use un esquema seguro. Previene javascript: URIs."""
    if not url or not isinstance(url, str):
        return "#"
    stripped = url.strip()
    if stripped.lower().startswith(("http://", "https://")):
        return stripped
    return "#"
