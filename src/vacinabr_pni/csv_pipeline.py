from __future__ import annotations

import json
import shutil
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse

import pandas as pd

from vacinabr_pni.transform import normalize_column_name, transform
from vacinabr_pni.writers import write_data_dictionary


SOURCE_PAGE = (
    "https://dadosabertos.saude.gov.br/dataset/"
    "doses-aplicadas-pelo-programa-de-nacional-de-imunizacoes-pni-2025"
)

RAW_CSV_COLUMNS = [
    "codigo_documento",
    "sexo_paciente",
    "codigo_raca_cor_paciente",
    "nome_raca_cor_paciente",
    "codigo_municipio_paciente",
    "codigo_pais_paciente",
    "nome_municipio_paciente",
    "nome_pais_paciente",
    "uf_paciente",
    "descricao_nacionalidade_paciente",
    "codigo_etnia_indigena_paciente",
    "nome_etnia_indigena_paciente",
    "codigo_cnes_estabelecimento",
    "razao_social_estabelecimento",
    "nome_fantasia_estabelecimento",
    "codigo_municipio_estabelecimento",
    "nome_municipio_estabelecimento",
    "uf_estabelecimento",
    "codigo_pais_estabelecimento",
    "codigo_vacina_fabricante",
    "sg_vacina",
    "data_vacina",
    "numero_idade_paciente",
    "descricao_dose_vacina",
    "codigo_dose_vacina",
    "descricao_local_aplicacao",
    "codigo_via_administracao",
    "descricao_via_administracao",
    "codigo_lote_vacina",
    "descricao_vacina_fabricante",
    "data_entrada_rnds",
    "codigo_sistema_origem",
    "descricao_sistema_origem",
    "st_documento",
    "codigo_estrategia_vacinacao",
    "descricao_estrategia_vacinacao",
    "codigo_origem_registro",
    "descricao_origem_registro",
    "codigo_vacina_categoria_atendimento",
    "descricao_vacina_categoria_atendimento",
    "codigo_vacina_grupo_atendimento",
    "descricao_vacina_grupo_atendimento",
    "codigo_vacina",
    "descricao_vacina",
    "codigo_condicao_maternal",
    "codigo_tipo_estabelecimento",
    "descricao_tipo_estabelecimento",
    "codigo_natureza_estabelecimento",
    "descricao_natureza_estabelecimento",
    "codigo_troca_documento",
    "descricao_condicao_maternal",
    "nome_uf_paciente",
    "nome_uf_estabelecimento",
    "data_deletado_rnds",
]

HEADER_HINTS = {
    "data_vacina",
    "codigo_documento",
    "tipo_sexo_paciente",
    "sexo_paciente",
    "codigo_municipio_paciente",
}


@dataclass(frozen=True)
class ManifestItem:
    year: int
    month: int
    month_name: str
    resource_name: str
    url: str
    source_page: str

    @property
    def zip_filename(self) -> str:
        parsed = urlparse(self.url)
        if parsed.scheme:
            return Path(unquote(parsed.path)).name
        return Path(self.url).name


def load_manifest(manifest_path: Path, months: Iterable[int] | None) -> list[ManifestItem]:
    manifest = pd.read_csv(manifest_path)

    if months is not None:
        selected_months = {int(month) for month in months}
        manifest = manifest[manifest["month"].astype(int).isin(selected_months)].copy()

    items = []
    for row in manifest.to_dict(orient="records"):
        items.append(
            ManifestItem(
                year=int(row["year"]),
                month=int(row["month"]),
                month_name=str(row.get("month_name", row["month"])),
                resource_name=str(row.get("resource_name", "")),
                url=str(row["url"]),
                source_page=str(row.get("source_page") or SOURCE_PAGE),
            )
        )

    return items


def download_zip(url: str, output_path: Path) -> None:
    if output_path.exists() and output_path.stat().st_size > 0:
        print(f"[download] reutilizando {output_path}")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".part")
    print(f"[download] baixando {url}")

    with urllib.request.urlopen(url) as response:
        with temp_path.open("wb") as file:
            shutil.copyfileobj(response, file)

    temp_path.replace(output_path)
    print(f"[download] salvo {output_path}")


