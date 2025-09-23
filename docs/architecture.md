# Arquitetura do Pipeline

## Visão Geral
- **Ingestão local** (`src/ingestion/fetch_b3_data.py`): baixa dados diários da B3 via `yfinance` e salva arquivos Parquet particionados por data e ticker.
- **Refino local** (`src/glue/refine_data.py`): lê os Parquets gerados, aplica agregações, renomeia colunas e calcula métricas (média móvel de 5 dias e variação diária) usando `pandas`.
- **Publicação opcional em S3**: ambos os scripts podem enviar os dados brutos/refinados para buckets S3 mantendo a mesma estrutura de partições.

## Layout S3 sugerido
```
s3://<bucket>/
+-- raw/
¦   +-- dt=YYYY-MM-DD/
¦       +-- ticker=XXXX/
+-- refined/
¦   +-- dt=YYYY-MM-DD/
¦       +-- ticker=XXXX/
```

## Automação na AWS (Opcional)
Caso queira orquestrar na AWS sem usar clusters Spark, utilize:
1. **S3 Event Notification** no bucket `raw/` apontando para uma função Lambda.
2. **Lambda** (`src/lambda/start_glue_job/app.py`): recebe o evento e dispara um Glue Job.
3. **AWS Glue Python Shell Job**: configure um job no modo Python Shell (não Spark) e utilize o script `src/glue/refine_data.py`. Adicione as bibliotecas `pandas`, `pyarrow` e `boto3` como dependências (via wheel/egg ou `--additional-python-modules`).
4. **Glue Data Catalog**: após o job, crie/atualize a tabela `refined` apontando para o prefixo `s3://<bucket>/refined/` e consulte via Athena.

## Dependências principais
- `boto3`
- `pandas`
- `pyarrow`
- `yfinance`

Use `pip install -r src/ingestion/requirements.txt` para preparar o ambiente local.
