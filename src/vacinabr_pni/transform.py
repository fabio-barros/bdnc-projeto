from __future__ import annotations

import re
from typing import Any

import pandas as pd

from vacinabr_pni.config import (
    CANONICAL_COLUMN_ALIASES,
    ESSENTIAL_COLUMNS,
    SENSITIVE_COLUMNS,
    UF_TO_REGION,
)
from vacinabr_pni.validation import build_validation_report


def normalize_column_name(column: str) -> str:
    column = str(column).strip().lower()
    column = re.sub(r"[^a-z0-9_]+", "_", column)
    column = re.sub(r"_+", "_", column)
    column = column.strip("_")

    if column in {"nome_da_estabelecimento", "nome_da__estabelecimento"}:
        return "nome_uf_estabelecimento"

    return column


def apply_canonical_aliases(df: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        source: target
        for source, target in CANONICAL_COLUMN_ALIASES.items()
        if source in df.columns and target not in df.columns
    }

    return df.rename(columns=aliases)


def normalize_text_series(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.strip()
        .str.upper()
        .replace(
            {
                "": pd.NA,
                "NAN": pd.NA,
                "NONE": pd.NA,
                "NULL": pd.NA,
            }
        )
    )


def age_group(age: Any) -> str | None:
    if pd.isna(age):
        return None

    try:
        age_int = int(age)
    except (TypeError, ValueError):
        return None

    if age_int < 0 or age_int > 130:
        return "idade_invalida"

    if age_int <= 1:
        return "0-1"

    if age_int <= 4:
        return "2-4"

    if age_int <= 11:
        return "5-11"

    if age_int <= 17:
        return "12-17"

    if age_int <= 29:
        return "18-29"

    if age_int <= 39:
        return "30-39"

    if age_int <= 59:
        return "40-59"

    return "60+"


def transform(
    df: pd.DataFrame,
    keep_sensitive: bool,
    only_valid_documents: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    original_rows = len(df)

    df = df.copy()
    df.columns = [normalize_column_name(column) for column in df.columns]
    df = apply_canonical_aliases(df)

    if "data_vacina" in df.columns:
        df["data_vacina"] = pd.to_datetime(df["data_vacina"], errors="coerce")

    if "numero_idade_paciente" in df.columns:
        df["numero_idade_paciente"] = pd.to_numeric(
            df["numero_idade_paciente"],
            errors="coerce",
        )

    text_columns = [
        "sexo_paciente",
        "uf_paciente",
        "uf_estabelecimento",
        "nome_uf_paciente",
        "nome_uf_estabelecimento",
        "nome_municipio_paciente",
        "sg_vacina",
        "descricao_dose_vacina",
        "descricao_vacina_fabricante",
        "descricao_estrategia_vacinacao",
        "descricao_sistema_origem",
        "st_documento",
    ]

    for col in text_columns:
        if col in df.columns:
            df[col] = normalize_text_series(df[col])

    code_columns = [
        "codigo_municipio_paciente",
        "codigo_municipio_estabelecimento",
        "codigo_vacina",
        "codigo_sistema_origem",
    ]

    for col in code_columns:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip().replace({"": pd.NA})

    df["registro_deletado_rnds"] = False

    if "data_deletado_rnds" in df.columns:
        df["registro_deletado_rnds"] = df["data_deletado_rnds"].notna()

    df["documento_final"] = True

    if "st_documento" in df.columns:
        df["documento_final"] = df["st_documento"].fillna("").str.upper().eq("FINAL")

    df["registro_valido_documento"] = (
        df["documento_final"] & (~df["registro_deletado_rnds"])
    )

    if only_valid_documents:
        df = df[df["registro_valido_documento"]].copy()

    if "data_vacina" in df.columns:
        df["ano_vacinacao"] = df["data_vacina"].dt.year.astype("Int64")
        df["mes_vacinacao"] = df["data_vacina"].dt.month.astype("Int64")
        df["trimestre_vacinacao"] = (
            "Q" + df["data_vacina"].dt.quarter.astype("Int64").astype("string")
        )
        df["semana_epidemiologica"] = (
            df["data_vacina"].dt.isocalendar().week.astype("Int64")
        )
    else:
        df["ano_vacinacao"] = pd.NA
        df["mes_vacinacao"] = pd.NA
        df["trimestre_vacinacao"] = pd.NA
        df["semana_epidemiologica"] = pd.NA

    if "numero_idade_paciente" in df.columns:
        df["idade_valida"] = df["numero_idade_paciente"].between(
            0,
            130,
            inclusive="both",
        )
        df["faixa_etaria"] = df["numero_idade_paciente"].apply(age_group)
    else:
        df["idade_valida"] = False
        df["faixa_etaria"] = pd.NA

    if "uf_paciente" in df.columns:
        df["regiao_paciente"] = df["uf_paciente"].map(UF_TO_REGION).fillna(
            "Nao informado"
        )
    else:
        df["regiao_paciente"] = "Nao informado"

    if "uf_estabelecimento" in df.columns:
        df["regiao_estabelecimento"] = df["uf_estabelecimento"].map(
            UF_TO_REGION
        ).fillna("Nao informado")
    else:
        df["regiao_estabelecimento"] = "Nao informado"

    if {"codigo_municipio_paciente", "codigo_municipio_estabelecimento"}.issubset(
        df.columns
    ):
        df["municipio_paciente_igual_estabelecimento"] = (
            df["codigo_municipio_paciente"]
            == df["codigo_municipio_estabelecimento"]
        )
    else:
        df["municipio_paciente_igual_estabelecimento"] = pd.NA

    existing_essential = [
        column for column in ESSENTIAL_COLUMNS if column in df.columns
    ]

    if existing_essential:
        df["registro_completo"] = df[existing_essential].notna().all(axis=1)
    else:
        df["registro_completo"] = False

    dedup_subset = [
        column for column in df.columns if column not in SENSITIVE_COLUMNS
    ]

    duplicated_before = int(df.duplicated(subset=dedup_subset).sum())

    df = df.drop_duplicates(subset=dedup_subset).copy()

    if not keep_sensitive:
        df = df.drop(
            columns=[column for column in SENSITIVE_COLUMNS if column in df.columns],
            errors="ignore",
        )

    validation_rows = build_validation_report(
        df=df,
        original_rows=original_rows,
        duplicated_before=duplicated_before,
    )

    return df, validation_rows
