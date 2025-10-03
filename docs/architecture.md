# Arquitetura do Pipeline

## Componentes

1. **Ingestão (EC2 + Python)**
   - Script `src/ingestion/fetch_b3_data.py` consulta cotações diárias via `yfinance`.
   - O script grava arquivos Parquet particionados (`raw/b3/dt=YYYY-MM-DD/ticker=XXX/`) e envia
     diretamente para o bucket S3 informado.

2. **Orquestração (S3 ? Lambda ? Glue)**
   - Cada objeto criado em `raw/b3/` dispara a Lambda `start_glue_job`.
   - A função apenas chama `glue.start_job_run` para o job `tech_challenge2_<env>_refine_job`.

3. **Processamento (Glue Spark)**
   - Script `glue/refine_job.py` roda em um job Glue Spark (Glue 4.0).
   - A pipeline realiza: agregação por `ticker`/`trade_date`, soma de volume, renomeação de colunas,
     cálculo da média móvel de 5 dias e diferença diária (`close_delta`).
   - O resultado é salvo em `refined/b3/` como Parquet particionado por `dt` e `ticker` e publicado
     automaticamente no Glue Data Catalog (`b3_daily_quotes_refined`).

4. **Consulta (Athena)**
   - As tabelas `b3_daily_quotes` (bronze) e `b3_daily_quotes_refined` ficam disponíveis via Athena.
   - O workgroup `tech_challenge2_<env>_wg` salva os resultados em `athena` bucket (`/results/`).

## Layout S3
```
s3://<raw-bucket>/
+-- raw/
¦   +-- b3/
¦       +-- dt=YYYY-MM-DD/
¦           +-- ticker=TICKER/
¦               +-- data.parquet
+-- refined/
    +-- b3/
        +-- dt=YYYY-MM-DD/
            +-- ticker=TICKER/
                +-- data.parquet
```

## Variáveis Terraform importantes
| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `manage_iam` | `true` | Cria instance profile/role para EC2. Sete `false` em labs com LabInstanceProfile. |
| `use_existing_iam_roles` | `false` | Cria roles para Glue/Lambda. Em labs, defina `true` e informe os ARNs de `LabRole`. |
| `key_pair_name` | — | Nome da key pair usada para acessar a EC2. |

## Fluxo de execução
1. `terraform apply` provisiona toda a infraestrutura.
2. `scripts/run_ingestion.sh` é executado na EC2 e envia Parquet para `raw/b3/`.
3. Evento S3 chama a Lambda que inicia o job Glue.
4. Job Glue grava `refined/b3/` e atualiza o catálogo.
5. Em Athena execute `MSCK REPAIR TABLE` seguido por consultas SQL.

## Considerações
- O script de ingestão aceita variáveis de ambiente (`TICKERS`, `START_DATE`, `END_DATE`).
- `scripts/run_ingestion.sh` tenta usar a virtualenv `.venvs/tech`; se não existir, usa o Python do
  sistema.
- Para ambientes sem permissões IAM/S3 completas, utilize as flags mencionadas acima e, se
  necessário, crie buckets manualmente e ajuste o state/variáveis conforme o caso.

Com essa arquitetura, o projeto pode ser executado tanto em contas pessoais quanto em laboratórios
restritos, bastando ajustar as variáveis Terraform adequadamente.
