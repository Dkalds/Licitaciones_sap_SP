"""Autenticación del dashboard — login con contraseña única."""

from __future__ import annotations

import hmac
import time

import streamlit as st

from config import DASHBOARD_PASSWORD

# Duración máxima de una sesión autenticada (segundos)
SESSION_TIMEOUT_SECONDS = 28_800  # 8 horas

# Número de intentos fallidos antes de activar el lockout
_MAX_ATTEMPTS_BEFORE_LOCKOUT = 3
# Lockout máximo independientemente del número de intentos (segundos)
_MAX_LOCKOUT_SECONDS = 60


def _get_password() -> str:
    """Lee la contraseña desde st.secrets (Cloud) o config.py (.env / local)."""
    try:
        return st.secrets.get("DASHBOARD_PASSWORD", "") or DASHBOARD_PASSWORD
    except FileNotFoundError:
        return DASHBOARD_PASSWORD


def _check_lockout() -> None:
    """Si hay lockout activo, muestra aviso y detiene la ejecución."""
    lockout_until: float = st.session_state.get("_login_lockout_until", 0.0)
    remaining = lockout_until - time.time()
    if remaining > 0:
        st.warning(
            f"Demasiados intentos fallidos. "
            f"Espera {int(remaining) + 1} segundos antes de intentarlo de nuevo."
        )
        st.stop()


def _record_failed_attempt() -> None:
    """Incrementa el contador de intentos y calcula el lockout progresivo."""
    attempts: int = st.session_state.get("_login_attempts", 0) + 1
    st.session_state["_login_attempts"] = attempts
    if attempts >= _MAX_ATTEMPTS_BEFORE_LOCKOUT:
        exponent = attempts - _MAX_ATTEMPTS_BEFORE_LOCKOUT + 1
        delay = min(2**exponent, _MAX_LOCKOUT_SECONDS)
        st.session_state["_login_lockout_until"] = time.time() + delay


def check_password() -> bool:
    """Muestra pantalla de login si hay contraseña configurada.

    Detiene la ejecución con `st.stop()` si el usuario no está autenticado.
    Devuelve True si no hay contraseña o ya está autenticado.
    """
    password = _get_password()
    if not password:
        return True

    # Verificar sesión activa y su timeout
    if st.session_state.get("authenticated"):
        auth_time: float = st.session_state.get("_auth_time", 0.0)
        if time.time() - auth_time < SESSION_TIMEOUT_SECONDS:
            return True
        # Sesión expirada: limpiar estado
        st.session_state.pop("authenticated", None)
        st.session_state.pop("_auth_time", None)
        st.info("Tu sesión ha expirado. Ingresa de nuevo.")

    # Verificar lockout activo por intentos fallidos
    _check_lockout()

    st.markdown("### 🔒 Acceso restringido")
    pwd = st.text_input("Contraseña", type="password", key="login_pwd")
    if st.button("Entrar", type="primary"):
        if hmac.compare_digest(pwd, password):
            st.session_state["authenticated"] = True
            st.session_state["_auth_time"] = time.time()
            st.session_state["_login_attempts"] = 0
            st.session_state.pop("_login_lockout_until", None)
            st.rerun()
        else:
            _record_failed_attempt()
            st.error("Contraseña incorrecta.")
    st.stop()
    return False  # unreachable, but satisfies mypy
