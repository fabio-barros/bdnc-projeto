from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import pandas as pd


SUMMARY_QUERIES = {
    "monthly_vaccination_summary": """
        SELECT
            ano_vacinacao,
            mes_vacinacao,
            count(*) AS doses_aplicadas
        FROM vacinacao_curada_geo
        GROUP BY ano_vacinacao, mes_vacinacao
        ORDER BY ano_vacinacao, mes_vacinacao
    """,
    "state_vaccination_summary": """
        SELECT
            uf_paciente,
            count(*) AS doses_aplicadas
        FROM vacinacao_curada_geo
        GROUP BY uf_paciente
        ORDER BY doses_aplicadas DESC
    """,
    "region_vaccination_summary": """
        SELECT
            regiao_paciente,
            count(*) AS doses_aplicadas
        FROM vacinacao_curada_geo
        GROUP BY regiao_paciente
        ORDER BY doses_aplicadas DESC
    """,
    "vaccine_type_summary": """
        SELECT
            sg_vacina,
            descricao_vacina,
            count(*) AS doses_aplicadas
        FROM vacinacao_curada_geo
        GROUP BY sg_vacina, descricao_vacina
        ORDER BY doses_aplicadas DESC
    """,
    "manufacturer_summary": """
        SELECT
            descricao_vacina_fabricante,
            count(*) AS doses_aplicadas
        FROM vacinacao_curada_geo
        GROUP BY descricao_vacina_fabricante
        ORDER BY doses_aplicadas DESC
    """,
    "age_group_summary": """
        SELECT
            faixa_etaria,
            count(*) AS doses_aplicadas
        FROM vacinacao_curada_geo
        GROUP BY faixa_etaria
        ORDER BY doses_aplicadas DESC
    """,
    "sex_summary": """
        SELECT
            sexo_paciente,
            count(*) AS doses_aplicadas
        FROM vacinacao_curada_geo
        GROUP BY sexo_paciente
        ORDER BY doses_aplicadas DESC
    """,
    "monthly_vaccine_type_summary": """
        SELECT
            ano_vacinacao,
            mes_vacinacao,
            sg_vacina,
            descricao_vacina,
            count(*) AS doses_aplicadas
        FROM vacinacao_curada_geo
        GROUP BY ano_vacinacao, mes_vacinacao, sg_vacina, descricao_vacina
        ORDER BY ano_vacinacao, mes_vacinacao, doses_aplicadas DESC
    """,
    "state_vaccine_type_summary": """
        SELECT
            uf_paciente,
            sg_vacina,
            descricao_vacina,
            count(*) AS doses_aplicadas
        FROM vacinacao_curada_geo
        GROUP BY uf_paciente, sg_vacina, descricao_vacina
        ORDER BY uf_paciente, doses_aplicadas DESC
    """,
    "municipality_vaccination_summary": """
        SELECT
            uf_paciente,
            regiao_paciente,
            codigo_municipio_paciente,
            nome_municipio_paciente,
            latitude,
            longitude,
            count(*) AS doses_aplicadas
        FROM vacinacao_curada_geo
        GROUP BY
            uf_paciente,
            regiao_paciente,
            codigo_municipio_paciente,
            nome_municipio_paciente,
            latitude,
            longitude
        ORDER BY doses_aplicadas DESC
    """,
    "state_municipality_vaccine_summary": """
        SELECT
            uf_paciente,
            codigo_municipio_paciente,
            nome_municipio_paciente,
            latitude,
            longitude,
            sg_vacina,
            descricao_vacina,
            count(*) AS doses_aplicadas
        FROM vacinacao_curada_geo
        GROUP BY
            uf_paciente,
            codigo_municipio_paciente,
            nome_municipio_paciente,
            latitude,
            longitude,
            sg_vacina,
            descricao_vacina
        ORDER BY uf_paciente, nome_municipio_paciente, doses_aplicadas DESC
    """,
    "quality_by_month": """
        SELECT
            ano_vacinacao,
            mes_vacinacao,
            count(*) AS total_registros,
            sum(CASE WHEN registro_completo THEN 1 ELSE 0 END) AS registros_completos,
            sum(CASE WHEN idade_valida THEN 1 ELSE 0 END) AS idades_validas,
            sum(CASE WHEN registro_valido_documento THEN 1 ELSE 0 END) AS documentos_validos,
            round(100.0 * sum(CASE WHEN registro_completo THEN 1 ELSE 0 END) / count(*), 2) AS pct_completude,
            round(100.0 * sum(CASE WHEN idade_valida THEN 1 ELSE 0 END) / count(*), 2) AS pct_idade_valida,
            round(100.0 * sum(CASE WHEN registro_valido_documento THEN 1 ELSE 0 END) / count(*), 2) AS pct_documento_valido
        FROM vacinacao_curada_geo
        GROUP BY ano_vacinacao, mes_vacinacao
        ORDER BY ano_vacinacao, mes_vacinacao
    """,
    "quality_by_state": """
        SELECT
            uf_paciente,
            count(*) AS total_registros,
            sum(CASE WHEN registro_completo THEN 1 ELSE 0 END) AS registros_completos,
            sum(CASE WHEN idade_valida THEN 1 ELSE 0 END) AS idades_validas,
            sum(CASE WHEN registro_valido_documento THEN 1 ELSE 0 END) AS documentos_validos,
            round(100.0 * sum(CASE WHEN registro_completo THEN 1 ELSE 0 END) / count(*), 2) AS pct_completude,
            round(100.0 * sum(CASE WHEN idade_valida THEN 1 ELSE 0 END) / count(*), 2) AS pct_idade_valida,
            round(100.0 * sum(CASE WHEN registro_valido_documento THEN 1 ELSE 0 END) / count(*), 2) AS pct_documento_valido
        FROM vacinacao_curada_geo
        GROUP BY uf_paciente
        ORDER BY total_registros DESC
    """,
    "quality_by_vaccine": """
        SELECT
            sg_vacina,
            descricao_vacina,
            count(*) AS total_registros,
            sum(CASE WHEN registro_completo THEN 1 ELSE 0 END) AS registros_completos,
            sum(CASE WHEN idade_valida THEN 1 ELSE 0 END) AS idades_validas,
            sum(CASE WHEN registro_valido_documento THEN 1 ELSE 0 END) AS documentos_validos,
            round(100.0 * sum(CASE WHEN registro_completo THEN 1 ELSE 0 END) / count(*), 2) AS pct_completude,
            round(100.0 * sum(CASE WHEN idade_valida THEN 1 ELSE 0 END) / count(*), 2) AS pct_idade_valida,
            round(100.0 * sum(CASE WHEN registro_valido_documento THEN 1 ELSE 0 END) / count(*), 2) AS pct_documento_valido
        FROM vacinacao_curada_geo
        GROUP BY sg_vacina, descricao_vacina
        ORDER BY total_registros DESC
    """,
    "vaccine_dictionary": """
        SELECT
            codigo_vacina,
            sg_vacina,
            descricao_vacina,
            count(*) AS registros_observados
        FROM vacinacao_curada_geo
        GROUP BY codigo_vacina, sg_vacina, descricao_vacina
        ORDER BY sg_vacina, descricao_vacina, codigo_vacina
    """,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cria uma base DuckDB analitica a partir dos Parquets curados."
    )
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--analytics-dir", default="data/analytics")
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument("--db-path", default="data/vacinabr_pni.duckdb")
    parser.add_argument("--geography-path", default="data_sources/ibge_municipalities.csv")
    return parser.parse_args()


