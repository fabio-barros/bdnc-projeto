# Fluxo Google Drive + Google Colab

Este fluxo substitui a coleta pela API. A fonte passa a ser o conjunto de CSVs
mensais publicado no Portal de Dados Abertos do SUS, processado pelo notebook
`notebooks/vacinabr_pni_colab_drive_etl.ipynb`.

## Fonte

Dataset 2025:

https://dadosabertos.saude.gov.br/dataset/doses-aplicadas-pelo-programa-de-nacional-de-imunizacoes-pni-2025

Manifesto local:

`data_sources/pni_2025_csv_manifest.csv`

No Colab, o manifesto tambem e salvo em:

`MyDrive/VacinaBR-PNI/docs/pni_2025_csv_manifest.csv`

## Pastas no Google Drive

O notebook usa como raiz:

`MyDrive/VacinaBR-PNI`

Estrutura gerada:

- `data/raw/zip`: ZIPs mensais baixados do portal.
- `data/processed`: Parquets curados particionados por ano e mes.
- `data/analytics`: CSVs agregados para analise exploratoria e relatorios.
- `data/vacinabr_pni.duckdb`: banco DuckDB para consultas SQL sobre a base curada.
- `docs`: schema, dicionario, validacao, metadados, fechamento da run e checks.
- `paper/figures`: figuras geradas no Colab, como o mapa Plotly.

## Como executar

1. Abra `notebooks/vacinabr_pni_colab_drive_etl.ipynb` no Google Colab.
2. Execute as celulas em ordem.
3. Autorize a montagem do Google Drive.
4. Confirme a raiz `DRIVE_ROOT = /content/drive/MyDrive/VacinaBR-PNI`.
5. A celula 6 baixa os ZIPs mensais e reaproveita arquivos ja baixados.
6. Na celula 7, defina manualmente os meses que deseja processar:

```python
MONTHS_TO_PROCESS = [10, 11, 12]  # meses especificos
MONTHS_TO_PROCESS = [1]           # apenas janeiro
MONTHS_TO_PROCESS = None          # todos os meses do manifesto
```

7. Para retomar uma execucao interrompida, mantenha:

```python
CLEAR_OUTPUTS_FOR_SELECTED_MONTHS = False
SKIP_EXISTING_MONTHS = True
RESUME_DEDUPLICATE = False
```

Com essa configuracao, meses que ja possuem `part-*.parquet` sao pulados, e o
notebook processa somente os meses restantes.

8. Use `CLEAR_OUTPUTS_FOR_SELECTED_MONTHS = True` apenas se quiser apagar e
   reprocessar do zero os meses selecionados.
9. Execute a celula 8 para gerar os artefatos finais a partir de todos os
   Parquets existentes.
10. Execute as celulas finais A e B para gerar o resumo da run completa, checks
    de consistencia, CSV municipal mapeavel e mapa Plotly.

## Artefatos finais

Principais arquivos gerados:

- `data/processed/year=*/month=*/*.parquet`
- `data/analytics/*.csv`
- `data/vacinabr_pni.duckdb`
- `docs/validation_report.csv`
- `docs/run_closure_summary.csv`
- `docs/run_consistency_checks.csv`
- `docs/schema.json`
- `docs/data_dictionary.csv`
- `docs/source_metadata.json`
- `docs/map_coverage_report.csv`
- `data/analytics/municipality_vaccination_summary_mappable.csv`
- `paper/figures/municipality_map_plotly.html`

## Observacoes

- Os arquivos brutos e Parquets podem ser grandes. Garanta espaco suficiente no
  Google Drive.
- A camada bruta contem campos sensiveis; publique apenas os artefatos curados e
  documentados.
- O processamento e feito em chunks para reduzir uso de memoria no Colab.
- A deduplicacao global pode consumir muita RAM em execucoes longas. Por isso,
  em retomadas, `RESUME_DEDUPLICATE = False` e a configuracao mais estavel.
- A celula 8 recalcula os agregados e relatorios lendo todos os Parquets
  existentes, incluindo meses processados em execucoes anteriores.
