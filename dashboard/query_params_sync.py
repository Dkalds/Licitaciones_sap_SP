"""Lectura/escritura de filtros activos en la URL (para compartir enlaces)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.filters import FiltersState


def load_initial(df_full: pd.DataFrame) -> None:
    """Hidrata session_state desde query params (solo primera carga)."""
    if "_qp_loaded" in st.session_state:
        return
    init = FiltersState.from_query_params(dict(st.query_params))
    if init.q:
        st.session_state["fs_q"] = init.q
    if init.estados:
        valid = set(df_full["estado_desc"].dropna().unique())
        st.session_state["fs_estados"] = [e for e in init.estados if e in valid]
    if init.ccaas:
        valid = set(df_full["ccaa"].dropna().unique())
        st.session_state["fs_ccaas"] = [c for c in init.ccaas if c in valid]
    if init.organos:
        valid = set(df_full["organo_contratacion"].dropna().unique())
        st.session_state["fs_organos"] = [o for o in init.organos if o in valid]
    if init.tipos_proy:
        valid = set(df_full["tipo_proyecto"].dropna().unique())
        st.session_state["fs_tipos"] = [t for t in init.tipos_proy if t in valid]
    if init.importe_min > 0:
        st.session_state["fs_imp_min"] = init.importe_min
    if init.rango:
        st.session_state["fs_rango"] = init.rango
    st.session_state["_qp_loaded"] = True


def sync_to_url(filters: FiltersState) -> None:
    new_qp = filters.to_query_params()
    cur_qp = dict(st.query_params)
    if cur_qp != new_qp:
        for k in list(cur_qp):
            if k not in new_qp:
                del st.query_params[k]
        st.query_params.update(new_qp)