def sql_literal(value: Path | str) -> str:
    return str(value).replace("\\", "/").replace("'", "''")


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def relation_columns(con: duckdb.DuckDBPyConnection, relation: str) -> list[tuple[str, str]]:
    rows = con.execute(f"DESCRIBE {relation}").fetchall()
    return [(str(row[0]), str(row[1])) for row in rows]


def column_names(con: duckdb.DuckDBPyConnection, relation: str) -> list[str]:
    return [name for name, _ in relation_columns(con, relation)]


def scalar(con: duckdb.DuckDBPyConnection, query: str) -> int:
    value = con.execute(query).fetchone()[0]
    return int(value or 0)


def count_missing(
    con: duckdb.DuckDBPyConnection,
    relation: str,
    column: str,
    total_records: int,
) -> int:
    if column not in column_names(con, relation):
        return total_records
    return scalar(
        con,
        f"SELECT count(*) FROM {relation} WHERE {quote_identifier(column)} IS NULL",
    )


def count_true(
    con: duckdb.DuckDBPyConnection,
    relation: str,
    column: str,
) -> int:
    if column not in column_names(con, relation):
        return 0
    return scalar(
        con,
        f"""
        SELECT count(*)
        FROM {relation}
        WHERE coalesce(try_cast({quote_identifier(column)} AS boolean), false)
        """,
    )


