# Tech Challenge B3 Data Pipeline

Este repositório implementa um pipeline batch para ingestão, processamento e análise de dados de ações da B3 utilizando AWS S3, Glue, Lambda e Athena.

## Arquitetura de alto nível
- **Ingestão:** script Python (`src/ingestion/fetch_b3_data.py`) usa `yfinance` para extrair cotações diárias, salva em Parquet particionado por data e envia para o bucket `raw`.
- **Orquestração:** upload no bucket `raw` dispara evento S3 -> Lambda (`src/lambda/start_glue_job/app.py`). A função inicia um job Glue pré-configurado.
- **Processamento:** job Glue Spark (`src/glue/job_script.py`) lê dados brutos, aplica agregações, renomeia colunas e calcula métricas baseadas em data. Resultado salvo em `refined` (Parquet) com partições por data e ativo.
- **Catálogo e Consulta:** job publica dados no Glue Data Catalog; a tabela pode ser consultada via Athena com SQL.

## Estrutura do projeto
```
tech_challenge2/
+-- docs/                     # Guias complementares (VS Code, arquitetura)
+-- infra/                    # Scripts IaC (Terraform/CloudFormation) ou instruções de deploy
+-- src/
¦   +-- ingestion/            # Pipelines de ingestão local/offline
¦   +-- lambda/start_glue_job/# Código da função Lambda
¦   +-- glue/                 # Scripts Glue (Spark)
+-- README.md
```

## Próximos passos
1. Configurar ambiente Python local (virtualenv) e instalar dependências.
2. Implementar script de ingestão e validá-lo localmente.
3. Provisionar infraestrutura AWS (S3, IAM, Glue, Lambda, Athena).
4. Empacotar e implantar Lambda/Glue, agendar execuções e validar consultas via Athena.

## Requisitos resumidos
- Scrap / ingestão diária de dados B3.
- Dados brutos em S3 no formato Parquet particionado por data.
- Evento S3 -> Lambda -> Glue.
- Transformações Glue: agregação numérica, renomeação de colunas, cálculo baseado em data.
- Dados refinados em Parquet particionados por data e ativo.
- Publicação automática no Glue Catalog e consulta via Athena.

Veja `docs/` para detalhes de arquitetura e dicas de VS Code.
