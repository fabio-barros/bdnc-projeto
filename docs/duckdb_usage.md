# Uso do DuckDB no VacinaBR-PNI

DuckDB entra no projeto como camada analitica sobre os arquivos Parquet curados.
Ele nao substitui o Google Drive nem os arquivos Parquet; ele cria uma base local
consultavel por SQL para demonstrar modelagem, consulta e agregacao dos dados.

Ele sera usado como banco SQL analitico/OLAP embarcado para consultar os
Parquets e materializar tabelas resumo.

## No Colab

Depois de executar a ETL principal e gerar os Parquets em
`MyDrive/VacinaBR-PNI/data/processed`, rode:

```python
!pip install -q duckdb

import duckdb
from pathlib import Path

ROOT = Path('/content/drive/MyDrive/VacinaBR-PNI')
DB_PATH = ROOT / 'data' / 'vacinabr_pni.duckdb'
PARQUET_PATTERN = str(ROOT / 'data' / 'processed' / 'year=*' / 'month=*' / '*.parquet')

con = duckdb.connect(str(DB_PATH))
con.execute(f"""
CREATE OR REPLACE VIEW vacinacao_curada AS
SELECT *
FROM read_parquet('{PARQUET_PATTERN}', union_by_name = true)
""")

con.sql("""
SELECT ano_vacinacao, mes_vacinacao, count(*) AS doses_aplicadas
FROM vacinacao_curada
GROUP BY ano_vacinacao, mes_vacinacao
ORDER BY ano_vacinacao, mes_vacinacao
""").df()
```

## Localmente

Com a venv ativa:

```powershell
pip install -r requirements.txt
python scripts/build_duckdb.py
```

Isso cria:

- `data/vacinabr_pni.duckdb`
- `docs/duckdb_catalog.json`
- tabelas resumo exportadas para `data/analytics/*.csv`

## Tabelas criadas

- `dataset_metadata`
- `monthly_vaccination_summary`
- `state_vaccination_summary`
- `region_vaccination_summary`
- `vaccine_type_summary`
- `manufacturer_summary`
- `age_group_summary`
- `sex_summary`

## Exemplo de consulta

```sql
SELECT
    uf_paciente,
    sg_vacina,
    count(*) AS doses_aplicadas
FROM vacinacao_curada
GROUP BY uf_paciente, sg_vacina
ORDER BY doses_aplicadas DESC
LIMIT 20;
```