def write_schema(con: duckdb.DuckDBPyConnection, docs_dir: Path) -> None:
    schema = {
        "dataset": "VacinaBR-PNI",
        "description": (
            "Dataset curado de doses aplicadas pelo Programa Nacional de "
            "Imunizacoes, gerado a partir dos CSVs mensais do PNI."
        ),
        "columns": [
            {"name": name, "duckdb_type": dtype}
            for name, dtype in relation_columns(con, "vacinacao_curada")
        ],
    }

    with (docs_dir / "schema.json").open("w", encoding="utf-8") as file:
        json.dump(schema, file, ensure_ascii=False, indent=2)


def write_validation_report(
    con: duckdb.DuckDBPyConnection,
    docs_dir: Path,
) -> pd.DataFrame:
    relation = "vacinacao_curada"
    names = column_names(con, relation)
    total_records = scalar(con, f"SELECT count(*) FROM {relation}")
    total_columns = len(names)

    if names:
        present_expr = " + ".join(
            f"count({quote_identifier(column)})::HUGEINT"
            for column in names
        )
        total_missing_values = scalar(
            con,
            f"""
            SELECT
                ({total_records}::HUGEINT * {total_columns}::HUGEINT)
                - ({present_expr})
            FROM {relation}
            """,
        )
    else:
        total_missing_values = 0

    if "numero_idade_paciente" in names:
        invalid_age_records = scalar(
            con,
            f"""
            SELECT count(*)
            FROM {relation}
            WHERE {quote_identifier('numero_idade_paciente')} IS NOT NULL
              AND (
                try_cast({quote_identifier('numero_idade_paciente')} AS double) < 0
                OR try_cast({quote_identifier('numero_idade_paciente')} AS double) > 130
              )
            """,
        )
    else:
        invalid_age_records = 0

    if "data_vacina" in names:
        invalid_date_records = scalar(
            con,
            f"""
            SELECT count(*)
            FROM {relation}
            WHERE {quote_identifier('data_vacina')} IS NULL
            """,
        )
    else:
        invalid_date_records = total_records

    complete_records = count_true(con, relation, "registro_completo")
    valid_document_records = count_true(con, relation, "registro_valido_documento")

    rows = [
        ("original_records", total_records, "original records"),
        ("processed_records", total_records, "processed records"),
        ("removed_duplicate_records", 0, "removed duplicate records"),
        ("total_columns", total_columns, "total columns"),
        ("total_missing_values", total_missing_values, "total missing values"),
        ("invalid_age_records", invalid_age_records, "invalid age records"),
        ("invalid_date_records", invalid_date_records, "invalid date records"),
        ("complete_records", complete_records, "complete records"),
        (
            "incomplete_records",
            total_records - complete_records,
            "incomplete records",
        ),
        (
            "valid_document_records",
            valid_document_records,
            "valid document records",
        ),
        (
            "invalid_document_records",
            total_records - valid_document_records,
            "invalid document records",
        ),
    ]

    for column in [
        "data_vacina",
        "sexo_paciente",
        "numero_idade_paciente",
        "uf_paciente",
        "codigo_municipio_paciente",
        "sg_vacina",
        "descricao_vacina_fabricante",
    ]:
        rows.append(
            (
                f"missing_{column}",
                count_missing(con, relation, column, total_records),
                f"missing {column.replace('_', ' ')}",
            )
        )

    validation = pd.DataFrame(rows, columns=["metric", "value", "description"])
    validation.to_csv(docs_dir / "validation_report.csv", index=False)
    return validation


def dir_size_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    total = sum(file.stat().st_size for file in path.rglob("*") if file.is_file())
    return round(total / (1024 * 1024), 2)


def csv_sum(path: Path, column: str) -> int:
    if not path.exists():
        return 0
    df = pd.read_csv(path)
    if column not in df.columns:
        return 0
    return int(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())


def metric_value(validation: pd.DataFrame, metric: str) -> int:
    value = validation.loc[validation["metric"] == metric, "value"]
    return int(value.iloc[0]) if not value.empty else 0


