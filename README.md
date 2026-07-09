# VacinaBR-PNI

Pipeline e artefatos para curadoria, validacao, documentacao e publicacao de
dados de doses aplicadas pelo Programa Nacional de Imunizacoes (PNI). O fluxo
oficial do projeto usa os CSVs mensais do Portal de Dados Abertos do SUS,
armazena os arquivos no Google Drive e executa a ETL no Google Colab.

## Dataset publicado

O pacote de dados publicado no Zenodo esta disponivel pelo DOI:

```text
10.5281/zenodo.21271031
```

Link persistente:

```text
https://doi.org/10.5281/zenodo.21271031
```

## Estrutura do repositorio

- `notebooks/vacinabr_pni_colab_drive_etl.ipynb`: fluxo oficial de coleta,
  processamento, validacao e geracao dos artefatos finais no Google Colab.
- `notebooks/query_duckdb_examples.ipynb`: exemplos de consulta com DuckDB.
- `notebooks/exploratory_analysis.ipynb`: exemplo de exploracao dos CSVs
  analiticos.
- `notebooks/data_quality_report.ipynb`: exemplo de relatorio de qualidade.
- `paper/`: fonte LaTeX, referencias e figuras do artigo de dados.
- `docs/`: documentacao do projeto, catalogos, dicionario de dados e relatorios.
- `data_sources/pni_2025_csv_manifest.csv`: manifesto dos ZIPs CSV mensais de
  2025.
- `data_sources/ibge_municipalities.csv`: metadados municipais usados no
  enriquecimento geografico e no mapa.
- `data/analytics/`: exemplos locais de CSVs analiticos.
- `dashboard/streamlit_app.py`: dashboard demonstrativo sobre os CSVs
  analiticos.
- `scripts/` e `src/`: codigo local equivalente ao fluxo do notebook, usado
  para reproduzir a curadoria em ambiente local quando os ZIPs e dependencias
  estiverem disponiveis.

## Fluxo recomendado: Google Drive + Colab

1. Abra `notebooks/vacinabr_pni_colab_drive_etl.ipynb` no Google Colab.
2. Execute as celulas em ordem.
3. Autorize a montagem do Google Drive.
4. Confirme que a celula 3 aponta para:

```text
/content/drive/MyDrive/VacinaBR-PNI
```

5. Na celula 7, escolha os meses que serao processados:

```python
MONTHS_TO_PROCESS = [10, 11, 12]  # meses especificos
MONTHS_TO_PROCESS = [1]           # apenas janeiro
MONTHS_TO_PROCESS = None          # todos os meses do manifesto
```

6. Para retomar uma execucao sem duplicar dados, mantenha:

```python
CLEAR_OUTPUTS_FOR_SELECTED_MONTHS = False
SKIP_EXISTING_MONTHS = True
RESUME_DEDUPLICATE = False
```

7. Use `CLEAR_OUTPUTS_FOR_SELECTED_MONTHS = True` apenas quando quiser apagar e
   reprocessar do zero os meses selecionados.
8. Depois do processamento, execute a celula 8 para gerar os artefatos finais:
   agregados CSV, DuckDB, dicionario de dados, schema, metadados e relatorios de
   validacao.
