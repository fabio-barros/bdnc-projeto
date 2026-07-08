from __future__ import annotations

import json
import unittest
from pathlib import Path


class NotebookIntegrityTest(unittest.TestCase):
    def test_notebooks_are_valid_json(self) -> None:
        notebooks = [
            Path("notebooks/vacinabr_pni_colab_drive_etl.ipynb"),
            Path("notebooks/query_duckdb_examples.ipynb"),
            Path("notebooks/exploratory_analysis.ipynb"),
            Path("notebooks/data_quality_report.ipynb"),
        ]

        for notebook in notebooks:
            if not notebook.exists():
                continue

            with self.subTest(notebook=str(notebook)):
                with notebook.open(encoding="utf-8") as file:
                    parsed = json.load(file)

                self.assertEqual(parsed["nbformat"], 4)
                self.assertIn("cells", parsed)


if __name__ == "__main__":
    unittest.main()
