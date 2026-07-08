from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(page_title="VacinaBR-PNI", layout="wide")


@st.cache_data
def load_csv(analytics_dir: str, name: str) -> pd.DataFrame:
    path = Path(analytics_dir) / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def metric_value(df: pd.DataFrame, column: str) -> str:
    if df.empty or column not in df.columns:
        return "0"
    return f"{int(df[column].sum()):,}".replace(",", ".")


st.title("VacinaBR-PNI")

analytics_dir = st.sidebar.text_input(
    "Pasta dos CSVs analiticos",
    value=str(Path("data") / "analytics"),
)

monthly = load_csv(analytics_dir, "monthly_vaccination_summary.csv")
states = load_csv(analytics_dir, "state_vaccination_summary.csv")
vaccines = load_csv(analytics_dir, "vaccine_type_summary.csv")
quality_state = load_csv(analytics_dir, "quality_by_state.csv")
municipalities = load_csv(analytics_dir, "municipality_vaccination_summary.csv")

total_doses = metric_value(monthly, "doses_aplicadas")
state_count = states["uf_paciente"].nunique() if "uf_paciente" in states else 0
vaccine_count = vaccines["sg_vacina"].nunique() if "sg_vacina" in vaccines else 0

col1, col2, col3 = st.columns(3)
col1.metric("Doses aplicadas", total_doses)
col2.metric("UFs observadas", state_count)
col3.metric("Vacinas observadas", vaccine_count)

tab_overview, tab_quality, tab_municipality = st.tabs(
    ["Visao geral", "Qualidade", "Municipios"]
)

with tab_overview:
    left, right = st.columns(2)

    with left:
        st.subheader("Doses por mes")
        if not monthly.empty:
            monthly = monthly.copy()
            monthly["periodo"] = (
                monthly["ano_vacinacao"].astype(str)
                + "-"
                + monthly["mes_vacinacao"].astype(str).str.zfill(2)
            )
            st.bar_chart(monthly, x="periodo", y="doses_aplicadas")
        else:
            st.info("Arquivo monthly_vaccination_summary.csv nao encontrado.")

    with right:
        st.subheader("Top vacinas")
        if not vaccines.empty:
            label_column = (
                "descricao_vacina"
                if "descricao_vacina" in vaccines.columns
                else "sg_vacina"
            )
            st.bar_chart(
                vaccines.head(15).sort_values("doses_aplicadas"),
                x=label_column,
                y="doses_aplicadas",
            )
        else:
            st.info("Arquivo vaccine_type_summary.csv nao encontrado.")

    st.subheader("Doses por UF")
    if not states.empty:
        st.dataframe(states, use_container_width=True, hide_index=True)

with tab_quality:
    st.subheader("Indicadores por UF")
    if not quality_state.empty:
        st.dataframe(quality_state, use_container_width=True, hide_index=True)

        columns = [
            column
            for column in ["pct_completude", "pct_idade_valida", "pct_documento_valido"]
            if column in quality_state.columns
        ]
        if columns:
            st.bar_chart(
                quality_state.sort_values(columns[0]).head(15),
                x="uf_paciente",
                y=columns,
            )
    else:
        st.info("Arquivo quality_by_state.csv nao encontrado.")

with tab_municipality:
    st.subheader("Municipios")
    if not municipalities.empty:
        uf_options = sorted(municipalities["uf_paciente"].dropna().unique())
        selected_uf = st.selectbox("UF", options=["Todas"] + uf_options)
        filtered = municipalities
        if selected_uf != "Todas":
            filtered = municipalities[municipalities["uf_paciente"] == selected_uf]
        st.dataframe(
            filtered.sort_values("doses_aplicadas", ascending=False).head(100),
            use_container_width=True,
            hide_index=True,
        )
        if {"latitude", "longitude"}.issubset(filtered.columns):
            mapped = filtered.dropna(subset=["latitude", "longitude"])
            if not mapped.empty:
                st.map(mapped, latitude="latitude", longitude="longitude")
    else:
        st.info("Arquivo municipality_vaccination_summary.csv nao encontrado.")
