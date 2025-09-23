# Tech Challenge B3 Data Pipeline

Este reposit�rio implementa um pipeline batch para ingest�o, processamento e an�lise de dados de a��es da B3 utilizando AWS S3, Glue, Lambda e Athena.

## Arquitetura de alto n�vel
- **Ingest�o:** script Python (`src/ingestion/fetch_b3_data.py`) usa `yfinance` para extrair cota��es di�rias, salva em Parquet particionado por data e envia para o bucket `raw`.
- **Orquestra��o:** upload no bucket `raw` dispara evento S3 -> Lambda (`src/lambda/start_glue_job/app.py`). A fun��o inicia um job Glue pr�-configurado.
- **Processamento:** job Glue Spark (`src/glue/job_script.py`) l� dados brutos, aplica agrega��es, renomeia colunas e calcula m�tricas baseadas em data. Resultado salvo em `refined` (Parquet) com parti��es por data e ativo.
- **Cat�logo e Consulta:** job publica dados no Glue Data Catalog; a tabela pode ser consultada via Athena com SQL.

## Estrutura do projeto
```
tech_challenge2/
+-- docs/                     # Guias complementares (VS Code, arquitetura)
+-- infra/                    # Scripts IaC (Terraform/CloudFormation) ou instru��es de deploy
+-- src/
�   +-- ingestion/            # Pipelines de ingest�o local/offline
�   +-- lambda/start_glue_job/# C�digo da fun��o Lambda
�   +-- glue/                 # Scripts Glue (Spark)
+-- README.md
```

## Pr�ximos passos
1. Configurar ambiente Python local (virtualenv) e instalar depend�ncias.
2. Implementar script de ingest�o e valid�-lo localmente.
3. Provisionar infraestrutura AWS (S3, IAM, Glue, Lambda, Athena).
4. Empacotar e implantar Lambda/Glue, agendar execu��es e validar consultas via Athena.

## Requisitos resumidos
- Scrap / ingest�o di�ria de dados B3.
- Dados brutos em S3 no formato Parquet particionado por data.
- Evento S3 -> Lambda -> Glue.
- Transforma��es Glue: agrega��o num�rica, renomea��o de colunas, c�lculo baseado em data.
- Dados refinados em Parquet particionados por data e ativo.
- Publica��o autom�tica no Glue Catalog e consulta via Athena.

Veja `docs/` para detalhes de arquitetura e dicas de VS Code.
