from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests

from vacinabr_pni.config import API_BASE_URL, ENDPOINT_TEMPLATE


def endpoint_url(year: int) -> str:
    return f"{API_BASE_URL}{ENDPOINT_TEMPLATE.format(year=year)}"


def extract_records_from_response(payload: Any) -> list[dict[str, Any]]:
    """Extract records from common API response shapes."""

    if isinstance(payload, list):
        return payload

    if not isinstance(payload, dict):
        return []

    for key in ["doses_aplicadas_pni", "data", "items", "results", "registros"]:
        value = payload.get(key)

        if isinstance(value, list):
            return value

    for value in payload.values():
        if isinstance(value, list) and (not value or isinstance(value[0], dict)):
            return value

    return []


def save_raw_page(raw_dir: Path, year: int, page: int, payload: Any) -> None:
    year_dir = raw_dir / f"year={year}"
    year_dir.mkdir(parents=True, exist_ok=True)

    output_path = raw_page_path(raw_dir, year, page)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def raw_page_path(raw_dir: Path, year: int, page: int) -> Path:
    return raw_dir / f"year={year}" / f"page={page:06d}.json"


def load_raw_page(raw_dir: Path, year: int, page: int) -> Any:
    with raw_page_path(raw_dir, year, page).open("r", encoding="utf-8") as file:
        return json.load(file)


def load_raw_pages(raw_dir: Path, year: int) -> list[dict[str, Any]]:
    year_dir = raw_dir / f"year={year}"
    records: list[dict[str, Any]] = []

    for path in sorted(year_dir.glob("page=*.json")):
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        records.extend(extract_records_from_response(payload))

    return records


def extract_year(
    year: int,
    raw_dir: Path,
    page_size: int,
    page_param: str,
    limit_param: str,
    max_pages: int | None,
    sleep_seconds: float,
) -> list[dict[str, Any]]:
    url = endpoint_url(year)
    all_records: list[dict[str, Any]] = []
    page = 0 if page_param == "offset" else 1
    pages_fetched = 0

    while True:
        params = {
            page_param: page,
            limit_param: page_size,
        }

        existing_page = raw_page_path(raw_dir, year, page)

        if existing_page.exists():
            print(f"[extract] reuse {existing_page}")
            payload = load_raw_page(raw_dir, year, page)
        else:
            print(f"[extract] GET {url} | {params}")

            response = requests.get(url, params=params, timeout=90)
            response.raise_for_status()

            payload = response.json()
            save_raw_page(raw_dir, year, page, payload)

        records = extract_records_from_response(payload)
        pages_fetched += 1

        print(f"[extract] year={year} page={page} records={len(records):,}")

        if not records:
            break

        all_records.extend(records)

        if len(records) < page_size:
            break

        page += 1

        if max_pages is not None and pages_fetched >= max_pages:
            break

        time.sleep(sleep_seconds)

    print(f"[extract] year={year} total_records={len(all_records):,}")

    return all_records
