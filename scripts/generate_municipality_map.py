from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera exemplos de mapa municipal a partir dos CSVs analiticos."
    )
    parser.add_argument(
        "--input",
        default="data/analytics/municipality_vaccination_summary.csv",
    )
    parser.add_argument(
        "--geography",
        default="data_sources/ibge_municipalities.csv",
        help="CSV com metadados municipais do IBGE, usado quando o input ainda nao possui latitude/longitude.",
    )
    parser.add_argument("--output-dir", default="paper/figures")
    parser.add_argument("--max-points", type=int, default=250)
    parser.add_argument("--analytics-dir", default="data/analytics")
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument(
        "--write-coverage",
        action="store_true",
        help="Tambem grava o CSV municipal mapeavel e o relatorio de cobertura.",
    )
    return parser.parse_args()


def enrich_with_geography(df: pd.DataFrame, geography_path: Path) -> pd.DataFrame:
    if {"latitude", "longitude"}.issubset(df.columns):
        return df

    geo = pd.read_csv(geography_path)
    df = df.copy()
    geo = geo.copy()
    df["codigo_municipio_paciente"] = (
        df["codigo_municipio_paciente"].astype("string").str.replace(r"\.0$", "", regex=True).str.zfill(6)
    )
    geo["codigo_municipio"] = (
        geo["codigo_municipio"].astype("string").str.replace(r"\.0$", "", regex=True).str.zfill(6)
    )
    return df.merge(
        geo[
            [
                "codigo_municipio",
                "nome_municipio_ibge",
                "nome_uf",
                "nome_regiao",
                "latitude",
                "longitude",
            ]
        ],
        left_on="codigo_municipio_paciente",
        right_on="codigo_municipio",
        how="left",
    )


