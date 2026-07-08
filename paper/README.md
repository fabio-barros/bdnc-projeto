# Artigo SBC - VacinaBR-PNI

Este diretório contém o primeiro rascunho do data paper no formato de seções
recomendado para o template SBC.

Arquivos:

- `main.tex`: texto principal do artigo.
- `references.bib`: referências bibliográficas iniciais.
- `sbc-template.sty`: fallback mínimo para compilar no Overleaf sem o pacote oficial.

## Overleaf

Suba para o Overleaf pelo menos estes arquivos:

- `main.tex`
- `references.bib`
- `sbc-template.sty`

O arquivo `sbc-template.sty` incluído aqui é um fallback para rascunho. Antes da
submissão, substitua-o pelo `sbc-template.sty` oficial da SBC e, se disponível,
troque `\bibliographystyle{plain}` por `\bibliographystyle{sbc}` no final do
`main.tex`.

## Pontos a preencher antes da submissão

- Autores, instituições e e-mails.
- DOI/URL final do Zenodo.
- Volumetria da execução completa com os 12 meses.
- Figuras e tabelas finais escolhidas para o artigo.
- Limite de páginas conforme a chamada específica do evento ou periódico.

## Figuras previstas no `main.tex`

Crie a pasta `paper/figures/` e substitua os placeholders do artigo por:

- `pipeline_architecture.png`: arquitetura da pipeline.
- `dataset_model.png`: modelo lógico do dataset.
- `monthly_volumetry.png`: gráfico de doses por mês.
- `data_quality.png`: gráfico de qualidade por UF ou por mês.
- `municipality_map.png`: mapa municipal opcional, se houver espaço.

## Tabelas a revisar/preencher

- Camadas da arquitetura: já preenchida.
- Principais atributos: já preenchida, mas pode ser reduzida se faltar espaço.
- Volumetria final: preencher depois da execução completa.
- Indicadores de qualidade: preencher depois da execução completa.
- Artefatos de release: revisar depois da publicação no Zenodo.
