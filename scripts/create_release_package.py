from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monta uma pasta de release publicavel do VacinaBR-PNI."
    )
    parser.add_argument("--output-dir", default="release/VacinaBR-PNI")
    parser.add_argument("--analytics-dir", default="data/analytics")
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument("--notebooks-dir", default="notebooks")
    parser.add_argument("--dashboard-dir", default="dashboard")
    parser.add_argument("--db-path", default="data/vacinabr_pni.duckdb")
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument(
        "--include-parquet",
        action="store_true",
        help="Copia os Parquets curados para o release. Pode ocupar bastante espaco.",
    )
    parser.add_argument(
        "--include-duckdb",
        action="store_true",
        help="Copia o arquivo .duckdb para o release se ele existir.",
    )
    return parser.parse_args()


def copy_tree(source: Path, target: Path) -> None:
    if not source.exists():
        return
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def copy_file(source: Path, target: Path) -> None:
    if not source.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    analytics_dir = Path(args.analytics_dir)
    docs_dir = Path(args.docs_dir)
    notebooks_dir = Path(args.notebooks_dir)
    dashboard_dir = Path(args.dashboard_dir)
    db_path = Path(args.db_path)
    processed_dir = Path(args.processed_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    copy_tree(analytics_dir, output_dir / "data" / "analytics")
    copy_tree(docs_dir, output_dir / "docs")
    copy_tree(notebooks_dir, output_dir / "notebooks")
    copy_tree(dashboard_dir, output_dir / "dashboard")

    for root_file in [
        "CITATION.cff",
        "LICENSE",
        "requirements.txt",
        "requirements-dashboard.txt",
    ]:
        copy_file(Path(root_file), output_dir / root_file)
    copy_file(Path("README.md"), output_dir / "PROJECT_README.md")

    if args.include_parquet:
        copy_tree(processed_dir, output_dir / "data" / "processed")

    if args.include_duckdb:
        copy_file(db_path, output_dir / "data" / db_path.name)

    release_readme = output_dir / "README.md"
    release_readme.write_text(
        """# VacinaBR-PNI Release

Este pacote contem artefatos publicaveis do dataset VacinaBR-PNI.

## Conteudo

- `data/analytics/`: CSVs agregados para analise exploratoria.
- `docs/`: dicionario de dados, schema, metadados, validacao e catalogo DuckDB.
- `notebooks/`: exemplos de consulta, exploracao e relatorio de qualidade.
- `dashboard/`: app Streamlit demonstrativo.
- `data/processed/`: Parquets curados, quando `--include-parquet` for usado.
- `data/vacinabr_pni.duckdb`: banco DuckDB, quando `--include-duckdb` for usado.
- `CITATION.cff`: citacao sugerida do dataset/projeto.
- `LICENSE`: licenca do pacote.
- `PROJECT_README.md`: README completo do repositorio.

## Consulta

Os CSVs podem ser abertos em planilhas e ferramentas de BI. Os Parquets podem ser
consultados com DuckDB:

```python
import duckdb

duckdb.sql(\"\"\"
    SELECT uf_paciente, count(*) AS doses_aplicadas
    FROM read_parquet('data/processed/year=*/month=*/*.parquet')
    GROUP BY uf_paciente
    ORDER BY doses_aplicadas DESC
\"\"\").df()
```

## Citacao

Use o arquivo `CITATION.cff` do repositorio principal e os metadados em
`docs/source_metadata.json`.
""",
        encoding="utf-8",
    )

    manifest = {
        "release_dir": str(output_dir),
        "analytics_copied": analytics_dir.exists(),
        "docs_copied": docs_dir.exists(),
        "notebooks_copied": notebooks_dir.exists(),
        "dashboard_copied": dashboard_dir.exists(),
        "parquet_included": args.include_parquet,
        "duckdb_included": args.include_duckdb and db_path.exists(),
    }
    (output_dir / "release_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[release] {output_dir}")
    print(f"[release] manifest={output_dir / 'release_manifest.json'}")


if __name__ == "__main__":
    main()