def write_run_closure_reports(
    con: duckdb.DuckDBPyConnection,
    validation: pd.DataFrame,
    processed_dir: Path,
    analytics_dir: Path,
    docs_dir: Path,
    db_path: Path,
) -> None:
    processed_records = metric_value(validation, "processed_records")
    parquet_files = sorted(processed_dir.glob("year=*/month=*/part-*.parquet"))

    monthly_total = csv_sum(analytics_dir / "monthly_vaccination_summary.csv", "doses_aplicadas")
    vaccine_total = csv_sum(analytics_dir / "vaccine_type_summary.csv", "doses_aplicadas")
    municipality_total = csv_sum(
        analytics_dir / "municipality_vaccination_summary.csv",
        "doses_aplicadas",
    )

    months_processed = scalar(
        con,
        """
        SELECT count(*)
        FROM (
            SELECT ano_vacinacao, mes_vacinacao
            FROM monthly_vaccination_summary
            WHERE ano_vacinacao IS NOT NULL AND mes_vacinacao IS NOT NULL
            GROUP BY ano_vacinacao, mes_vacinacao
        )
        """,
    )
    municipalities_observed = scalar(
        con,
        """
        SELECT count(*)
        FROM municipality_vaccination_summary
        WHERE codigo_municipio_paciente IS NOT NULL
        """,
    )
    distinct_sg_vacina = scalar(
        con,
        """
        SELECT count(DISTINCT sg_vacina)
        FROM vaccine_type_summary
        WHERE sg_vacina IS NOT NULL
        """,
    )
    distinct_vaccine_rows = scalar(con, "SELECT count(*) FROM vaccine_dictionary")

    closure_rows = [
        ("processed_records", processed_records),
        ("original_records", metric_value(validation, "original_records")),
        ("removed_duplicate_records", metric_value(validation, "removed_duplicate_records")),
        ("total_missing_values", metric_value(validation, "total_missing_values")),
        ("complete_records", metric_value(validation, "complete_records")),
        ("incomplete_records", metric_value(validation, "incomplete_records")),
        ("valid_document_records", metric_value(validation, "valid_document_records")),
        ("invalid_age_records", metric_value(validation, "invalid_age_records")),
        ("invalid_date_records", metric_value(validation, "invalid_date_records")),
        ("missing_uf_paciente", metric_value(validation, "missing_uf_paciente")),
        (
            "missing_codigo_municipio_paciente",
            metric_value(validation, "missing_codigo_municipio_paciente"),
        ),
        ("monthly_total_records", monthly_total),
        ("vaccine_total_records", vaccine_total),
        ("municipality_total_records", municipality_total),
        ("months_processed", months_processed),
        ("municipalities_observed", municipalities_observed),
        ("distinct_sg_vacina", distinct_sg_vacina),
        ("distinct_vaccine_rows", distinct_vaccine_rows),
        ("parquet_files", len(parquet_files)),
        ("processed_parquet_size_mb", dir_size_mb(processed_dir)),
        ("duckdb_size_mb", round(db_path.stat().st_size / (1024 * 1024), 2) if db_path.exists() else 0.0),
    ]

    pd.DataFrame(closure_rows, columns=["metric", "value"]).to_csv(
        docs_dir / "run_closure_summary.csv",
        index=False,
    )

    checks = [
        (
            "monthly_total_equals_processed",
            monthly_total == processed_records,
            monthly_total,
            processed_records,
        ),
        (
            "vaccine_total_equals_processed",
            vaccine_total == processed_records,
            vaccine_total,
            processed_records,
        ),
        (
            "municipality_total_equals_processed",
            municipality_total == processed_records,
            municipality_total,
            processed_records,
        ),
        (
            "valid_documents_equals_processed",
            metric_value(validation, "valid_document_records") == processed_records,
            metric_value(validation, "valid_document_records"),
            processed_records,
        ),
    ]

    pd.DataFrame(
        checks,
        columns=["check", "passed", "observed_value", "expected_value"],
    ).to_csv(docs_dir / "run_consistency_checks.csv", index=False)


