from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
import sys

import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scripts.build_duckdb import build_database
from vacinabr_pni.csv_pipeline import process_csv_manifest


class CsvPipelineTest(unittest.TestCase):
    def test_process_csv_manifest_creates_partitioned_parquet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            docs_dir = root / "docs"
            raw_zip_dir = data_dir / "raw" / "zip"
            raw_zip_dir.mkdir(parents=True)

            zip_path = raw_zip_dir / "vacinacao_jan_2025_csv.zip"
            csv_content = (
                "data_vacina;tipo_sexo_paciente;numero_idade_paciente;"
                "sigla_uf_paciente;codigo_municipio_paciente;nome_municipio_paciente;"
                "codigo_vacina;"
                "sigla_vacina;descricao_vacina;descricao_vacina_fabricante;"
                "st_documento\n"
                "2025-01-14;F;35;SP;355030;Sao Paulo;87;COVID-19;"
                "Vacina covid-19;Fabricante A;FINAL\n"
                "2025-01-15;M;64;SP;355030;Sao Paulo;87;COVID-19;"
                "Vacina covid-19;Fabricante A;FINAL\n"
            )
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("vacinacao_jan_2025.csv", csv_content)

            manifest_path = root / "manifest.csv"
            pd.DataFrame(
                [
                    {
                        "year": 2025,
                        "month": 1,
                        "month_name": "janeiro",
                        "resource_name": "Vacinação - Janeiro 2025",
                        "format": "CSV",
                        "url": "https://example.test/vacinacao_jan_2025_csv.zip",
                        "source_page": "https://example.test/source",
                    }
                ]
            ).to_csv(manifest_path, index=False)

            process_csv_manifest(
                data_dir=data_dir,
                docs_dir=docs_dir,
                manifest_path=manifest_path,
                months=[1],
                download=False,
                chunksize=1,
            )

            parquet_files = sorted(
                (data_dir / "processed").glob("year=2025/month=01/part-*.parquet")
            )
            self.assertEqual(len(parquet_files), 2)
            self.assertTrue((docs_dir / "schema.json").exists())
            self.assertTrue((docs_dir / "data_dictionary.csv").exists())
            self.assertTrue((docs_dir / "source_metadata.json").exists())

            build_database(
                processed_dir=data_dir / "processed",
                analytics_dir=data_dir / "analytics",
                docs_dir=docs_dir,
                db_path=data_dir / "vacinabr_pni.duckdb",
                geography_path=None,
            )

            self.assertTrue((docs_dir / "validation_report.csv").exists())
            self.assertTrue((docs_dir / "run_closure_summary.csv").exists())
            self.assertTrue((data_dir / "analytics" / "monthly_vaccination_summary.csv").exists())

            con = duckdb.connect(str(data_dir / "vacinabr_pni.duckdb"), read_only=True)
            count = con.execute("SELECT count(*) FROM vacinacao_curada").fetchone()[0]
            con.close()
            self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
