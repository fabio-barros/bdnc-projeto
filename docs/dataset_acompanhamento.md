# VacinaBR-PNI - Respostas para Acompanhamento do Dataset

## Contexto e Coleta

### 1. Qual problema científico seu dataset resolve?

O dataset **VacinaBR-PNI** busca resolver um problema prático de acesso,
organização e reuso dos dados abertos de doses aplicadas pelo Programa Nacional
de Imunizações (PNI).

Embora os dados originais sejam públicos, eles são disponibilizados em arquivos
CSV mensais de grande volume. Esses arquivos estão em formato bruto, possuem
campos sensíveis, exigem padronização e não trazem, de forma pronta, agregados
analíticos ou documentação suficiente para uso direto em pesquisas.

Assim, o projeto transforma a fonte original em um dataset curado, documentado,
validado e preparado para análises epidemiológicas, territoriais e de qualidade
dos dados.

### 2. Quais são as fontes dos dados?

As fontes principais são:

- o **Portal de Dados Abertos do SUS**, que disponibiliza os arquivos CSV
  mensais de doses aplicadas pelo PNI em 2025;
- a **API de Localidades do IBGE**, utilizada como fonte auxiliar para enriquecer
  os dados com informações municipais, UF, região e coordenadas geográficas.

A fonte primária dos registros de vacinação é o Ministério da Saúde. A fonte do
IBGE não substitui os dados do PNI; ela apenas complementa os registros com
metadados territoriais padronizados.

### 3. Como ocorre a coleta?

A coleta ocorre por meio de uma pipeline executada, preferencialmente, no Google
Colab, com armazenamento persistente no Google Drive.

O processo ocorre da seguinte forma:

1. Um manifesto lista os arquivos CSV mensais oficiais do PNI.
2. A pipeline baixa os arquivos ZIP mensais do Portal de Dados Abertos do SUS.
3. Os arquivos brutos são armazenados em `data/raw/zip`.
4. Os CSVs são lidos em partes, usando chunks, para lidar com arquivos grandes.
5. Os dados processados são gravados em formato Parquet, em `data/processed`.
6. A camada DuckDB e os CSVs analíticos são gerados a partir dos Parquets.
7. Os documentos de metadados, validação e dicionário de dados são gerados em
   `docs`.

Esse fluxo torna a coleta reprodutível, pois as fontes, os caminhos e as etapas
do processamento ficam documentados no projeto.

### 4. Como os dados são limpos?

A limpeza dos dados é feita pela pipeline ETL/ELT. As principais etapas são:

- padronização dos nomes das colunas;
- aplicação de aliases, para unificar nomes equivalentes;
- conversão de datas, idades e códigos para tipos adequados;
- normalização de campos textuais, como UF, sexo, município, vacina e fabricante;
- remoção de campos sensíveis, como `codigo_paciente` e `numero_cep_paciente`;
- remoção de duplicatas por assinatura de linha;
- criação de campos derivados, como ano, mês, trimestre, semana epidemiológica,
  faixa etária e região do paciente;
    - quantas doses foram aplicadas por mês?
      qual trimestre teve mais vacinação?
      como a vacinação evoluiu por semana epidemiológica?
      -faixa_etaria = 40-59
      idade_valida = true
      registro_completo
- criação de indicadores de qualidade, como `registro_completo`,
  `idade_valida` e `registro_valido_documento`;
- enriquecimento geográfico com dados municipais do IBGE.

O resultado da limpeza é uma base em Parquet mais eficiente, padronizada e segura
para análises.

## Qualidade e Disponibilização

### 5. Como a qualidade será validada?

A qualidade será validada por métricas automáticas geradas pela própria pipeline.
Essas métricas permitem avaliar tanto a estrutura dos dados quanto a completude
e a consistência dos registros.

As principais validações são:

- verificação de schema e de colunas esperadas;
- contagem de registros brutos e processados;
- contagem de duplicatas removidas;
- verificação de campos ausentes;
- validação de idade, considerando o intervalo de 0 a 130 anos;
- validação de datas de vacinação;
- verificação de completude dos campos essenciais;
- validação do status documental do registro;
- confirmação de que campos sensíveis não permanecem na camada processada.

A pipeline gera relatórios como:

- `docs/validation_report.csv`;
- `data/analytics/quality_by_month.csv`;
- `data/analytics/quality_by_state.csv`;
- `data/analytics/quality_by_vaccine.csv`.

Além disso, existem testes automatizados para verificar a criação do DuckDB, a
geração dos agregados, a ausência de campos sensíveis e o funcionamento do
enriquecimento geográfico.

### 6. Quem poderá reutilizar o dataset?

O dataset poderá ser reutilizado por diferentes públicos, incluindo:

- pesquisadores em saúde pública e epidemiologia;
- estudantes e professores de ciência de dados, banco de dados e saúde coletiva;
- analistas de dados em instituições públicas ou privadas;
- equipes que desenvolvem dashboards e visualizações;
- gestores interessados em análises territoriais e temporais de vacinação.

Os arquivos Parquet e DuckDB permitem consultas mais técnicas e escaláveis. Já os
CSVs analíticos permitem uso mais simples em planilhas, ferramentas de BI e
visualizações.

### 7. Onde ele será publicado?

A proposta é publicar o dataset em um repositório público com identificador
persistente, preferencialmente no Zenodo.

O pacote de publicação será montado na pasta `release/VacinaBR-PNI` e deverá
conter:

- dados curados em Parquet;
- CSVs analíticos;
- banco DuckDB;
- documentação;
- dicionário de dados;
- relatórios de qualidade;
- notebooks de exemplo;
- dashboard demonstrativo;
- arquivo de citação `CITATION.cff`;
- licença.

Outras alternativas possíveis são OSF, Figshare ou Hugging Face Datasets.

### 8. Qual licença será utilizada?

A licença prevista para o projeto é a **Creative Commons Attribution 4.0
International (CC BY 4.0)**.

Essa licença permite compartilhar e adaptar o material, inclusive para fins
acadêmicos e analíticos, desde que seja dado o devido crédito aos autores e que
a fonte original dos dados seja indicada.

Como o dataset é derivado de dados públicos do Ministério da Saúde, a
disponibilização também deve deixar claro que:

- a fonte primária é o Portal de Dados Abertos do SUS;
- o VacinaBR-PNI é uma versão curada, transformada e documentada;
- eventuais erros ou limitações da fonte original podem impactar a base derivada.
