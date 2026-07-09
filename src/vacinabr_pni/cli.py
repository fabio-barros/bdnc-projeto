from __future__ import annotations

import argparse
import contextlib
import sys
from pathlib import Path
from typing import Any


def parse_months(value: str | None) -> list[int] | None:
    if value is None:
        return None
    value = value.strip()
    if not value or value.lower() in {"all", "none"}:
        return None
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ETL VacinaBR-PNI")

    parser.add_argument(
        "--source",
        choices=["csv", "api"],
        default="csv",
        help="Fonte de entrada. Use csv para o fluxo atual equivalente ao notebook.",
    )
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument(
        "--manifest-path",
        default="data_sources/pni_2025_csv_manifest.csv",
        help="Manifesto dos ZIPs CSV mensais.",
    )
    parser.add_argument(
        "--months",
        default=None,
        help="Meses a processar, separados por virgula. Ex.: 1,2,3. Omitir para todos.",
    )
    parser.add_argument("--max-months", type=int, default=None)
    parser.add_argument("--chunksize", type=int, default=100_000)
    parser.add_argument("--csv-encoding", default="latin1")
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Nao baixa ZIPs; usa arquivos existentes em data/raw/zip.",
    )
    parser.add_argument(
        "--clear-selected-months",
        action="store_true",
        help="Apaga as particoes dos meses selecionados antes de reprocessar.",
    )
    parser.add_argument(
        "--no-skip-existing-months",
        action="store_true",
        help="Processa meses selecionados mesmo quando ja existem part-*.parquet.",
    )
    parser.add_argument(
        "--resume-deduplicate",
        action="store_true",
        help="Remove duplicatas entre chunks na mesma execucao local. Desligado por padrao, como no notebook.",
    )
    parser.add_argument(
        "--skip-finalize",
        action="store_true",
        help="Nao recria DuckDB, CSVs analiticos e relatorios finais.",
    )
    parser.add_argument("--db-path", default="data/vacinabr_pni.duckdb")
    parser.add_argument("--geography-path", default="data_sources/ibge_municipalities.csv")
    parser.add_argument("--figures-dir", default="paper/figures")
    parser.add_argument(
        "--map-max-points",
        type=int,
        default=250,
        help="Numero de pontos usados nos HTMLs/SVGs de mapa.",
    )

    parser.add_argument("--years", nargs="+", type=int, default=[2025])
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--page-param", default="offset")
    parser.add_argument("--limit-param", default="limit")
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=0.3)
    parser.add_argument("--skip-extract", action="store_true")

    parser.add_argument(
        "--log-file",
        default="pipeline_log.txt",
        help="Arquivo para registrar a saida da execucao. Use vazio para desativar.",
    )
    parser.add_argument(
        "--keep-sensitive",
        action="store_true",
        help="Mantem campos potencialmente sensiveis no processed.",
    )
    parser.add_argument(
        "--only-valid-documents",
        action="store_true",
        help="Mantem apenas registros finais e nao deletados na RNDS.",
    )

    return parser.parse_args()


class Tee:
    def __init__(self, *streams: Any) -> None:
        self.streams = streams

    def write(self, text: str) -> int:
        for stream in self.streams:
            stream.write(text)
            stream.flush()
        return len(text)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()


