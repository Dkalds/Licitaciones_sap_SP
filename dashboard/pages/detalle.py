"""Página Detalle — tabla completa y vista expandida."""

from __future__ import annotations

import streamlit as st

from dashboard.components.states import guarded_render
from dashboard.components.tables import data_table
from dashboard.data_loader import load_adjudicaciones
from dashboard.pages._base import PageContext
from dashboard.stats import risk_flags
from dashboard.utils.export import to_excel_bytes
from dashboard.utils.format import fmt_eur


@guarded_render
def render(ctx: PageContext) -> None:
    df = ctx.df

    # ── Flags de riesgo ───────────────────────────────────────────────────────
    # Calculados sobre df_full para tener contexto histórico completo (CPV P10, monopolio…)
    try:
        adj_rf = load_adjudicaciones()
        rf = risk_flags(ctx.df_full, adj_rf)
        df = df.merge(
            rf[["id_externo", "riesgo_flags", "riesgo_score"]], on="id_externo", how="left"
        )
        df["riesgo_flags"] = df["riesgo_flags"].fillna("")
        df["riesgo_score"] = df["riesgo_score"].fillna(0).astype(int)
    except Exception:
        df = df.copy()
        df["riesgo_flags"] = ""
        df["riesgo_score"] = 0

    st.subheader(f"Detalle de licitaciones ({len(df)})")
    st.caption(
        "Plataforma de Contratación del Sector Público — reutilización al amparo de la Ley 37/2007"
    )

    cdl1, cdl2 = st.columns([1, 6])
    with cdl1:
        st.download_button(
            "⬇️ Excel",
            data=to_excel_bytes(df),
            file_name="licitaciones_sap.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with cdl2:
        st.download_button(
            "⬇️ CSV",
            data=df.drop(columns=["modulos"]).to_csv(index=False).encode("utf-8-sig"),
            file_name="licitaciones_sap.csv",
            mime="text/csv",
        )

    cols = [
        "fecha_publicacion",
        "titulo",
        "organo_contratacion",
        "ccaa",
        "importe",
        "moneda",
        "estado_desc",
        "tipo_proyecto",
        "modulos_str",
        "cpv_desc",
        "riesgo_flags",
        "url",
    ]
    cols = [c for c in cols if c in df.columns]
    show = df[cols].sort_values("fecha_publicacion", ascending=False)

    data_table(
        show,
        height=600,
        column_config={
            "fecha_publicacion": st.column_config.DatetimeColumn("Fecha", format="DD-MM-YYYY"),
            "titulo": st.column_config.TextColumn("Título", width="large"),
            "organo_contratacion": st.column_config.TextColumn("Órgano", width="medium"),
            "ccaa": st.column_config.TextColumn("CCAA", width="small"),
            "importe": st.column_config.NumberColumn("Importe", format="%.0f €"),
            "estado_desc": st.column_config.TextColumn("Estado"),
            "tipo_proyecto": st.column_config.TextColumn("Tipo"),
            "modulos_str": st.column_config.TextColumn("Módulos"),
            "cpv_desc": st.column_config.TextColumn("CPV"),
            "riesgo_flags": st.column_config.TextColumn("⚠️ Riesgo", width="medium"),
            "url": st.column_config.LinkColumn("Enlace", display_text="🔗"),
        },
    )

    st.divider()
    st.subheader("🔎 Vista expandida (clic para ver descripción completa)")
    for _, row in df.sort_values("fecha_publicacion", ascending=False).head(20).iterrows():
        with st.expander(f"💼 {fmt_eur(row['importe'])} — {row['titulo'][:90]}"):
            cE1, cE2 = st.columns([2, 1])
            with cE1:
                st.markdown(f"**Órgano:** {row.get('organo_contratacion', '—')}")
                st.markdown(
                    f"**Estado:** {row.get('estado_desc', '—')} · "
                    f"**Tipo proyecto:** {row.get('tipo_proyecto', '—')}"
                )
                st.markdown(f"**Módulos SAP detectados:** {row.get('modulos_str', '—')}")
                st.markdown(f"**CPV:** {row.get('cpv_desc', '—')}")
                st.markdown(
                    f"**Provincia / CCAA:** {row.get('provincia', '—')} · {row.get('ccaa', '—')}"
                )
                st.markdown("**Descripción:**")
                st.write(row.get("descripcion") or "—")
            with cE2:
                st.metric("Importe", fmt_eur(row["importe"]))
                flags_txt = row.get("riesgo_flags", "")
                if flags_txt:
                    st.markdown(f"**⚠️ Alertas:** {flags_txt}")
                else:
                    st.markdown("**✅ Sin alertas de riesgo**")
                if row.get("url"):
                    st.link_button(
                        "📄 Ver licitación oficial", row["url"], use_container_width=True
                    )
