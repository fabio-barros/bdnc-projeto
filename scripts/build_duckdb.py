from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


SUMMARY_QUERIES = {
    "monthly_vaccination_summary": """
        SELECT
            ano_vacinacao,
            mes_vacinacao,
            count(*) AS doses_aplicadas
        FROM vacinacao_curada
        GROUP BY ano_vacinacao, mes_vacinacao
        ORDER BY ano_vacinacao, mes_vacinacao
    """,
    "state_vaccination_summary": """
        SELECT
            uf_paciente,
            count(*) AS doses_aplicadas
        FROM vacinacao_curada
        GROUP BY uf_paciente
        ORDER BY doses_aplicadas DESC
    """,
    "region_vaccination_summary": """
        SELECT
            regiao_paciente,
            count(*) AS doses_aplicadas
        FROM vacinacao_curada
        GROUP BY regiao_paciente
        ORDER BY doses_aplicadas DESC
    """,
    "vaccine_type_summary": """
        SELECT
            sg_vacina,
            count(*) AS doses_aplicadas
        FROM vacinacao_curada
        GROUP BY sg_vacina
        ORDER BY doses_aplicadas DESC
    """,
    "manufacturer_summary": """
        SELECT
            descricao_vacina_fabricante,
            count(*) AS doses_aplicadas
        FROM vacinacao_curada
        GROUP BY descricao_vacina_fabricante
        ORDER BY doses_aplicadas DESC
    """,
    "age_group_summary": """
        SELECT
            faixa_etaria,
            count(*) AS doses_aplicadas
        FROM vacinacao_curada
        GROUP BY faixa_etaria
        ORDER BY doses_aplicadas DESC
    """,
    "sex_summary": """
        SELECT
            sexo_paciente,
            count(*) AS doses_aplicadas
        FROM vacinacao_curada
        GROUP BY sexo_paciente
        ORDER BY doses_aplicadas DESC
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
    return parser.parse_args()


def sql_literal(value: Path | str) -> str:
    return str(value).replace("\\", "/").replace("'", "''")


def build_database(
    processed_dir: Path,
    analytics_dir: Path,
    docs_dir: Path,
    db_path: Path,
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
        "tables": [
            {"name": table_name, "type": table_type}
            for table_name, table_type in table_rows
        ],
        "view": "vacinacao_curada",
        "summary_queries": SUMMARY_QUERIES,
    }

    with (docs_dir / "duckdb_catalog.json").open("w", encoding="utf-8") as file:
        json.dump(catalog, file, ensure_ascii=False, indent=2)

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
    )


if __name__ == "__main__":
    main()