def find_csv_member(zip_path: Path) -> str:
    with zipfile.ZipFile(zip_path) as zf:
        csv_members = [
            member
            for member in zf.namelist()
            if not member.endswith("/") and member.lower().endswith(".csv")
        ]

    if not csv_members:
        raise FileNotFoundError(f"Nenhum CSV encontrado em {zip_path}")

    return csv_members[0]


def detect_separator(sample: str) -> str:
    semicolon_count = sample.count(";")
    comma_count = sample.count(",")
    return ";" if semicolon_count >= comma_count else ","


def has_header(first_line: str, sep: str) -> bool:
    normalized = {normalize_column_name(part) for part in first_line.split(sep)}
    return bool(normalized.intersection(HEADER_HINTS))


def inspect_zip_csv(zip_path: Path, encoding: str) -> tuple[str, str, bool]:
    member = find_csv_member(zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(member) as raw_file:
            first_line = raw_file.readline().decode(encoding, errors="replace")

    sep = detect_separator(first_line)
    header = has_header(first_line, sep)
    print(
        f"[inspect] {zip_path.name} member={member} sep={sep!r} "
        f"header={header}"
    )
    return member, sep, header


def month_partition_dir(processed_dir: Path, item: ManifestItem) -> Path:
    return processed_dir / f"year={item.year}" / f"month={item.month:02d}"


def month_has_parts(processed_dir: Path, item: ManifestItem) -> bool:
    return any(month_partition_dir(processed_dir, item).glob("part-*.parquet"))


def next_part_counter(processed_dir: Path) -> int:
    max_part = -1
    for path in processed_dir.glob("year=*/month=*/part-*.parquet"):
        stem = path.stem
        try:
            max_part = max(max_part, int(stem.split("-")[-1]))
        except ValueError:
            continue

    return max_part + 1


def iter_csv_chunks(
    zip_path: Path,
    member: str,
    sep: str,
    header: bool,
    chunksize: int,
    encoding: str,
) -> Iterable[pd.DataFrame]:
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(member) as raw_file:
            yield from pd.read_csv(
                raw_file,
                sep=sep,
                header=0 if header else None,
                names=None if header else RAW_CSV_COLUMNS,
                dtype="string",
                chunksize=chunksize,
                encoding=encoding,
                low_memory=False,
            )


def write_schema_from_columns(
    columns: dict[str, str],
    docs_dir: Path,
) -> None:
    schema = {
        "dataset": "VacinaBR-PNI",
        "description": (
            "Dataset curado de doses aplicadas pelo Programa Nacional de "
            "Imunizacoes, gerado a partir dos CSVs mensais do PNI."
        ),
        "columns": [
            {"name": name, "pandas_dtype": dtype}
            for name, dtype in columns.items()
        ],
    }
    with (docs_dir / "schema.json").open("w", encoding="utf-8") as file:
        json.dump(schema, file, ensure_ascii=False, indent=2)


def write_source_metadata(
    docs_dir: Path,
    manifest_path: Path,
    items: list[ManifestItem],
    chunksize: int,
    encoding: str,
) -> None:
    metadata = {
        "dataset": "VacinaBR-PNI",
        "source": "Portal de Dados Abertos do SUS",
        "source_page": SOURCE_PAGE,
        "manifest_path": str(manifest_path),
        "years": sorted({item.year for item in items}),
        "months": [item.month for item in items],
        "chunksize": chunksize,
        "csv_encoding": encoding,
        "raw_format": "ZIP files containing monthly CSV files",
        "processed_format": "Parquet partitioned by year and month",
        "sensitive_fields_removed_from_processed": [
            "codigo_paciente",
            "numero_cep_paciente",
        ],
        "resources": [
            {
                "year": item.year,
                "month": item.month,
                "month_name": item.month_name,
                "resource_name": item.resource_name,
                "url": item.url,
                "source_page": item.source_page,
            }
            for item in items
        ],
    }

    with (docs_dir / "source_metadata.json").open("w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)


def process_csv_manifest(
    data_dir: Path,
    docs_dir: Path,
    manifest_path: Path,
    months: Iterable[int] | None = None,
    max_months: int | None = None,
    chunksize: int = 100_000,
    encoding: str = "latin1",
    download: bool = True,
    clear_selected_months: bool = False,
    skip_existing_months: bool = True,
    resume_deduplicate: bool = False,
    keep_sensitive: bool = False,
    only_valid_documents: bool = False,
) -> None:
    raw_zip_dir = data_dir / "raw" / "zip"
    processed_dir = data_dir / "processed"
    analytics_dir = data_dir / "analytics"

    raw_zip_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    analytics_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    items = load_manifest(manifest_path, months)
    if max_months is not None:
        items = items[:max_months]

    if not items:
        raise ValueError("Nenhum mes selecionado para processamento.")

    manifest_copy = docs_dir / manifest_path.name
    pd.read_csv(manifest_path).to_csv(manifest_copy, index=False, encoding="utf-8")

    print(f"[manifest] meses selecionados: {[item.month for item in items]}")

    for item in items:
        zip_path = raw_zip_dir / item.zip_filename
        if download:
            download_zip(item.url, zip_path)
        elif not zip_path.exists():
            raise FileNotFoundError(
                f"ZIP ausente: {zip_path}. Use download=True ou coloque o arquivo em data/raw/zip."
            )

    if clear_selected_months:
        for item in items:
            partition_dir = month_partition_dir(processed_dir, item)
            if partition_dir.exists():
                print(f"[clear] removendo {partition_dir}")
                shutil.rmtree(partition_dir)

    observed_schema: dict[str, str] = {}
    processed_rows = 0
    part_counter = next_part_counter(processed_dir)
    seen_hashes: set[int] = set()

    for item in items:
        if skip_existing_months and month_has_parts(processed_dir, item):
            print(
                f"[skip] {item.year}-{item.month:02d}: particoes existentes em "
                f"{month_partition_dir(processed_dir, item)}"
            )
            continue

        zip_path = raw_zip_dir / item.zip_filename
        member, sep, header = inspect_zip_csv(zip_path, encoding=encoding)
        partition_dir = month_partition_dir(processed_dir, item)
        partition_dir.mkdir(parents=True, exist_ok=True)

        for chunk_index, chunk in enumerate(
            iter_csv_chunks(
                zip_path=zip_path,
                member=member,
                sep=sep,
                header=header,
                chunksize=chunksize,
                encoding=encoding,
            )
        ):
            processed, _ = transform(
                df=chunk,
                keep_sensitive=keep_sensitive,
                only_valid_documents=only_valid_documents,
                deduplicate=False,
            )

            if resume_deduplicate and not processed.empty:
                row_hashes = pd.util.hash_pandas_object(processed, index=False)
                keep_mask = ~row_hashes.isin(seen_hashes)
                seen_hashes.update(row_hashes[keep_mask].astype(int).tolist())
                processed = processed.loc[keep_mask].copy()

            if processed.empty:
                continue

            if not observed_schema:
                observed_schema = {
                    column: str(dtype)
                    for column, dtype in processed.dtypes.items()
                }

            output_path = partition_dir / f"part-{part_counter:06d}.parquet"
            processed.to_parquet(output_path, index=False)
            processed_rows += len(processed)
            print(
                f"[process] {item.year}-{item.month:02d} chunk={chunk_index} "
                f"rows={len(processed):,} -> {output_path.name}"
            )
            part_counter += 1

    if observed_schema:
        write_schema_from_columns(observed_schema, docs_dir=docs_dir)

    write_data_dictionary(docs_dir=docs_dir)
    write_source_metadata(
        docs_dir=docs_dir,
        manifest_path=manifest_path,
        items=items,
        chunksize=chunksize,
        encoding=encoding,
    )

    print(f"[done] registros processados nesta execucao: {processed_rows:,}")
