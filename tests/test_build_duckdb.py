from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import duckdb
import pandas as pd

from scripts.build_duckdb import build_database


class BuildDuckDBTest(unittest.TestCase):
    def test_build_database_creates_geo_view_and_analytics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed_dir = root / "data" / "processed"
            analytics_dir = root / "data" / "analytics"
            docs_dir = root / "docs"
            db_path = root / "data" / "vacinabr_pni.duckdb"
            parquet_dir = processed_dir / "year=2025" / "month=01"
            parquet_dir.mkdir(parents=True)

            records = pd.DataFrame(
                [
                    {
                        "ano_vacinacao": 2025,
                        "mes_vacinacao": 1,
                        "uf_paciente": "SP",
                        "regiao_paciente": "Sudeste",
                        "codigo_municipio_paciente": "355030",
                        "nome_municipio_paciente": "Sao Paulo",
                        "sg_vacina": "COVID-19",
                        "descricao_vacina": "Vacina covid-19",
                        "descricao_vacina_fabricante": "Fabricante A",
                        "faixa_etaria": "30-39",
                        "sexo_paciente": "F",
                        "registro_completo": True,
                        "idade_valida": True,
                        "registro_valido_documento": True,
                        "codigo_vacina": "87",
                    },
                    {
                        "ano_vacinacao": 2025,
                        "mes_vacinacao": 1,
                        "uf_paciente": "SP",
                        "regiao_paciente": "Sudeste",
                        "codigo_municipio_paciente": "355030",
                        "nome_municipio_paciente": "Sao Paulo",
                        "sg_vacina": "COVID-19",
                        "descricao_vacina": "Vacina covid-19",
                        "descricao_vacina_fabricante": "Fabricante A",
                        "faixa_etaria": "40-49",
                        "sexo_paciente": "M",
                        "registro_completo": False,
                        "idade_valida": True,
                        "registro_valido_documento": False,
                        "codigo_vacina": "87",
                    },
                ]
            )
            records.to_parquet(parquet_dir / "part-000000.parquet", index=False)

            geography_path = root / "data_sources" / "ibge_municipalities.csv"
            geography_path.parent.mkdir(parents=True)
            pd.DataFrame(
                [
                    {
                        "codigo_municipio": "355030",
                        "nome_municipio_ibge": "Sao Paulo",
                        "uf": "SP",
                        "nome_uf": "Sao Paulo",
                        "regiao": "Sudeste",
                        "nome_regiao": "Sudeste",
                        "latitude": -23.5505,
                        "longitude": -46.6333,
                    }
                ]
            ).to_csv(geography_path, index=False)

            build_database(
                processed_dir=processed_dir,
                analytics_dir=analytics_dir,
                docs_dir=docs_dir,
                db_path=db_path,
                geography_path=geography_path,
            )

            self.assertTrue(db_path.exists())
            self.assertTrue((analytics_dir / "quality_by_state.csv").exists())
            self.assertTrue((analytics_dir / "vaccine_dictionary.csv").exists())
            self.assertTrue((docs_dir / "duckdb_catalog.json").exists())

            municipality = pd.read_csv(
                analytics_dir / "municipality_vaccination_summary.csv"
            )
            self.assertIn("latitude", municipality.columns)
            self.assertEqual(municipality.loc[0, "doses_aplicadas"], 2)
            self.assertAlmostEqual(municipality.loc[0, "latitude"], -23.5505)

            parquet_columns = set(
                pd.read_parquet(parquet_dir / "part-000000.parquet").columns
            )
            self.assertNotIn("codigo_paciente", parquet_columns)
            self.assertNotIn("numero_cep_paciente", parquet_columns)

            con = duckdb.connect(str(db_path), read_only=True)
            count = con.execute("SELECT count(*) FROM vacinacao_curada_geo").fetchone()[0]
            tables = {
                row[0]
                for row in con.execute(
                    "SELECT table_name FROM information_schema.tables"
                ).fetchall()
            }
            con.close()

            self.assertEqual(count, 2)
            self.assertIn("quality_by_vaccine", tables)
            self.assertIn("municipality_geography", tables)


if __name__ == "__main__":
    unittest.main()
