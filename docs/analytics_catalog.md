# Catalogo dos CSVs Analiticos

Os arquivos em `data/analytics` sao agregados derivados dos Parquets curados.
Eles existem para facilitar exploracao rapida, graficos, validacao e uso em BI.

## Resumos principais

- `monthly_vaccination_summary.csv`: doses por ano e mes.
- `region_vaccination_summary.csv`: doses por regiao brasileira do paciente.
- `state_vaccination_summary.csv`: doses por UF do paciente.
- `municipality_vaccination_summary.csv`: doses por municipio do paciente; inclui `latitude` e `longitude` quando o enriquecimento IBGE estiver disponivel.
- `vaccine_type_summary.csv`: doses por sigla e descricao da vacina.
- `manufacturer_summary.csv`: doses por fabricante informado.
- `age_group_summary.csv`: doses por faixa etaria derivada.
- `sex_summary.csv`: doses por sexo informado.

## Cruzamentos analiticos

- `monthly_vaccine_type_summary.csv`: doses por ano, mes, sigla e descricao da vacina.
- `state_vaccine_type_summary.csv`: doses por UF, sigla e descricao da vacina.
- `state_municipality_vaccine_summary.csv`: doses por UF, municipio, sigla e descricao da vacina; inclui coordenadas quando disponiveis.

## Qualidade dos dados

- `quality_by_month.csv`: completude, idade valida e documento valido por mes.
- `quality_by_state.csv`: completude, idade valida e documento valido por UF.
- `quality_by_vaccine.csv`: completude, idade valida e documento valido por vacina.

## Dimensoes auxiliares

- `vaccine_dictionary.csv`: relacao observada entre `codigo_vacina`, `sg_vacina` e `descricao_vacina`.

## Enriquecimento geografico

O script `scripts/build_geography_metadata.py` gera
`data_sources/ibge_municipalities.csv` com codigo municipal, nome IBGE, UF,
regiao e coordenadas auxiliares. Quando esse arquivo existe, `scripts/build_duckdb.py`
cria a tabela `municipality_geography` e a view `vacinacao_curada_geo`, que
alimenta os resumos municipais.

## Camadas

```text
Raw ZIPs      -> fonte oficial bruta
Parquet       -> base curada completa em nivel de registro
DuckDB        -> camada SQL sobre os Parquets
Analytics CSV -> resumos prontos para leitura e graficos
```
