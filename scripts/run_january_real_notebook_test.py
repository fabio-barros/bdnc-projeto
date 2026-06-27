from __future__ import annotations

import json
from pathlib import Path


def display(value):
    if hasattr(value, "to_string"):
        print(value.to_string(index=False))
    else:
        print(value)


def main() -> None:
    notebook_path = Path("notebooks/vacinabr_pni_colab_drive_etl.ipynb")
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    namespace = {"display": display}

    for index in range(3, 9):
        source = "".join(notebook["cells"][index]["source"])
        source = source.replace(
            "DRIVE_ROOT = Path('/content/drive/MyDrive/VacinaBR-PNI')",
            "DRIVE_ROOT = Path('tmp/january_real_test')",
        )
        source = source.replace(
            "RAW_ZIP_DIR = DRIVE_ROOT / 'data' / 'raw' / 'zip'",
            "RAW_ZIP_DIR = Path('data/raw/zip')",
        )
        source = source.replace(
            "MAX_MONTHS = 1  # Use 1 para teste. Troque para None para processar os 12 meses.",
            "MAX_MONTHS = 1  # Local test: January only.",
        )
        print(f"[runner] executing notebook cell {index}")
        exec(compile(source, f"{notebook_path}:cell-{index}", "exec"), namespace)

    output_root = Path("tmp/january_real_test")
    parquet_files = sorted((output_root / "data" / "processed").glob("year=*/month=*/*.parquet"))
    print(f"[runner] parquet_files={len(parquet_files)}")
    print(f"[runner] duckdb={(output_root / 'data' / 'vacinabr_pni.duckdb')}")


if __name__ == "__main__":
    main()