9. Execute as celulas finais A e B para gerar o resumo da run completa, checks de
   consistencia, CSV municipal mapeavel e mapa Plotly.

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
MyDrive/VacinaBR-PNI/paper/figures
```

Mais detalhes estao em `docs/colab_drive_workflow.md`.

## Saidas principais

A execucao completa gera os arquivos usados como dataset, evidencia e
documentacao:

- `data/processed/year=*/month=*/*.parquet`: registros curados particionados por
  ano e mes.
- `data/analytics/*.csv`: agregados por mes, UF, regiao, municipio, vacina,
  fabricante, sexo, faixa etaria e qualidade.
- `data/vacinabr_pni.duckdb`: banco DuckDB portatil para consultas SQL.
- `docs/validation_report.csv`: metricas globais de volume, completude e
  qualidade.
- `docs/run_closure_summary.csv`: resumo final da execucao anual.
- `docs/run_consistency_checks.csv`: verificacoes de consistencia dos totais.
- `docs/schema.json`: esquema observado na camada curada.
- `docs/data_dictionary.csv`: dicionario de dados.
- `docs/source_metadata.json`: metadados de proveniencia.
- `docs/pni_2025_csv_manifest.csv`: manifesto das fontes oficiais.
- `docs/map_coverage_report.csv`: cobertura dos registros mapeaveis.
- `data/analytics/municipality_vaccination_summary_mappable.csv`: CSV municipal
  com coordenadas validas para visualizacao.
- `paper/figures/municipality_map_plotly.html`: mapa interativo gerado no Colab.

Consulte `docs/analytics_catalog.md` para a descricao de cada CSV analitico.

## Como usar os dados

### DuckDB

```python
import duckdb

con = duckdb.connect("data/vacinabr_pni.duckdb")

con.sql("""
    SELECT uf_paciente, SUM(doses_aplicadas) AS doses_aplicadas
    FROM state_vaccination_summary
    GROUP BY uf_paciente
    ORDER BY doses_aplicadas DESC
""").df()
```

### Parquet direto

```python
import duckdb

duckdb.sql("""
    SELECT uf_paciente, COUNT(*) AS doses_aplicadas
    FROM read_parquet('data/processed/year=*/month=*/*.parquet')
    GROUP BY uf_paciente
    ORDER BY doses_aplicadas DESC
""").df()
```

Exemplos adicionais estao em:

- `notebooks/query_duckdb_examples.ipynb`
- `notebooks/exploratory_analysis.ipynb`
- `notebooks/data_quality_report.ipynb`
- `docs/duckdb_usage.md`

## Instalacao local para notebooks e exemplos

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Qualidade dos dados

A validacao verifica:

- schema e colunas esperadas;
- registros brutos e processados;
- duplicatas removidas;
- campos ausentes;
- idade valida entre 0 e 130 anos;
- datas de vacinacao invalidas ou ausentes;
- completude de campos essenciais;
- validade documental do registro;
- remocao de campos sensiveis da camada processada.

Os relatorios segmentados incluem:

- `quality_by_month.csv`
- `quality_by_state.csv`
- `quality_by_vaccine.csv`

## Privacidade

Campos sensiveis diretos, como identificadores de paciente e CEP do paciente,
nao permanecem na camada Parquet curada. O dataset preserva campos agregaveis e
analiticos necessarios para pesquisa, documentando ausencias e limitacoes nos
relatorios de qualidade.

## Publicacao no Zenodo

O pacote publicado no Zenodo e focado no dataset e contem:

```text
data/
docs/
notebooks/
README.md
CITATION.cff
LICENSE
```

O artigo, o notebook de pipeline e o codigo local permanecem no repositorio do
projeto. O pacote de dados publicado esta identificado pelo DOI:

```text
https://doi.org/10.5281/zenodo.21271031
```

## Testes locais

```powershell
python -m unittest discover
```

Os testes cobrem criacao do DuckDB, resumos analiticos, enriquecimento
geografico basico e validade JSON dos notebooks.

## Execucao local equivalente ao notebook

O fluxo local usa o mesmo manifesto de ZIPs CSV mensais, processa os arquivos em
chunks, grava Parquets em `data/processed/year=*/month=*/part-*.parquet`,
recalcula os agregados com DuckDB e gera os relatorios finais. As diferencas em
relacao ao Colab sao apenas de ambiente: os caminhos sao locais e os ZIPs ficam
em `data/raw/zip`.

Para processar todos os meses do manifesto:

```powershell
python scripts/etl_pni_pipeline.py --source csv
```

Para processar meses especificos:

```powershell
python scripts/etl_pni_pipeline.py --source csv --months 10,11,12
```

Para retomar sem baixar novamente e sem reprocessar meses que ja possuem
`part-*.parquet`:

```powershell
python scripts/etl_pni_pipeline.py --source csv --skip-download --months 10,11,12
```

Para apagar e reprocessar apenas os meses selecionados:

```powershell
python scripts/etl_pni_pipeline.py --source csv --months 10,11,12 --clear-selected-months
```

O fluxo antigo por API ainda existe apenas para comparacao historica:

```powershell
python scripts/etl_pni_pipeline.py --source api --years 2025 --max-pages 2 --page-size 1000
```
