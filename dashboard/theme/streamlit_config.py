"""Generador offline de `.streamlit/config.toml` desde los design tokens.

Ejecutar como:

    python -m dashboard.theme.streamlit_config

El resultado incluye un banner indicando que el archivo es un output
generado; editar a mano se perderá en la próxima regeneración.
"""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from dashboard.theme.tokens import TOKENS, Tokens


CONFIG_PATH = Path(__file__).resolve().parents[2] / ".streamlit" / "config.toml"

BANNER = (
    "# ─────────────────────────────────────────────────────────────\n"
    "# Archivo GENERADO desde dashboard/theme/tokens.py.\n"
    "# No editar a mano: se sobrescribe al ejecutar:\n"
    "#   python -m dashboard.theme.streamlit_config\n"
    "# ─────────────────────────────────────────────────────────────\n"
)


def render_config(t: Tokens = TOKENS) -> str:
    c = t.colors
    return BANNER + dedent(f"""
        [theme]
        base = "dark"
        primaryColor = "{c.st_primary}"
        backgroundColor = "{c.bg_base}"
        secondaryBackgroundColor = "{c.st_bg_widget}"
        textColor = "{c.st_text}"
        font = "sans serif"

        [server]
        headless = true

        [browser]
        gatherUsageStats = false
    """).lstrip()


def main() -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(render_config(), encoding="utf-8")
    print(f"Escrito: {CONFIG_PATH}")


if __name__ == "__main__":
    main()
