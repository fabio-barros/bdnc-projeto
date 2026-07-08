# Enriquecimento Geografico

O VacinaBR-PNI pode enriquecer os registros curados com metadados municipais do
IBGE. A etapa e opcional, mas recomendada para analises territoriais e mapas.

## Geracao da dimensao municipal

```powershell
python scripts/build_geography_metadata.py
```

Saida:

```text
data_sources/ibge_municipalities.csv
```

Campos principais:

- `codigo_municipio`: codigo municipal de 6 digitos usado para compatibilidade com o PNI.
- `nome_municipio_ibge`: nome oficial do municipio no IBGE.
- `uf`: sigla da unidade federativa.
- `nome_uf`: nome da unidade federativa.
- `regiao`: regiao brasileira.
- `latitude` e `longitude`: coordenadas auxiliares quando disponiveis.

## Uso no DuckDB

```powershell
python scripts/build_duckdb.py --geography-path data_sources/ibge_municipalities.csv
```

Quando o arquivo existe, o DuckDB cria:

- `municipality_geography`
- `vacinacao_curada_geo`

Os CSVs `municipality_vaccination_summary.csv` e
`state_municipality_vaccine_summary.csv` passam a incluir coordenadas.

## Caso de uso

Com a camada geografica, pesquisadores podem:

- mapear municipios com maior volume de doses;
- comparar distribuicao de vacinas por territorio;
- cruzar indicadores de qualidade com UF, regiao e municipio;
- exportar os CSVs para ferramentas de BI ou SIG.
