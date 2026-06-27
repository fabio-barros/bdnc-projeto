from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


ROOT = Path("tmp/colab_smoke")
RAW_ZIP_DIR = ROOT / "data" / "raw" / "zip"
PROCESSED_DIR = ROOT / "data" / "processed"
ANALYTICS_DIR = ROOT / "data" / "analytics"
DOCS_DIR = ROOT / "docs"
DUCKDB_PATH = ROOT / "data" / "vacinabr_pni.duckdb"

UF_TO_REGION = {
    "SP": "Sudeste",
    "MG": "Sudeste",
    "BA": "Nordeste",
}

SENSITIVE_COLUMNS = ["codigo_paciente", "numero_cep_paciente"]
ESSENTIAL_COLUMNS = [
    "data_vacina",
    "sexo_paciente",
    "numero_idade_paciente",
    "uf_paciente",
    "codigo_municipio_paciente",
    "codigo_vacina",
    "sg_vacina",
]
ALIASES = {
    "sigla_uf_paciente": "uf_paciente",
    "sigla_uf_estabelecimento": "uf_estabelecimento",
    "sigla_vacina": "sg_vacina",
    "tipo_sexo_paciente": "sexo_paciente",
    "status_documento": "st_documento",
}


def normalize_column_name(column: str) -> str:
    column = str(column).strip().lower()
    column = re.sub(r"[^a-z0-9_]+", "_", column)
    return re.sub(r"_+", "_", column).strip("_")


def normalize_text(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.strip()
        .str.upper()
        .replace({"": pd.NA, "NAN": pd.NA, "NONE": pd.NA, "NULL": pd.NA})
    )


def age_group(age: Any) -> str | None:
    if pd.isna(age):
        return None

    age_int = int(age)

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


