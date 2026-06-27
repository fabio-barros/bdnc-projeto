from __future__ import annotations

import argparse
import contextlib
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ETL VacinaBR-PNI")

    parser.add_argument("--years", nargs="+", type=int, default=[2024, 2025])
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--docs-dir", default="docs")

    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--page-param", default="offset")
    parser.add_argument("--limit-param", default="limit")
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=0.3)
    parser.add_argument(
        "--log-file",
        default="pipeline_log.txt",
        help="Arquivo para registrar a saida da execucao.",
    )

    parser.add_argument("--skip-extract", action="store_true")

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


def run_pipeline(args: argparse.Namespace) -> None:
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

    dirs = ensure_dirs(
        data_dir=Path(args.data_dir),
        docs_dir=Path(args.docs_dir),
    )

    all_records: list[dict[str, Any]] = []

    for year in args.years:
        if args.skip_extract:
            records = load_raw_pages(dirs["raw"], year)

            print(
                f"[extract] loaded raw pages from disk "
                f"year={year} records={len(records):,}"
            )
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
        raise RuntimeError(
            "Nenhum registro coletado. Verifique endpoint, paginacao e "
            "parametros da API."
        )

    raw_df = pd.DataFrame(all_records)

    print(
        f"[transform] total raw records={len(raw_df):,} "
        f"columns={len(raw_df.columns):,}"
    )

    processed_df, validation_df = transform(
        df=raw_df,
        keep_sensitive=args.keep_sensitive,
        only_valid_documents=args.only_valid_documents,
    )

    print(
        f"[transform] processed records={len(processed_df):,} "
        f"columns={len(processed_df.columns):,}"
    )

    write_partitions(
        df=processed_df,
        processed_dir=dirs["processed"],
    )

    write_analytics(
        df=processed_df,
        analytics_dir=dirs["analytics"],
    )

    write_schema(
        df=processed_df,
        docs_dir=dirs["docs"],
    )

    write_data_dictionary(
        docs_dir=dirs["docs"],
    )

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

    print("[done] Pipeline finalizada com sucesso.")
    print(f"[done] Processed: {dirs['processed']}")
    print(f"[done] Analytics: {dirs['analytics']}")
    print(f"[done] Docs: {dirs['docs']}")


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
