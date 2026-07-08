from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from vacinabr_pni.config import API_BASE_URL, ENDPOINT_TEMPLATE


def ensure_dirs(data_dir: Path, docs_dir: Path) -> dict[str, Path]:
    paths = {
        "raw": data_dir / "raw",
        "processed": data_dir / "processed",
        "analytics": data_dir / "analytics",
        "docs": docs_dir,
    }

    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)

    return paths


def write_partitions(df: pd.DataFrame, processed_dir: Path) -> None:
    if "ano_vacinacao" not in df.columns or "mes_vacinacao" not in df.columns:
        output = processed_dir / "vacinabr_pni_clean.parquet"
        df.to_parquet(output, index=False)
        print(f"[load] saved {output}")
        return

    valid_partition = df.dropna(
        subset=["ano_vacinacao", "mes_vacinacao"]
    ).copy()

    if valid_partition.empty:
        output = processed_dir / "vacinabr_pni_clean.parquet"
        df.to_parquet(output, index=False)
        print(f"[load] saved {output}")
        return

    for (year, month), group in valid_partition.groupby(
        ["ano_vacinacao", "mes_vacinacao"]
    ):
        output_dir = processed_dir / f"year={int(year)}" / f"month={int(month):02d}"
        output_dir.mkdir(parents=True, exist_ok=True)

        output = output_dir / "vacinabr_pni_clean.parquet"

        group.to_parquet(output, index=False)

        print(f"[load] saved {output} rows={len(group):,}")


def write_schema(df: pd.DataFrame, docs_dir: Path) -> None:
    schema = {
        "dataset": "VacinaBR-PNI",
        "description": (
            "Dataset tratado de doses aplicadas pelo Programa Nacional de "
            "Imunizacoes."
        ),
        "columns": [
            {
                "name": column,
                "pandas_dtype": str(dtype),
            }
            for column, dtype in df.dtypes.items()
        ],
    }

    with (docs_dir / "schema.json").open("w", encoding="utf-8") as file:
        json.dump(schema, file, ensure_ascii=False, indent=2)


