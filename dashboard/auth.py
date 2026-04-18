"""Autenticación del dashboard — login con contraseña única."""
from __future__ import annotations

import hmac

import streamlit as st

from config import DASHBOARD_PASSWORD


def _get_password() -> str:
    """Lee la contraseña desde st.secrets (Cloud) o config.py (.env / local)."""
    try:
        return st.secrets.get("DASHBOARD_PASSWORD", "") or DASHBOARD_PASSWORD
    except FileNotFoundError:
        return DASHBOARD_PASSWORD


def check_password() -> bool:
    """Muestra pantalla de login si hay contraseña configurada.

    Detiene la ejecución con `st.stop()` si el usuario no está autenticado.
    Devuelve True si no hay contraseña o ya está autenticado.
    """
    password = _get_password()
    if not password:
        return True
    if st.session_state.get("authenticated"):
        return True

    st.markdown("### 🔒 Acceso restringido")
    pwd = st.text_input("Contraseña", type="password", key="login_pwd")
    if st.button("Entrar", type="primary"):
        if hmac.compare_digest(pwd, password):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    st.stop()
