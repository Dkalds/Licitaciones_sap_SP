"""Autenticación del dashboard — password y/o Google OAuth."""

from __future__ import annotations

import hmac
import time
from typing import Any

import streamlit as st

from config import DASHBOARD_PASSWORD, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, OAUTH_REDIRECT_URI

# Duración máxima de una sesión autenticada (segundos)
SESSION_TIMEOUT_SECONDS = 28_800  # 8 horas

# Número de intentos fallidos antes de activar el lockout
_MAX_ATTEMPTS_BEFORE_LOCKOUT = 3
# Lockout máximo independientemente del número de intentos (segundos)
_MAX_LOCKOUT_SECONDS = 60


def oauth_configured() -> bool:
    """True si las credenciales de Google OAuth están configuradas."""
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


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


def _handle_oauth_callback() -> bool:
    """Procesa el callback de OAuth si hay code en query params.

    Returns True si el usuario queda autenticado tras el callback.
    """
    params = st.query_params
    code = params.get("code")
    if not code:
        return False

    import requests  # noqa: S404

    # Intercambiar code por access token
    try:
        resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": OAUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        resp.raise_for_status()
        token_data = resp.json()
    except Exception:
        st.error("Error al autenticar con Google. Inténtalo de nuevo.")
        # Limpiar code de la URL
        st.query_params.clear()
        return False

    # Obtener info del usuario
    try:
        userinfo = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
            timeout=10,
        ).json()
    except Exception:
        st.error("Error al obtener datos del usuario.")
        st.query_params.clear()
        return False

    # Crear/vincular usuario en BD
    from db.users import get_or_create_oauth_user

    user_id = get_or_create_oauth_user(
        email=userinfo.get("email", ""),
        oauth_provider="google",
        oauth_sub=userinfo["sub"],
        display_name=userinfo.get("name"),
    )

    st.session_state["_auth_time"] = time.time()
    st.session_state["_auth_method"] = "oauth"
    st.session_state["_user_id"] = user_id
    st.session_state["_user_email"] = userinfo.get("email", "")
    st.session_state["_user_name"] = userinfo.get("name", "")

    # No marcar authenticated aquí — check_password decide si falta contraseña

    # Registrar acceso OAuth (paso 1)
    from db.users import log_access

    log_access(auth_method="oauth", user_id=user_id, email=userinfo.get("email", ""))

    # Limpiar code/state de la URL
    st.query_params.clear()
    return True


def _show_oauth_button() -> None:
    """Muestra el botón de inicio de sesión con Google."""
    import urllib.parse

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(
        {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": OAUTH_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    st.link_button("🔑 Iniciar sesión con Google", auth_url, use_container_width=True)


def get_current_user() -> dict[str, Any] | None:
    """Devuelve info del usuario autenticado o None.

    Claves: user_id, email, name, auth_method.
    """
    if not st.session_state.get("authenticated"):
        return None
    return {
        "user_id": st.session_state.get("_user_id"),
        "email": st.session_state.get("_user_email", ""),
        "name": st.session_state.get("_user_name", ""),
        "auth_method": st.session_state.get("_auth_method", "password"),
    }


def check_password() -> bool:
    """Autenticación en dos pasos: Google OAuth → contraseña.

    - Si hay OAuth + password: primero Google, luego pide contraseña.
    - Si solo OAuth: solo Google.
    - Si solo password: solo contraseña.
    - Sin nada: acceso libre.

    Detiene la ejecución con ``st.stop()`` si el usuario no está autenticado.
    """
    password = _get_password()
    has_oauth = oauth_configured()

    if not password and not has_oauth:
        return True

    # Verificar sesión completamente autenticada y su timeout
    if st.session_state.get("authenticated"):
        auth_time: float = st.session_state.get("_auth_time", 0.0)
        if time.time() - auth_time < SESSION_TIMEOUT_SECONDS:
            return True
        # Sesión expirada: limpiar estado
        for key in ("authenticated", "_auth_time", "_auth_method",
                     "_user_id", "_user_email", "_user_name",
                     "_oauth_step_done"):
            st.session_state.pop(key, None)
        st.info("Tu sesión ha expirado. Ingresa de nuevo.")

    # Procesar callback OAuth si hay code en la URL
    if has_oauth and _handle_oauth_callback():
        if password:
            # OAuth OK, pero falta contraseña → marcar paso 1 completo
            st.session_state["_oauth_step_done"] = True
        else:
            # Solo OAuth, sin contraseña → autenticado
            st.session_state["authenticated"] = True
        st.rerun()

    # Verificar lockout activo por intentos fallidos
    _check_lockout()

    oauth_done = st.session_state.get("_oauth_step_done", False)

    # ── Paso 2: Contraseña (tras OAuth) ──────────────────────────────
    if has_oauth and password and oauth_done:
        user_name = st.session_state.get("_user_name", "")
        greeting = f"Hola, {user_name}. " if user_name else ""
        st.markdown(f"### 🔒 {greeting}Introduce la contraseña")
        pwd = st.text_input("Contraseña", type="password", key="login_pwd")
        if st.button("Entrar", type="primary"):
            if hmac.compare_digest(pwd, password):
                st.session_state["authenticated"] = True
                st.session_state["_auth_time"] = time.time()
                st.session_state["_auth_method"] = "oauth+password"
                st.session_state["_login_attempts"] = 0
                st.session_state.pop("_login_lockout_until", None)

                from db.users import log_access

                log_access(
                    auth_method="oauth+password",
                    user_id=st.session_state.get("_user_id"),
                    email=st.session_state.get("_user_email"),
                )
                st.rerun()
            else:
                _record_failed_attempt()
                st.error("Contraseña incorrecta.")
        st.stop()
        return False

    # ── Paso 1: Google OAuth ─────────────────────────────────────────
    if has_oauth and not oauth_done:
        st.markdown("### 🔒 Acceso restringido")
        _show_oauth_button()
        st.stop()
        return False

    # ── Solo contraseña (sin OAuth configurado) ──────────────────────
    if password:
        st.markdown("### 🔒 Acceso restringido")
        pwd = st.text_input("Contraseña", type="password", key="login_pwd")
        if st.button("Entrar", type="primary"):
            if hmac.compare_digest(pwd, password):
                st.session_state["authenticated"] = True
                st.session_state["_auth_time"] = time.time()
                st.session_state["_auth_method"] = "password"
                st.session_state["_login_attempts"] = 0
                st.session_state.pop("_login_lockout_until", None)

                from db.users import log_access

                log_access(auth_method="password")
                st.rerun()
            else:
                _record_failed_attempt()
                st.error("Contraseña incorrecta.")

    st.stop()
    return False  # unreachable, but satisfies mypy
