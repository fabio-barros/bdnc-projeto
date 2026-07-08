# VacinaBR-PNI ETL Pipeline

Pipeline para baixar, tratar, validar e documentar dados de doses aplicadas pelo
Programa Nacional de Imunizacoes (PNI). O fluxo recomendado usa os CSVs mensais
do Portal de Dados Abertos do SUS, armazena os arquivos no Google Drive e executa
a ETL no Google Colab.

## Dataset publicado

O pacote de dados publicado no Zenodo esta disponivel pelo DOI:

```text
10.5281/zenodo.21270037
```

Link persistente:

```text
https://doi.org/10.5281/zenodo.21270037
```

## Estrutura

- `scripts/etl_pni_pipeline.py`: pipeline local legada baseada na API.
- `scripts/build_duckdb.py`: cria a base analitica DuckDB a partir dos Parquets.
- `scripts/build_geography_metadata.py`: baixa metadados municipais do IBGE para enriquecimento geografico.
- `scripts/create_release_package.py`: monta uma pasta de release com docs, CSVs e metadados.
- `notebooks/vacinabr_pni_colab_drive_etl.ipynb`: fluxo principal no Google Colab.
- `notebooks/query_duckdb_examples.ipynb`: exemplos de consulta dos Parquets/DuckDB.
- `notebooks/exploratory_analysis.ipynb`: exemplo de analise exploratoria dos CSVs.
- `notebooks/data_quality_report.ipynb`: exemplo de relatorio de qualidade dos dados.
- `dashboard/streamlit_app.py`: dashboard demonstrativo sobre os CSVs analiticos.
- `data_sources/pni_2025_csv_manifest.csv`: manifesto dos ZIPs CSV mensais de 2025.
- `src/vacinabr_pni/config.py`: regioes, aliases, colunas sensiveis e essenciais.
- `src/vacinabr_pni/extract.py`: extracao legada via API.
- `src/vacinabr_pni/transform.py`: limpeza, normalizacao, derivacao de campos e deduplicacao.
- `src/vacinabr_pni/validation.py`: metricas de qualidade dos dados.
- `src/vacinabr_pni/writers.py`: escrita de parquet, agregados analiticos e documentacao.
- `data/`: destino padrao dos dados brutos, processados e agregados.
- `docs/`: destino padrao dos artefatos de documentacao gerados.
- `pipeline_log.txt`: evidencia da ultima execucao da pipeline.

## Fluxo recomendado: Google Drive + Colab

1. Abra `notebooks/vacinabr_pni_colab_drive_etl.ipynb` no Google Colab.
2. Execute as celulas em ordem.
3. Autorize a montagem do Google Drive.
4. Rode primeiro com `MAX_MONTHS = 1`.
5. Quando validar, altere para `MAX_MONTHS = None` e rode os 12 meses.

O notebook baixa os ZIPs para:

```text
MyDrive/VacinaBR-PNI/data/raw/zip
```

E gera:

```text
MyDrive/VacinaBR-PNI/data/processed
MyDrive/VacinaBR-PNI/data/analytics
MyDrive/VacinaBR-PNI/data/vacinabr_pni.duckdb
MyDrive/VacinaBR-PNI/docs
```

Mais detalhes em `docs/colab_drive_workflow.md`.

## Instalacao

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Artefatos para o Data Paper

A execucao gera os arquivos usados como evidencia e documentacao:

- `MyDrive/VacinaBR-PNI/docs/validation_report.csv`
- `MyDrive/VacinaBR-PNI/docs/schema.json`
- `MyDrive/VacinaBR-PNI/docs/data_dictionary.csv`
- `MyDrive/VacinaBR-PNI/docs/source_metadata.json`
- `MyDrive/VacinaBR-PNI/docs/pni_2025_csv_manifest.csv`
- `MyDrive/VacinaBR-PNI/data/analytics/*.csv`
- `MyDrive/VacinaBR-PNI/data/vacinabr_pni.duckdb` quando a camada DuckDB for criada

Consulte `docs/analytics_catalog.md` para a descricao de cada CSV gerado.

## Camada analitica DuckDB

DuckDB pode ser usado para consultar os Parquets curados com SQL e materializar
tabelas resumo. Ele e a camada de banco analitico do projeto.

Uso local:

```powershell
python scripts/build_duckdb.py
```

Para enriquecer municipios com metadados do IBGE antes de criar o DuckDB:

```powershell
python scripts/build_geography_metadata.py
python scripts/build_duckdb.py --geography-path data_sources/ibge_municipalities.csv
```

No Colab, o notebook principal ja cria `vacinabr_pni.duckdb` depois de gerar os
Parquets. Exemplos adicionais estao em `docs/duckdb_usage.md`.

## Testes

```powershell
python -m unittest discover
```

Os testes cobrem criacao do DuckDB, resumos analiticos, enriquecimento
geografico basico e validade JSON dos notebooks.

## Dashboard

```powershell
pip install -r requirements-dashboard.txt
streamlit run dashboard/streamlit_app.py
```

## Publicacao

Para montar uma pasta de release com os artefatos leves:

```powershell
python scripts/create_release_package.py
```

Para incluir tambem o banco DuckDB:

```powershell
python scripts/create_release_package.py --include-duckdb
```

Para incluir os Parquets curados, use `--include-parquet` apenas se houver espaco
suficiente, pois essa camada pode ser grande.

## Execucao local legada

```powershell
python scripts/etl_pni_pipeline.py --years 2025 --max-pages 2 --page-size 1000
```
