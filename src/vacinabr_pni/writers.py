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
        ("data_vacina", "date", "Data de aplicacao da vacina."),
        ("ano_vacinacao", "integer", "Ano extraido da data de vacinacao."),
        ("mes_vacinacao", "integer", "Mes extraido da data de vacinacao."),
        ("trimestre_vacinacao", "string", "Trimestre da vacinacao."),
        (
            "semana_epidemiologica",
            "integer",
            "Semana epidemiologica estimada a partir da data de vacinacao.",
        ),
        ("sexo_paciente", "string", "Sexo informado do paciente."),
        ("numero_idade_paciente", "number", "Idade informada do paciente."),
        ("faixa_etaria", "string", "Faixa etaria derivada da idade."),
        (
            "idade_valida",
            "boolean",
            "Indica se a idade esta no intervalo esperado de 0 a 130 anos.",
        ),
        ("uf_paciente", "string", "Unidade federativa do paciente."),
        (
            "regiao_paciente",
            "string",
            "Regiao geografica derivada da UF do paciente.",
        ),
        ("codigo_municipio_paciente", "string", "Codigo do municipio do paciente."),
        ("nome_municipio_paciente", "string", "Nome do municipio do paciente."),
        ("uf_estabelecimento", "string", "Unidade federativa do estabelecimento."),
        (
            "razao_social_estabelecimento",
            "string",
            "Razao social do estabelecimento de saude.",
        ),
        (
            "nome_fantasia_estabelecimento",
            "string",
            "Nome fantasia do estabelecimento de saude.",
        ),
        (
            "regiao_estabelecimento",
            "string",
            "Regiao geografica derivada da UF do estabelecimento.",
        ),
        (
            "codigo_municipio_estabelecimento",
            "string",
            "Codigo do municipio do estabelecimento.",
        ),
        (
            "municipio_paciente_igual_estabelecimento",
            "boolean",
            "Indica se paciente e estabelecimento pertencem ao mesmo municipio.",
        ),
        ("codigo_vacina", "string", "Codigo da vacina."),
        ("sg_vacina", "string", "Sigla da vacina ou imunobiologico."),
        ("descricao_dose_vacina", "string", "Descricao da dose aplicada."),
        ("codigo_lote_vacina", "string", "Codigo do lote da vacina."),
        (
            "descricao_vacina_fabricante",
            "string",
            "Fabricante informado da vacina.",
        ),
        (
            "descricao_estrategia_vacinacao",
            "string",
            "Estrategia de vacinacao informada.",
        ),
        ("descricao_sistema_origem", "string", "Sistema de origem do registro."),
        ("st_documento", "string", "Status documental do registro."),
        (
            "registro_deletado_rnds",
            "boolean",
            "Indica se o registro possui data de delecao na RNDS.",
        ),
        ("documento_final", "boolean", "Indica se o status do documento e final."),
        (
            "registro_valido_documento",
            "boolean",
            "Indica documento final e nao deletado.",
        ),
        (
            "registro_completo",
            "boolean",
            "Indica preenchimento dos campos essenciais.",
        ),
    ]

    df = pd.DataFrame(dictionary, columns=["field", "type", "description"])

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
    save(["sg_vacina"], "vaccine_type_summary.csv")
    save(["descricao_vacina_fabricante"], "manufacturer_summary.csv")
    save(["faixa_etaria"], "age_group_summary.csv")
    save(["sexo_paciente"], "sex_summary.csv")
    save(
        ["ano_vacinacao", "mes_vacinacao", "sg_vacina"],
        "monthly_vaccine_type_summary.csv",
    )
    save(
        ["uf_paciente", "sg_vacina"],
        "state_vaccine_type_summary.csv",
    )