def prepare_mappable_municipalities(path: Path, geography_path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = enrich_with_geography(df, geography_path)
    df = df.dropna(subset=["latitude", "longitude", "doses_aplicadas"]).copy()
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["doses_aplicadas"] = pd.to_numeric(df["doses_aplicadas"], errors="coerce")
    df = df.dropna(subset=["latitude", "longitude", "doses_aplicadas"])

    if {"codigo_municipio_paciente", "nome_municipio_ibge"}.issubset(df.columns):
        df["nome_municipio_paciente"] = df["nome_municipio_ibge"].fillna(
            df["nome_municipio_paciente"]
        )
        if "nome_regiao" in df.columns:
            df["regiao_paciente"] = df["nome_regiao"].fillna(df.get("regiao_paciente"))
        group_cols = [
            "codigo_municipio_paciente",
            "nome_municipio_paciente",
            "uf_paciente",
            "regiao_paciente",
            "latitude",
            "longitude",
        ]
        df = (
            df.groupby(group_cols, dropna=False, as_index=False)["doses_aplicadas"]
            .sum()
            .copy()
        )

    df = df.sort_values("doses_aplicadas", ascending=False)
    return df


def load_municipalities(path: Path, geography_path: Path, max_points: int) -> pd.DataFrame:
    return prepare_mappable_municipalities(path, geography_path).head(max_points)


def write_coverage_outputs(
    input_path: Path,
    geography_path: Path,
    analytics_dir: Path,
    docs_dir: Path,
) -> pd.DataFrame:
    source = pd.read_csv(input_path)
    total_records = int(
        pd.to_numeric(source["doses_aplicadas"], errors="coerce").fillna(0).sum()
    )
    mappable = prepare_mappable_municipalities(input_path, geography_path)
    mappable_records = int(mappable["doses_aplicadas"].sum()) if not mappable.empty else 0
    pct_mappable = round(100 * mappable_records / total_records, 2) if total_records else 0.0

    analytics_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    mappable.to_csv(
        analytics_dir / "municipality_vaccination_summary_mappable.csv",
        index=False,
        encoding="utf-8",
    )

    pd.DataFrame(
        [
            {
                "metric": "municipalities_mappable",
                "value": int(len(mappable)),
                "description": "municipalities with valid latitude and longitude",
            },
            {
                "metric": "mappable_doses",
                "value": mappable_records,
                "description": "doses in mappable municipalities",
            },
            {
                "metric": "total_doses",
                "value": total_records,
                "description": "total doses in municipality summary",
            },
            {
                "metric": "pct_mappable_doses",
                "value": pct_mappable,
                "description": "percentage of doses with valid municipal coordinates",
            },
        ]
    ).to_csv(docs_dir / "map_coverage_report.csv", index=False, encoding="utf-8")

    return mappable


def write_leaflet_html(df: pd.DataFrame, output_path: Path) -> None:
    points = []
    max_doses = max(float(df["doses_aplicadas"].max()), 1.0)
    total_doses = int(df["doses_aplicadas"].sum())
    total_municipalities = len(df)

    for row in df.to_dict(orient="records"):
        doses = float(row["doses_aplicadas"])
        radius = 5 + 20 * (doses / max_doses) ** 0.5
        points.append(
            {
                "lat": float(row["latitude"]),
                "lon": float(row["longitude"]),
                "radius": round(radius, 2),
                "doses": int(doses),
                "municipio": str(row.get("nome_municipio_paciente", "")),
                "uf": str(row.get("uf_paciente", "")),
            }
        )

    payload = json.dumps(points, ensure_ascii=False)
    output_path.write_text(
        f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>VacinaBR-PNI - Doses por municipio</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; }}
    #map {{ height: 92vh; }}
    header {{ padding: 12px 16px; border-bottom: 1px solid #ddd; }}
    h1 {{ font-size: 18px; margin: 0 0 4px; }}
    p {{ margin: 0; color: #555; }}
  </style>
</head>
<body>
  <header>
    <h1>VacinaBR-PNI: doses aplicadas por município</h1>
    <p>Cada círculo representa um município com coordenadas IBGE. Mapa com {total_municipalities:,} municípios e {total_doses:,} doses mapeáveis.</p>
  </header>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const points = {payload};
    const map = L.map('map').setView([-14.2, -51.9], 4);
    L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 18,
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);

    points.forEach(point => {{
      L.circleMarker([point.lat, point.lon], {{
        radius: point.radius,
        color: '#1f5aa6',
        weight: 1,
        fillColor: '#3b82f6',
        fillOpacity: 0.45
      }})
      .bindPopup(`<strong>${{point.municipio}} - ${{point.uf}}</strong><br>Doses aplicadas: ${{point.doses}}`)
      .addTo(map);
    }});
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )


def write_plotly_html(df: pd.DataFrame, output_path: Path) -> None:
    plot_df = df.copy()
    total_doses = int(plot_df["doses_aplicadas"].sum())
    total_municipalities = len(plot_df)
    plot_df["municipio_label"] = (
        plot_df["nome_municipio_paciente"].fillna("")
        + " - "
        + plot_df["uf_paciente"].fillna("")
    )
    plot_df["hover"] = plot_df.apply(
        lambda row: (
            f"{row['municipio_label']}<br>"
            f"Doses aplicadas: {int(row['doses_aplicadas'])}"
        ),
        axis=1,
    )
    max_doses = max(float(plot_df["doses_aplicadas"].max()), 1.0)
    plot_df["marker_size"] = 8 + 36 * (plot_df["doses_aplicadas"] / max_doses) ** 0.5

    payload = json.dumps(
        {
            "lat": plot_df["latitude"].round(6).tolist(),
            "lon": plot_df["longitude"].round(6).tolist(),
            "doses": plot_df["doses_aplicadas"].astype(int).tolist(),
            "size": plot_df["marker_size"].round(2).tolist(),
            "hover": plot_df["hover"].tolist(),
        },
        ensure_ascii=False,
    )

    output_path.write_text(
        f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>VacinaBR-PNI - Mapa Plotly</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; background: #f8fafc; }}
    header {{ padding: 14px 18px; border-bottom: 1px solid #ddd; background: white; }}
    h1 {{ font-size: 19px; margin: 0 0 4px; }}
    p {{ margin: 0; color: #555; }}
    #map {{ width: 100vw; height: calc(100vh - 74px); }}
  </style>
</head>
<body>
  <header>
    <h1>VacinaBR-PNI: doses aplicadas por município</h1>
    <p>Mapa gerado com Plotly. Cada ponto representa um município com coordenadas IBGE; tamanho e cor indicam doses aplicadas. Total mapeável: {total_municipalities:,} municípios e {total_doses:,} doses.</p>
  </header>
  <div id="map"></div>
  <script>
    const data = {payload};
    const trace = {{
      type: "scattermapbox",
      lat: data.lat,
      lon: data.lon,
      mode: "markers",
      text: data.hover,
      hoverinfo: "text",
      marker: {{
        size: data.size,
        color: data.doses,
        colorscale: "Blues",
        cmin: Math.min(...data.doses),
        cmax: Math.max(...data.doses),
        opacity: 0.72,
        colorbar: {{
          title: "Doses"
        }}
      }}
    }};

    const layout = {{
      margin: {{ l: 0, r: 0, t: 0, b: 0 }},
      mapbox: {{
        style: "open-street-map",
        center: {{ lat: -14.2, lon: -51.9 }},
        zoom: 3.2
      }}
    }};

    Plotly.newPlot("map", [trace], layout, {{ responsive: true }});
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )


def write_svg_preview(df: pd.DataFrame, output_path: Path) -> None:
    width = 900
    height = 720
    margin = 36
    min_lon, max_lon = df["longitude"].min(), df["longitude"].max()
    min_lat, max_lat = df["latitude"].min(), df["latitude"].max()
    max_doses = max(float(df["doses_aplicadas"].max()), 1.0)
    total_doses = int(df["doses_aplicadas"].sum())
    total_municipalities = len(df)

    def x_for(lon: float) -> float:
        return margin + (lon - min_lon) / (max_lon - min_lon) * (width - 2 * margin)

    def y_for(lat: float) -> float:
        return height - margin - (lat - min_lat) / (max_lat - min_lat) * (
            height - 2 * margin
        )

    circles = []
    labels = []
    top_labels = df.sort_values("doses_aplicadas", ascending=False).head(8)
    top_label_keys = set(
        zip(top_labels["codigo_municipio_paciente"], top_labels["nome_municipio_paciente"])
    )

    for row in df.to_dict(orient="records"):
        x = x_for(float(row["longitude"]))
        y = y_for(float(row["latitude"]))
        doses = float(row["doses_aplicadas"])
        radius = 3 + 16 * (doses / max_doses) ** 0.5
        title = html.escape(
            f"{row.get('nome_municipio_paciente', '')} - {row.get('uf_paciente', '')}: {int(doses)} doses"
        )
        circles.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="#3b82f6" fill-opacity="0.48" stroke="#1f5aa6" stroke-width="1"><title>{title}</title></circle>'
        )
        key = (row.get("codigo_municipio_paciente"), row.get("nome_municipio_paciente"))
        if key in top_label_keys:
            labels.append(
                f'<text x="{x + radius + 4:.1f}" y="{y + 4:.1f}" font-size="12" fill="#1f2937">{html.escape(str(row.get("nome_municipio_paciente", "")))}</text>'
            )

    output_path.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#f8fafc"/>
  <text x="{margin}" y="28" font-family="Arial" font-size="22" font-weight="700" fill="#111827">VacinaBR-PNI: doses aplicadas por município</text>
  <text x="{margin}" y="50" font-family="Arial" font-size="13" fill="#4b5563">Prévia baseada em {total_municipalities:,} municípios e {total_doses:,} doses mapeáveis; use o HTML para mapa interativo.</text>
  <g font-family="Arial">
    {''.join(circles)}
    {''.join(labels)}
  </g>
</svg>
""",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    geography_path = Path(args.geography)
    if args.write_coverage:
        full_df = write_coverage_outputs(
            input_path=input_path,
            geography_path=geography_path,
            analytics_dir=Path(args.analytics_dir),
            docs_dir=Path(args.docs_dir),
        )
        df = full_df.head(args.max_points)
    else:
        df = load_municipalities(input_path, geography_path, args.max_points)

    if df.empty:
        raise ValueError("Nenhum municipio com latitude/longitude foi encontrado.")

    html_path = output_dir / "municipality_map.html"
    plotly_path = output_dir / "municipality_map_plotly.html"
    svg_path = output_dir / "municipality_map.svg"
    write_leaflet_html(df, html_path)
    write_plotly_html(df, plotly_path)
    write_svg_preview(df, svg_path)

    print(f"[map] municipios={len(df):,}")
    print(f"[map] html={html_path}")
    print(f"[map] plotly={plotly_path}")
    print(f"[map] svg={svg_path}")


if __name__ == "__main__":
    main()
