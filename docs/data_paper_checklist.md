# Checklist do Data Paper VacinaBR-PNI

## Objetivo

Construir um dataset curado, enriquecido, validado, documentado e reutilizavel
de doses aplicadas pelo Programa Nacional de Imunizacoes.

## Escopo inicial

- Ano inicial: 2025.
- Fonte: CSVs mensais do Portal de Dados Abertos do SUS.
- Dataset: `doses-aplicadas-pelo-programa-de-nacional-de-imunizacoes-pni-2025`.
- Formato processado: Parquet particionado por ano e mes.

## Evidencias geradas pela pipeline

- `MyDrive/VacinaBR-PNI/docs/validation_report.csv`: metricas de qualidade.
- `MyDrive/VacinaBR-PNI/docs/schema.json`: esquema tecnico da base processada.
- `MyDrive/VacinaBR-PNI/docs/data_dictionary.csv`: dicionario de dados.
- `MyDrive/VacinaBR-PNI/docs/source_metadata.json`: fonte e recursos mensais.
- `MyDrive/VacinaBR-PNI/docs/pni_2025_csv_manifest.csv`: manifesto dos ZIPs.
- `MyDrive/VacinaBR-PNI/data/analytics/*.csv`: agregados exploratorios.
- `MyDrive/VacinaBR-PNI/data/vacinabr_pni.duckdb`: banco analitico DuckDB
  criado a partir dos Parquets curados.

## Regras de privacidade

- `codigo_paciente` e `numero_cep_paciente` sao removidos por padrao da camada
  processada.
- A camada `data/raw` nao deve ser publicada publicamente sem avaliacao de
  privacidade.
- Para Zenodo, priorize `data/processed`, `data/analytics`, `docs`, `scripts`,
  `src`, `README.md`, `requirements.txt`, `LICENSE` e `CITATION.cff`.

## Proximos incrementos possiveis

- Processar os 12 meses de 2025 no Colab.
- Criar a camada DuckDB a partir dos Parquets curados.
- Incorporar os CSVs mensais de 2024 em manifesto separado, se o escopo voltar a
  incluir 2024.
- Adicionar camada `data/quarantine` para registros removidos ou marcados por
  regras de qualidade.
- Criar notebook ou script de caso de uso exploratorio.
- Atualizar `CITATION.cff` com todos os autores e URL/DOI definitivo.
