from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import requests


IBGE_MUNICIPALITIES_URL = (
    "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
)
COORDINATES_URL = (
    "https://raw.githubusercontent.com/kelvins/Municipios-Brasileiros/main/csv/municipios.csv"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baixa metadados municipais do IBGE e coordenadas auxiliares."
    )
    parser.add_argument("--output", default="data_sources/ibge_municipalities.csv")
    parser.add_argument("--ibge-url", default=IBGE_MUNICIPALITIES_URL)
    parser.add_argument("--coordinates-url", default=COORDINATES_URL)
    parser.add_argument(
        "--skip-coordinates",
        action="store_true",
        help="Gera apenas codigos, nomes, UF e regiao do IBGE.",
    )
    return parser.parse_args()


def fetch_ibge_municipalities(url: str) -> pd.DataFrame:
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    rows = []

    for item in response.json():
        micro = item.get("microrregiao") or {}
        meso = micro.get("mesorregiao") or {}
        uf = meso.get("UF") or {}
        region = uf.get("regiao") or {}

        rows.append(
            {
                "codigo_municipio": str(item.get("id", "")).zfill(7)[:6],
                "nome_municipio_ibge": item.get("nome"),
                "uf": uf.get("sigla"),
                "nome_uf": uf.get("nome"),
                "regiao": region.get("nome"),
                "nome_regiao": region.get("nome"),
            }
        )

    return pd.DataFrame(rows)


def fetch_coordinates(url: str) -> pd.DataFrame:
    df = pd.read_csv(url, dtype={"codigo_ibge": "string"})
    df = df.rename(
        columns={
            "codigo_ibge": "codigo_municipio",
            "latitude": "latitude",
            "longitude": "longitude",
        }
    )
    df["codigo_municipio"] = df["codigo_municipio"].astype("string").str.zfill(7)
    df["codigo_municipio"] = df["codigo_municipio"].str[:6]
    return df[["codigo_municipio", "latitude", "longitude"]].drop_duplicates(
        subset=["codigo_municipio"]
    )


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    geography = fetch_ibge_municipalities(args.ibge_url)

    if args.skip_coordinates:
        geography["latitude"] = pd.NA
        geography["longitude"] = pd.NA
    else:
        try:
            coordinates = fetch_coordinates(args.coordinates_url)
            geography = geography.merge(
                coordinates,
                on="codigo_municipio",
                how="left",
            )
        except Exception as exc:
            print(f"[geography] coordenadas indisponiveis: {exc}")
            geography["latitude"] = pd.NA
            geography["longitude"] = pd.NA

    geography.to_csv(output_path, index=False, encoding="utf-8")
    print(f"[geography] rows={len(geography):,}")
    print(f"[geography] output={output_path}")


if __name__ == "__main__":
    main()