def run_csv_pipeline(args: argparse.Namespace) -> None:
    from scripts.build_duckdb import build_database
    from scripts.generate_municipality_map import (
        write_coverage_outputs,
        write_leaflet_html,
        write_plotly_html,
        write_svg_preview,
    )
    from vacinabr_pni.csv_pipeline import process_csv_manifest

    data_dir = Path(args.data_dir)
    docs_dir = Path(args.docs_dir)
    analytics_dir = data_dir / "analytics"
    processed_dir = data_dir / "processed"
    db_path = Path(args.db_path)
    geography_path = Path(args.geography_path)
    figures_dir = Path(args.figures_dir)

    process_csv_manifest(
        data_dir=data_dir,
        docs_dir=docs_dir,
        manifest_path=Path(args.manifest_path),
        months=parse_months(args.months),
        max_months=args.max_months,
        chunksize=args.chunksize,
        encoding=args.csv_encoding,
        download=not args.skip_download,
        clear_selected_months=args.clear_selected_months,
        skip_existing_months=not args.no_skip_existing_months,
        resume_deduplicate=args.resume_deduplicate,
        keep_sensitive=args.keep_sensitive,
        only_valid_documents=args.only_valid_documents,
    )

    if args.skip_finalize:
        print("[done] Processamento concluido sem fechamento DuckDB.")
        return

    build_database(
        processed_dir=processed_dir,
        analytics_dir=analytics_dir,
        docs_dir=docs_dir,
        db_path=db_path,
        geography_path=geography_path if geography_path.exists() else None,
    )

    municipality_csv = analytics_dir / "municipality_vaccination_summary.csv"
    if municipality_csv.exists() and geography_path.exists():
        figures_dir.mkdir(parents=True, exist_ok=True)
        mappable = write_coverage_outputs(
            input_path=municipality_csv,
            geography_path=geography_path,
            analytics_dir=analytics_dir,
            docs_dir=docs_dir,
        )
        preview = mappable.head(args.map_max_points)
        if not preview.empty:
            write_leaflet_html(preview, figures_dir / "municipality_map.html")
            write_plotly_html(preview, figures_dir / "municipality_map_plotly.html")
            write_svg_preview(preview, figures_dir / "municipality_map.svg")

    print("[done] Pipeline CSV finalizada com sucesso.")
    print(f"[done] Processed: {processed_dir}")
    print(f"[done] Analytics: {analytics_dir}")
    print(f"[done] Docs: {docs_dir}")


def run_api_pipeline(args: argparse.Namespace) -> None:
    import pandas as pd

    from vacinabr_pni.extract import extract_year, load_raw_pages
    from vacinabr_pni.transform import transform
    from vacinabr_pni.writers import (
        ensure_dirs,
        write_analytics,
        write_data_dictionary,
        write_partitions,
        write_schema,
        write_source_metadata,
    )

    dirs = ensure_dirs(data_dir=Path(args.data_dir), docs_dir=Path(args.docs_dir))
    all_records: list[dict[str, Any]] = []

    for year in args.years:
        if args.skip_extract:
            records = load_raw_pages(dirs["raw"], year)
            print(f"[extract] loaded raw pages year={year} records={len(records):,}")
        else:
            records = extract_year(
                year=year,
                raw_dir=dirs["raw"],
                page_size=args.page_size,
                page_param=args.page_param,
                limit_param=args.limit_param,
                max_pages=args.max_pages,
                sleep_seconds=args.sleep,
            )
        all_records.extend(records)

    if not all_records:
        raise RuntimeError("Nenhum registro coletado pelo fluxo API.")

    raw_df = pd.DataFrame(all_records)
    processed_df, validation_df = transform(
        df=raw_df,
        keep_sensitive=args.keep_sensitive,
        only_valid_documents=args.only_valid_documents,
        deduplicate=True,
    )

    write_partitions(df=processed_df, processed_dir=dirs["processed"])
    write_analytics(df=processed_df, analytics_dir=dirs["analytics"])
    write_schema(df=processed_df, docs_dir=dirs["docs"])
    write_data_dictionary(docs_dir=dirs["docs"])
    write_source_metadata(
        docs_dir=dirs["docs"],
        years=args.years,
        page_param=args.page_param,
        limit_param=args.limit_param,
        page_size=args.page_size,
    )
    validation_df.to_csv(
        dirs["docs"] / "validation_report.csv",
        index=False,
        encoding="utf-8",
    )

    print("[done] Pipeline API legada finalizada com sucesso.")


def run_pipeline(args: argparse.Namespace) -> None:
    if args.source == "api":
        run_api_pipeline(args)
    else:
        run_csv_pipeline(args)


def main() -> None:
    args = parse_args()

    if not args.log_file:
        run_pipeline(args)
        return

    log_path = Path(args.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("w", encoding="utf-8") as log_file:
        with contextlib.redirect_stdout(Tee(sys.stdout, log_file)):
            run_pipeline(args)
