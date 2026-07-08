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

Com enriquecimento geografico:

```powershell
python scripts/build_geography_metadata.py
python scripts/build_duckdb.py --geography-path data_sources/ibge_municipalities.csv
```

Isso cria:

- `data/vacinabr_pni.duckdb`
- `docs/duckdb_catalog.json`
- tabelas resumo exportadas para `data/analytics/*.csv`

Se `data_sources/ibge_municipalities.csv` existir, tambem cria:

- `municipality_geography`: dimensao municipal com metadados IBGE.
- `vacinacao_curada_geo`: view que une os registros curados aos metadados municipais.

## Tabelas criadas

- `dataset_metadata`
- `municipality_geography` quando o CSV geografico estiver disponivel
- `monthly_vaccination_summary`
- `state_vaccination_summary`
- `region_vaccination_summary`
- `vaccine_type_summary`
- `manufacturer_summary`
- `age_group_summary`
- `sex_summary`
- `monthly_vaccine_type_summary`
- `state_vaccine_type_summary`
- `municipality_vaccination_summary`
- `state_municipality_vaccine_summary`
- `quality_by_month`
- `quality_by_state`
- `quality_by_vaccine`
- `vaccine_dictionary`

## Exemplo de consulta

```sql
SELECT
    uf_paciente,
    sg_vacina,
    descricao_vacina,
    count(*) AS doses_aplicadas
FROM vacinacao_curada
GROUP BY uf_paciente, sg_vacina, descricao_vacina
ORDER BY doses_aplicadas DESC
LIMIT 20;
```

Para consultas com metadados municipais, use `vacinacao_curada_geo`:

```sql
SELECT
    uf_paciente,
    nome_municipio_paciente,
    latitude,
    longitude,
    count(*) AS doses_aplicadas
FROM vacinacao_curada_geo
GROUP BY uf_paciente, nome_municipio_paciente, latitude, longitude
ORDER BY doses_aplicadas DESC
LIMIT 20;
```

## Qualidade por UF

```sql
SELECT
    uf_paciente,
    total_registros,
    pct_completude,
    pct_idade_valida,
    pct_documento_valido
FROM quality_by_state
ORDER BY total_registros DESC;
```

## Municipios com mais registros

```sql
SELECT
    uf_paciente,
    codigo_municipio_paciente,
    nome_municipio_paciente,
    doses_aplicadas
FROM municipality_vaccination_summary
ORDER BY doses_aplicadas DESC
LIMIT 20;
```
