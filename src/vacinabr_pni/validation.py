from __future__ import annotations

from typing import Any

import pandas as pd


def build_validation_report(
    df: pd.DataFrame,
    original_rows: int,
    duplicated_before: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(metric: str, value: Any, description: str) -> None:
        rows.append(
            {
                "metric": metric,
                "value": value,
                "description": description,
            }
        )

    add(
        "original_records",
        original_rows,
        "Quantidade de registros antes da transformacao.",
    )

    add(
        "processed_records",
        len(df),
        "Quantidade de registros apos transformacao e deduplicacao.",
    )

    add(
        "removed_duplicate_records",
        duplicated_before,
        "Duplicatas removidas pelo pipeline.",
    )

    add(
        "total_columns",
        len(df.columns),
        "Quantidade de colunas na versao processada.",
    )

    add(
        "total_missing_values",
        int(df.isna().sum().sum()),
        "Total de valores ausentes na versao processada.",
    )

    if "idade_valida" in df.columns:
        add(
            "invalid_age_records",
            int((~df["idade_valida"].fillna(False)).sum()),
            "Registros com idade ausente ou fora do intervalo esperado.",
        )

    if "data_vacina" in df.columns:
        add(
            "invalid_date_records",
            int(df["data_vacina"].isna().sum()),
            "Registros com data de vacinacao invalida ou ausente.",
        )

    if "registro_completo" in df.columns:
        add(
            "complete_records",
            int(df["registro_completo"].sum()),
            "Registros com todos os campos essenciais preenchidos.",
        )

        add(
            "incomplete_records",
            int((~df["registro_completo"].fillna(False)).sum()),
            "Registros com algum campo essencial ausente.",
        )

    if "registro_valido_documento" in df.columns:
        add(
            "valid_document_records",
            int(df["registro_valido_documento"].sum()),
            "Registros finais e nao deletados na RNDS.",
        )

        add(
            "invalid_document_records",
            int((~df["registro_valido_documento"].fillna(False)).sum()),
            "Registros nao finais ou deletados na RNDS.",
        )

    fields_to_check = [
        "data_vacina",
        "sexo_paciente",
        "numero_idade_paciente",
        "uf_paciente",
        "codigo_municipio_paciente",
        "sg_vacina",
        "descricao_vacina_fabricante",
    ]

    for column in fields_to_check:
        if column in df.columns:
            add(
                f"missing_{column}",
                int(df[column].isna().sum()),
                f"Valores ausentes na coluna {column}.",
            )

    return pd.DataFrame(rows)
