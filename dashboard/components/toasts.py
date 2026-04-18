"""Wrappers de notificaciones — st.toast con iconos semánticos."""
from __future__ import annotations

import streamlit as st


def notify_success(message: str) -> None:
    st.toast(f"✅ {message}", icon="✅")


def notify_error(message: str) -> None:
    st.toast(f"❌ {message}", icon="❌")


def notify_info(message: str) -> None:
    st.toast(f"ℹ️ {message}")
