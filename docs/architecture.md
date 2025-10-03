# Arquitetura do Pipeline

## Componentes

1. **Ingest�o (EC2 + Python)**
   - Script `src/ingestion/fetch_b3_data.py` consulta cota��es di�rias via `yfinance`.
   - O script grava arquivos Parquet particionados (`raw/b3/dt=YYYY-MM-DD/ticker=XXX/`) e envia
     diretamente para o bucket S3 informado.

2. **Orquestra��o (S3 ? Lambda ? Glue)**
   - Cada objeto criado em `raw/b3/` dispara a Lambda `start_glue_job`.
   - A fun��o apenas chama `glue.start_job_run` para o job `tech_challenge2_<env>_refine_job`.

3. **Processamento (Glue Spark)**
   - Script `glue/refine_job.py` roda em um job Glue Spark (Glue 4.0).
   - A pipeline realiza: agrega��o por `ticker`/`trade_date`, soma de volume, renomea��o de colunas,
     c�lculo da m�dia m�vel de 5 dias e diferen�a di�ria (`close_delta`).
   - O resultado � salvo em `refined/b3/` como Parquet particionado por `dt` e `ticker` e publicado
     automaticamente no Glue Data Catalog (`b3_daily_quotes_refined`).

4. **Consulta (Athena)**
   - As tabelas `b3_daily_quotes` (bronze) e `b3_daily_quotes_refined` ficam dispon�veis via Athena.
   - O workgroup `tech_challenge2_<env>_wg` salva os resultados em `athena` bucket (`/results/`).

## Layout S3
```
s3://<raw-bucket>/
+-- raw/
�   +-- b3/
�       +-- dt=YYYY-MM-DD/
�           +-- ticker=TICKER/
�               +-- data.parquet
+-- refined/
    +-- b3/
        +-- dt=YYYY-MM-DD/
            +-- ticker=TICKER/
                +-- data.parquet
```

## Vari�veis Terraform importantes
| Vari�vel | Padr�o | Descri��o |
|----------|--------|-----------|
| `manage_iam` | `true` | Cria instance profile/role para EC2. Sete `false` em labs com LabInstanceProfile. |
| `use_existing_iam_roles` | `false` | Cria roles para Glue/Lambda. Em labs, defina `true` e informe os ARNs de `LabRole`. |
| `key_pair_name` | � | Nome da key pair usada para acessar a EC2. |

## Fluxo de execu��o
1. `terraform apply` provisiona toda a infraestrutura.
2. `scripts/run_ingestion.sh` � executado na EC2 e envia Parquet para `raw/b3/`.
3. Evento S3 chama a Lambda que inicia o job Glue.
4. Job Glue grava `refined/b3/` e atualiza o cat�logo.
5. Em Athena execute `MSCK REPAIR TABLE` seguido por consultas SQL.

## Considera��es
- O script de ingest�o aceita vari�veis de ambiente (`TICKERS`, `START_DATE`, `END_DATE`).
- `scripts/run_ingestion.sh` tenta usar a virtualenv `.venvs/tech`; se n�o existir, usa o Python do
  sistema.
- Para ambientes sem permiss�es IAM/S3 completas, utilize as flags mencionadas acima e, se
  necess�rio, crie buckets manualmente e ajuste o state/vari�veis conforme o caso.

Com essa arquitetura, o projeto pode ser executado tanto em contas pessoais quanto em laborat�rios
restritos, bastando ajustar as vari�veis Terraform adequadamente.
