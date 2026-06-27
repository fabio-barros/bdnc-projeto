from __future__ import annotations

API_BASE_URL = "https://apidadosabertos.saude.gov.br"
ENDPOINT_TEMPLATE = "/vacinacao/doses-aplicadas-pni-{year}"

UF_TO_REGION = {
    "AC": "Norte",
    "AP": "Norte",
    "AM": "Norte",
    "PA": "Norte",
    "RO": "Norte",
    "RR": "Norte",
    "TO": "Norte",
    "AL": "Nordeste",
    "BA": "Nordeste",
    "CE": "Nordeste",
    "MA": "Nordeste",
    "PB": "Nordeste",
    "PE": "Nordeste",
    "PI": "Nordeste",
    "RN": "Nordeste",
    "SE": "Nordeste",
    "DF": "Centro-Oeste",
    "GO": "Centro-Oeste",
    "MT": "Centro-Oeste",
    "MS": "Centro-Oeste",
    "ES": "Sudeste",
    "MG": "Sudeste",
    "RJ": "Sudeste",
    "SP": "Sudeste",
    "PR": "Sul",
    "RS": "Sul",
    "SC": "Sul",
}

SENSITIVE_COLUMNS = [
    "codigo_paciente",
    "numero_cep_paciente",
]

ESSENTIAL_COLUMNS = [
    "data_vacina",
    "sexo_paciente",
    "numero_idade_paciente",
    "uf_paciente",
    "codigo_municipio_paciente",
    "codigo_vacina",
    "sg_vacina",
]

CANONICAL_COLUMN_ALIASES = {
    "sigla_uf_paciente": "uf_paciente",
    "sigla_uf_estabelecimento": "uf_estabelecimento",
    "sigla_vacina": "sg_vacina",
    "tipo_sexo_paciente": "sexo_paciente",
    "status_documento": "st_documento",
    "nome_razao_social_estabelecimento": "razao_social_estabelecimento",
    "nome_fantasia_estalecimento": "nome_fantasia_estabelecimento",
}