def write_source_metadata(
    docs_dir: Path,
    years: list[int],
    page_param: str,
    limit_param: str,
    page_size: int,
) -> None:
    metadata = {
        "dataset": "VacinaBR-PNI",
        "source": "API de Dados Abertos do Ministerio da Saude",
        "source_base_url": API_BASE_URL,
        "endpoint_template": ENDPOINT_TEMPLATE,
        "endpoints": [
            f"{API_BASE_URL}{ENDPOINT_TEMPLATE.format(year=year)}"
            for year in years
        ],
        "years": years,
        "pagination": {
            "page_param": page_param,
            "limit_param": limit_param,
            "page_size": page_size,
            "offset_starts_at_zero": page_param == "offset",
        },
        "sensitive_fields_removed_from_processed": [
            "codigo_paciente",
            "numero_cep_paciente",
        ],
    }

    with (docs_dir / "source_metadata.json").open("w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)


def write_data_dictionary(docs_dir: Path) -> None:
    dictionary = [
        ("data_vacina", "date", "Data de aplicacao da vacina.", "source", "2025-01-14", False),
        ("ano_vacinacao", "integer", "Ano extraido da data de vacinacao.", "derived", "2025", False),
        ("mes_vacinacao", "integer", "Mes extraido da data de vacinacao.", "derived", "1", False),
        ("trimestre_vacinacao", "string", "Trimestre da vacinacao.", "derived", "Q1", False),
        (
            "semana_epidemiologica",
            "integer",
            "Semana epidemiologica estimada a partir da data de vacinacao.",
            "derived",
            "3",
            False,
        ),
        ("sexo_paciente", "string", "Sexo informado do paciente.", "source", "M", False),
        ("numero_idade_paciente", "number", "Idade informada do paciente.", "source", "59", False),
        ("faixa_etaria", "string", "Faixa etaria derivada da idade.", "derived", "40-59", False),
        (
            "idade_valida",
            "boolean",
            "Indica se a idade esta no intervalo esperado de 0 a 130 anos.",
            "derived_quality",
            "true",
            False,
        ),
        ("uf_paciente", "string", "Unidade federativa do paciente.", "source", "SP", False),
        (
            "regiao_paciente",
            "string",
            "Regiao geografica derivada da UF do paciente.",
            "derived",
            "Sudeste",
            False,
        ),
        ("codigo_municipio_paciente", "string", "Codigo do municipio do paciente.", "source", "355030", False),
        ("nome_municipio_paciente", "string", "Nome do municipio do paciente.", "source", "SAO PAULO", False),
        ("uf_estabelecimento", "string", "Unidade federativa do estabelecimento.", "source", "SP", False),
        (
            "razao_social_estabelecimento",
            "string",
            "Razao social do estabelecimento de saude.",
            "source",
            "SECRETARIA MUNICIPAL DE SAUDE",
            False,
        ),
        (
            "nome_fantasia_estabelecimento",
            "string",
            "Nome fantasia do estabelecimento de saude.",
            "source",
            "UBS EXEMPLO",
            False,
        ),
        (
            "regiao_estabelecimento",
            "string",
            "Regiao geografica derivada da UF do estabelecimento.",
            "derived",
            "Sudeste",
            False,
        ),
        (
            "codigo_municipio_estabelecimento",
            "string",
            "Codigo do municipio do estabelecimento.",
            "source",
            "355030",
            False,
        ),
        (
            "municipio_paciente_igual_estabelecimento",
            "boolean",
            "Indica se paciente e estabelecimento pertencem ao mesmo municipio.",
            "derived",
            "true",
            False,
        ),
        ("codigo_vacina", "string", "Codigo da vacina.", "source", "26513", False),
        ("sg_vacina", "string", "Sigla da vacina ou imunobiologico.", "source", "IGHT", False),
        ("descricao_vacina", "string", "Nome/descricao da vacina ou imunobiologico.", "source", "Imunoglobulina humana antitetano", False),
        ("descricao_dose_vacina", "string", "Descricao da dose aplicada.", "source", "1A DOSE", False),
        ("codigo_lote_vacina", "string", "Codigo do lote da vacina.", "source", "P100647543", False),
        (
            "descricao_vacina_fabricante",
            "string",
            "Fabricante informado da vacina.",
            "source",
            "CSL BEHRING",
            False,
        ),
        (
            "descricao_estrategia_vacinacao",
            "string",
            "Estrategia de vacinacao informada.",
            "source",
            "Rotina",
            False,
        ),
        ("descricao_sistema_origem", "string", "Sistema de origem do registro.", "source", "Novo PNI", False),
        ("st_documento", "string", "Status documental do registro.", "source", "FINAL", False),
        (
            "registro_deletado_rnds",
            "boolean",
            "Indica se o registro possui data de delecao na RNDS.",
            "derived_quality",
            "false",
            False,
        ),
        ("documento_final", "boolean", "Indica se o status do documento e final.", "derived_quality", "true", False),
        (
            "registro_valido_documento",
            "boolean",
            "Indica documento final e nao deletado.",
            "derived_quality",
            "true",
            False,
        ),
        (
            "registro_completo",
            "boolean",
            "Indica preenchimento dos campos essenciais.",
            "derived_quality",
            "true",
            False,
        ),
    ]

    df = pd.DataFrame(
        dictionary,
        columns=[
            "field",
            "type",
            "description",
            "source_or_derived",
            "example_value",
            "sensitive",
        ],
    )

    df.to_csv(
        docs_dir / "data_dictionary.csv",
        index=False,
        encoding="utf-8",
    )


def write_analytics(df: pd.DataFrame, analytics_dir: Path) -> None:
    def save(
        group_cols: list[str],
        filename: str,
        extra_aggs: dict[str, tuple[str, str]] | None = None,
    ) -> None:
        existing = [col for col in group_cols if col in df.columns]

        if not existing:
            return

        agg_dict: dict[str, tuple[str, str]] = {
            "doses_aplicadas": (existing[0], "size")
        }

        if extra_aggs:
            agg_dict.update(extra_aggs)

        result = (
            df.groupby(existing, dropna=False)
            .agg(**agg_dict)
            .reset_index()
        )

        result.to_csv(
            analytics_dir / filename,
            index=False,
            encoding="utf-8",
        )

    save(["ano_vacinacao", "mes_vacinacao"], "monthly_vaccination_summary.csv")
    save(["uf_paciente"], "state_vaccination_summary.csv")
    save(["regiao_paciente"], "region_vaccination_summary.csv")
    save(["sg_vacina", "descricao_vacina"], "vaccine_type_summary.csv")
    save(["descricao_vacina_fabricante"], "manufacturer_summary.csv")
    save(["faixa_etaria"], "age_group_summary.csv")
    save(["sexo_paciente"], "sex_summary.csv")
    save(
        ["ano_vacinacao", "mes_vacinacao", "sg_vacina", "descricao_vacina"],
        "monthly_vaccine_type_summary.csv",
    )
    save(
        ["uf_paciente", "sg_vacina", "descricao_vacina"],
        "state_vaccine_type_summary.csv",
    )
    save(
        [
            "uf_paciente",
            "regiao_paciente",
            "codigo_municipio_paciente",
            "nome_municipio_paciente",
        ],
        "municipality_vaccination_summary.csv",
    )
    save(
        [
            "uf_paciente",
            "codigo_municipio_paciente",
            "nome_municipio_paciente",
            "sg_vacina",
            "descricao_vacina",
        ],
        "state_municipality_vaccine_summary.csv",
    )

    def save_quality(group_cols: list[str], filename: str) -> None:
        existing = [col for col in group_cols if col in df.columns]
        required = [
            "registro_completo",
            "idade_valida",
            "registro_valido_documento",
        ]

        if len(existing) != len(group_cols) or not set(required).issubset(df.columns):
            return

        grouped = df.groupby(existing, dropna=False)
        result = grouped.agg(
            total_registros=(existing[0], "size"),
            registros_completos=("registro_completo", "sum"),
            idades_validas=("idade_valida", "sum"),
            documentos_validos=("registro_valido_documento", "sum"),
        ).reset_index()

        result["pct_completude"] = (
            100 * result["registros_completos"] / result["total_registros"]
        ).round(2)
        result["pct_idade_valida"] = (
            100 * result["idades_validas"] / result["total_registros"]
        ).round(2)
        result["pct_documento_valido"] = (
            100 * result["documentos_validos"] / result["total_registros"]
        ).round(2)

        result.to_csv(analytics_dir / filename, index=False, encoding="utf-8")

    save_quality(["ano_vacinacao", "mes_vacinacao"], "quality_by_month.csv")
    save_quality(["uf_paciente"], "quality_by_state.csv")
    save_quality(["sg_vacina", "descricao_vacina"], "quality_by_vaccine.csv")

    vaccine_columns = [
        "codigo_vacina",
        "sg_vacina",
        "descricao_vacina",
    ]
    if set(vaccine_columns).issubset(df.columns):
        vaccine_dictionary = (
            df.groupby(vaccine_columns, dropna=False)
            .size()
            .reset_index(name="registros_observados")
            .sort_values(["sg_vacina", "descricao_vacina", "codigo_vacina"])
        )
        vaccine_dictionary.to_csv(
            analytics_dir / "vaccine_dictionary.csv",
            index=False,
            encoding="utf-8",
        )
