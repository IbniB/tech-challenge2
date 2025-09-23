# Arquitetura do Pipeline

## Vis�o Geral
- **Ingest�o local** (`src/ingestion/fetch_b3_data.py`): baixa dados di�rios da B3 via `yfinance` e salva arquivos Parquet particionados por data e ticker.
- **Refino local** (`src/glue/refine_data.py`): l� os Parquets gerados, aplica agrega��es, renomeia colunas e calcula m�tricas (m�dia m�vel de 5 dias e varia��o di�ria) usando `pandas`.
- **Publica��o opcional em S3**: ambos os scripts podem enviar os dados brutos/refinados para buckets S3 mantendo a mesma estrutura de parti��es.

## Layout S3 sugerido
```
s3://<bucket>/
+-- raw/
�   +-- dt=YYYY-MM-DD/
�       +-- ticker=XXXX/
+-- refined/
�   +-- dt=YYYY-MM-DD/
�       +-- ticker=XXXX/
```

## Automa��o na AWS (Opcional)
Caso queira orquestrar na AWS sem usar clusters Spark, utilize:
1. **S3 Event Notification** no bucket `raw/` apontando para uma fun��o Lambda.
2. **Lambda** (`src/lambda/start_glue_job/app.py`): recebe o evento e dispara um Glue Job.
3. **AWS Glue Python Shell Job**: configure um job no modo Python Shell (n�o Spark) e utilize o script `src/glue/refine_data.py`. Adicione as bibliotecas `pandas`, `pyarrow` e `boto3` como depend�ncias (via wheel/egg ou `--additional-python-modules`).
4. **Glue Data Catalog**: ap�s o job, crie/atualize a tabela `refined` apontando para o prefixo `s3://<bucket>/refined/` e consulte via Athena.

## Depend�ncias principais
- `boto3`
- `pandas`
- `pyarrow`
- `yfinance`

Use `pip install -r src/ingestion/requirements.txt` para preparar o ambiente local.
