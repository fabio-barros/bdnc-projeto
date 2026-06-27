# Fluxo Google Drive + Google Colab

Este fluxo substitui a coleta pela API. A fonte passa a ser o conjunto de CSVs
mensais publicado no Portal de Dados Abertos do SUS.

## Fonte

Dataset 2025:

https://dadosabertos.saude.gov.br/dataset/doses-aplicadas-pelo-programa-de-nacional-de-imunizacoes-pni-2025

Manifesto local:

`data_sources/pni_2025_csv_manifest.csv`

## Pastas no Google Drive

O notebook usa como raiz:

`MyDrive/VacinaBR-PNI`

Estrutura gerada:

- `data/raw/zip`: ZIPs mensais baixados do portal.
- `data/processed`: Parquets limpos particionados por ano/mes.
- `data/analytics`: CSVs agregados para analise exploratoria.
- `data/vacinabr_pni.duckdb`: banco DuckDB para consultas SQL sobre a base curada.
- `docs`: schema, dicionario, validacao e metadados da fonte.

## Como executar

1. Abra `notebooks/vacinabr_pni_colab_drive_etl.ipynb` no Google Colab.
2. Execute as celulas em ordem.
3. Autorize a montagem do Google Drive.
4. Rode primeiro com `MAX_MONTHS = 1` para validar.
5. Depois troque para `MAX_MONTHS = None` para baixar/processar os 12 meses.

## Observacoes

- Os arquivos brutos podem ser grandes. Garanta espaco suficiente no Drive.
- A camada bruta contem campos sensiveis; publique preferencialmente apenas
  `data/processed`, `data/analytics` e `docs`.
- O processamento e feito em chunks para reduzir uso de memoria no Colab.