def build_database(
    processed_dir: Path,
    analytics_dir: Path,
    docs_dir: Path,
    db_path: Path,
    geography_path: Path | None = None,
) -> None:
    parquet_pattern = processed_dir / "year=*" / "month=*" / "*.parquet"
    parquet_files = sorted(processed_dir.glob("year=*/month=*/*.parquet"))

    if not parquet_files:
        raise FileNotFoundError(
            f"Nenhum Parquet encontrado em {parquet_pattern}. "
            "Execute a ETL antes de criar o DuckDB."
        )

    analytics_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path))

    con.execute(
        f"""
        CREATE OR REPLACE VIEW vacinacao_curada AS
        SELECT *
        FROM read_parquet('{sql_literal(parquet_pattern)}', union_by_name = true)
        """
    )

    if geography_path and geography_path.exists():
        con.execute(
            f"""
            CREATE OR REPLACE TABLE municipality_geography AS
            SELECT
                lpad(cast(codigo_municipio AS varchar), 6, '0') AS codigo_municipio,
                nome_municipio_ibge,
                uf AS uf_ibge,
                nome_uf,
                regiao AS regiao_ibge,
                nome_regiao,
                try_cast(latitude AS double) AS latitude,
                try_cast(longitude AS double) AS longitude
            FROM read_csv_auto('{sql_literal(geography_path)}', header = true)
            """
        )

        con.execute(
            """
            CREATE OR REPLACE VIEW vacinacao_curada_geo AS
            SELECT
                v.*,
                g.nome_municipio_ibge,
                g.uf_ibge,
                g.nome_uf,
                g.regiao_ibge,
                g.nome_regiao,
                g.latitude,
                g.longitude
            FROM vacinacao_curada AS v
            LEFT JOIN municipality_geography AS g
                ON lpad(cast(v.codigo_municipio_paciente AS varchar), 6, '0') = g.codigo_municipio
            """
        )
    else:
        con.execute(
            """
            CREATE OR REPLACE VIEW vacinacao_curada_geo AS
            SELECT
                *,
                cast(NULL AS varchar) AS nome_municipio_ibge,
                cast(NULL AS varchar) AS uf_ibge,
                cast(NULL AS varchar) AS nome_uf,
                cast(NULL AS varchar) AS regiao_ibge,
                cast(NULL AS varchar) AS nome_regiao,
                cast(NULL AS double) AS latitude,
                cast(NULL AS double) AS longitude
            FROM vacinacao_curada
            """
        )

    con.execute(
        """
        CREATE OR REPLACE TABLE dataset_metadata AS
        SELECT
            'VacinaBR-PNI' AS dataset,
            'Portal de Dados Abertos do SUS' AS source,
            current_timestamp AS generated_at,
            (SELECT count(*) FROM vacinacao_curada) AS total_records
        """
    )

    for table_name, query in SUMMARY_QUERIES.items():
        con.execute(f"CREATE OR REPLACE TABLE {table_name} AS {query}")
        output_path = analytics_dir / f"{table_name}.csv"
        con.execute(
            f"""
            COPY {table_name}
            TO '{sql_literal(output_path)}'
            (HEADER, DELIMITER ',')
            """
        )

    table_rows = con.execute(
        """
        SELECT table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = 'main'
        ORDER BY table_name
        """
    ).fetchall()

    catalog = {
        "database": str(db_path),
        "source_parquet_pattern": str(parquet_pattern),
        "geography_path": str(geography_path) if geography_path else None,
        "geography_loaded": bool(geography_path and geography_path.exists()),
        "tables": [
            {"name": table_name, "type": table_type}
            for table_name, table_type in table_rows
        ],
        "view": "vacinacao_curada",
        "summary_queries": SUMMARY_QUERIES,
    }

    with (docs_dir / "duckdb_catalog.json").open("w", encoding="utf-8") as file:
        json.dump(catalog, file, ensure_ascii=False, indent=2)

    write_schema(con, docs_dir)
    validation = write_validation_report(con, docs_dir)
    write_run_closure_reports(
        con=con,
        validation=validation,
        processed_dir=processed_dir,
        analytics_dir=analytics_dir,
        docs_dir=docs_dir,
        db_path=db_path,
    )

    total_records = con.execute("SELECT total_records FROM dataset_metadata").fetchone()[0]
    con.close()

    print(f"[duckdb] database={db_path}")
    print(f"[duckdb] parquet_files={len(parquet_files)}")
    print(f"[duckdb] total_records={total_records:,}")
    print(f"[duckdb] catalog={docs_dir / 'duckdb_catalog.json'}")


def main() -> None:
    args = parse_args()
    build_database(
        processed_dir=Path(args.processed_dir),
        analytics_dir=Path(args.analytics_dir),
        docs_dir=Path(args.docs_dir),
        db_path=Path(args.db_path),
        geography_path=Path(args.geography_path),
    )


if __name__ == "__main__":
    main()