def transform_chunk(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [normalize_column_name(c) for c in df.columns]
    df = df.rename(
        columns={
            source: target
            for source, target in ALIASES.items()
            if source in df.columns and target not in df.columns
        }
    )

    df["data_vacina"] = pd.to_datetime(df["data_vacina"], errors="coerce")
    df["numero_idade_paciente"] = pd.to_numeric(
        df["numero_idade_paciente"],
        errors="coerce",
    )

    for col in [
        "sexo_paciente",
        "uf_paciente",
        "uf_estabelecimento",
        "sg_vacina",
        "descricao_vacina_fabricante",
        "st_documento",
    ]:
        df[col] = normalize_text(df[col])

    for col in [
        "codigo_municipio_paciente",
        "codigo_municipio_estabelecimento",
        "codigo_vacina",
    ]:
        df[col] = df[col].astype("string").str.strip().replace({"": pd.NA})

    df["registro_deletado_rnds"] = df["data_deletado_rnds"].notna()
    df["documento_final"] = df["st_documento"].fillna("").str.upper().eq("FINAL")
    df["registro_valido_documento"] = (
        df["documento_final"] & (~df["registro_deletado_rnds"])
    )
    df["ano_vacinacao"] = df["data_vacina"].dt.year.astype("Int64")
    df["mes_vacinacao"] = df["data_vacina"].dt.month.astype("Int64")
    df["trimestre_vacinacao"] = (
        "Q" + df["data_vacina"].dt.quarter.astype("Int64").astype("string")
    )
    df["semana_epidemiologica"] = (
        df["data_vacina"].dt.isocalendar().week.astype("Int64")
    )
    df["idade_valida"] = df["numero_idade_paciente"].between(0, 130)
    df["faixa_etaria"] = df["numero_idade_paciente"].apply(age_group)
    df["regiao_paciente"] = df["uf_paciente"].map(UF_TO_REGION).fillna(
        "Nao informado"
    )
    df["regiao_estabelecimento"] = df["uf_estabelecimento"].map(UF_TO_REGION).fillna(
        "Nao informado"
    )
    df["municipio_paciente_igual_estabelecimento"] = (
        df["codigo_municipio_paciente"] == df["codigo_municipio_estabelecimento"]
    )
    df["registro_completo"] = df[ESSENTIAL_COLUMNS].notna().all(axis=1)
    return df.drop(columns=SENSITIVE_COLUMNS, errors="ignore")


def create_fixture_zip() -> Path:
    RAW_ZIP_DIR.mkdir(parents=True, exist_ok=True)
    fixture_csv = RAW_ZIP_DIR / "vacinacao_jan_2025_sample.csv"
    fixture_zip = RAW_ZIP_DIR / "vacinacao_jan_2025_sample_csv.zip"

    sample = pd.DataFrame(
        [
            {
                "data_vacina": "2025-01-10 00:00:00-03",
                "tipo_sexo_paciente": "F",
                "numero_idade_paciente": "34",
                "sigla_uf_paciente": "SP",
                "codigo_municipio_paciente": "355030",
                "sigla_uf_estabelecimento": "SP",
                "codigo_municipio_estabelecimento": "355030",
                "codigo_vacina": "24",
                "sigla_vacina": "SCR",
                "descricao_vacina_fabricante": "FIOCRUZ",
                "status_documento": "final",
                "data_deletado_rnds": None,
                "codigo_paciente": "hash-paciente-1",
                "numero_cep_paciente": "01000",
            },
            {
                "data_vacina": "2025-01-11 00:00:00-03",
                "tipo_sexo_paciente": "M",
                "numero_idade_paciente": "70",
                "sigla_uf_paciente": "MG",
                "codigo_municipio_paciente": "310620",
                "sigla_uf_estabelecimento": "MG",
                "codigo_municipio_estabelecimento": "310620",
                "codigo_vacina": "25",
                "sigla_vacina": "VIP",
                "descricao_vacina_fabricante": "BUTANTAN",
                "status_documento": "final",
                "data_deletado_rnds": None,
                "codigo_paciente": "hash-paciente-2",
                "numero_cep_paciente": "30100",
            },
        ]
    )

    sample.to_csv(fixture_csv, index=False)

    with zipfile.ZipFile(fixture_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(fixture_csv, arcname=fixture_csv.name)

    return fixture_zip


def main() -> None:
    for path in [PROCESSED_DIR, ANALYTICS_DIR, DOCS_DIR]:
        path.mkdir(parents=True, exist_ok=True)

    fixture_zip = create_fixture_zip()

    with zipfile.ZipFile(fixture_zip) as zf:
        member = [name for name in zf.namelist() if name.endswith(".csv")][0]
        with zf.open(member) as file:
            chunk = pd.read_csv(file, dtype="string")

    processed = transform_chunk(chunk)
    out_dir = PROCESSED_DIR / "year=2025" / "month=01"
    out_dir.mkdir(parents=True, exist_ok=True)
    processed.to_parquet(out_dir / "part-000000.parquet", index=False)

    validation = pd.DataFrame(
        [
            {
                "metric": "original_records",
                "value": len(chunk),
                "description": "Registros brutos no teste local.",
            },
            {
                "metric": "processed_records",
                "value": len(processed),
                "description": "Registros processados no teste local.",
            },
        ]
    )
    validation.to_csv(DOCS_DIR / "validation_report.csv", index=False)

    parquet_pattern = str(PROCESSED_DIR / "year=*" / "month=*" / "*.parquet")
    con = duckdb.connect(str(DUCKDB_PATH))
    con.execute(
        f"""
        CREATE OR REPLACE VIEW vacinacao_curada AS
        SELECT *
        FROM read_parquet('{parquet_pattern}', union_by_name = true)
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE state_vaccination_summary AS
        SELECT uf_paciente, count(*) AS doses_aplicadas
        FROM vacinacao_curada
        GROUP BY uf_paciente
        ORDER BY doses_aplicadas DESC
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE dataset_metadata AS
        SELECT 'VacinaBR-PNI' AS dataset, count(*) AS total_records
        FROM vacinacao_curada
        """
    )

    catalog = {
        "database": str(DUCKDB_PATH),
        "source_parquet_pattern": parquet_pattern,
        "view": "vacinacao_curada",
    }
    with (DOCS_DIR / "duckdb_catalog.json").open("w", encoding="utf-8") as file:
        json.dump(catalog, file, ensure_ascii=False, indent=2)

    print(con.sql("SELECT * FROM dataset_metadata").df().to_string(index=False))
    print(con.sql("SELECT * FROM state_vaccination_summary").df().to_string(index=False))
    con.close()
    print(f"[smoke] OK root={ROOT}")


if __name__ == "__main__":
    main()
