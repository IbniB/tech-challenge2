# Tech Challenge – B3 Batch Pipeline

Este repositório contém uma solução completa para o desafio do pipeline batch da B3. O objetivo é
coletar cotações diárias via `yfinance`, armazenar em S3 (camada *raw*), acionar uma Lambda que
inicia um job Glue Spark responsável pelo refino (*silver*) e disponibilizar os dados via
Athena/Glue Data Catalog.

> **Arquitetura detalhada:** veja `docs/architecture.md`.

## Visão geral do fluxo
1. **Terraform** provisiona buckets, EC2 de ingestão, Lambda, Glue Job e catálogos.
2. **Ingestão (`scripts/run_ingestion.sh`)** executa na EC2, baixa cotações e envia Parquet para
   `s3://<raw-bucket>/raw/b3/dt=YYYY-MM-DD/ticker=XXX/`.
3. **Evento S3** dispara a Lambda (`start_glue_job`) que inicia o job Glue `refine_job`.
4. **Glue** agrega, renomeia colunas e calcula métricas (`close_ma_5`, `close_delta`), escrevendo
   `s3://<raw-bucket>/refined/b3/...` particionado por `dt` e `ticker`, além de atualizar a
   tabela `b3_daily_quotes_refined` no Data Catalog.
5. **Athena** consulta tanto `b3_daily_quotes` (bronze) quanto `b3_daily_quotes_refined`.

## Requisitos
- Terraform 1.6+ e AWS CLI configurados.
- Python 3.10+ (para criar a virtualenv na EC2 e localmente).
- Uma chave EC2 (`.pem`) registrada na conta para acesso SSH.

> **Observação:** em ambientes restritos como AWS Academy Labrole, não é permitido criar IAM
> roles/policies. Veja a seção [Executando em ambientes restritos](#executando-em-ambientes-restritos).

## Passo a passo

### 1. Preparar as variáveis do Terraform

1. Copie o arquivo de exemplo:
   ```bash
   cd infra
   cp terraform.tfvars.example terraform.tfvars
   ```
2. Ajuste `terraform.tfvars` com valores da sua conta:
   - `key_pair_name`: nome da key pair EC2.
   - `project_name`/`environment`: usados na composição dos nomes.
   - Deixe `manage_iam = true` e `use_existing_iam_roles = false` para contas próprias.

### 2. Provisionar infraestrutura

```bash
terraform init
terraform apply
```

Ao final, anote os outputs (principalmente `raw_data_bucket`, `athena_results_bucket`,
`ec2_instance_id`, `glue_job_name`).

### 3. Preparar a instância EC2 de ingestão

```bash
ssh -i /caminho/minha-chave.pem ec2-user@<public-dns>

git clone https://github.com/<usuario>/tech_challenge2.git ~/tech_challenge2
cd ~/tech_challenge2
python3 -m venv .venvs/tech
source .venvs/tech/bin/activate
pip install -r requirements.txt
```

### 4. Rodar a ingestão

```bash
export RAW_BUCKET=<valor do output raw_data_bucket>
# Opcional: sobrescreva TICKERS/START_DATE/END_DATE antes do script
scripts/run_ingestion.sh
```

O script grava Parquet em `s3://$RAW_BUCKET/raw/b3/...`. A Lambda
`tech_challenge2_<env>_start_glue` é acionada automaticamente e inicia o Glue job
`tech_challenge2_<env>_refine_job`.

### 5. Validar o pipeline

1. **Glue**: console ? AWS Glue ? Jobs ? `tech_challenge2_<env>_refine_job`. Certifique-se de que
   o run está com status `SUCCEEDED`.
2. **S3**: confirme a existência de arquivos em `raw/b3/` e `refined/b3/`.
3. **Athena** (workgroup `tech_challenge2_<env>_wg`):
   ```sql
   MSCK REPAIR TABLE b3_daily_quotes;
   MSCK REPAIR TABLE b3_daily_quotes_refined;
   SELECT * FROM b3_daily_quotes_refined LIMIT 20;
   ```

### 6. Encerramento

Quando terminar, destrua a infraestrutura:
```bash
terraform destroy
```

## Executando em ambientes restritos (ex.: AWS Academy)

O perfil `LabRole` não permite criar IAM roles/policies. Ajuste `infra/terraform.tfvars`:

```hcl
manage_iam             = false
existing_instance_profile_name = "LabInstanceProfile"
use_existing_iam_roles = true
existing_glue_role_arn   = "arn:aws:iam::<id>:role/LabRole"
existing_lambda_role_arn = "arn:aws:iam::<id>:role/LabRole"
```

Caso o Terraform não consiga criar buckets (erro `AccessDenied`), crie-os manualmente via
console e atualize os nomes em `terraform.tfstate` ou nos outputs. Ainda assim, o pipeline
funcionará: Lambda e Glue reutilizam o `LabRole` existente.

## Estrutura dos diretórios
```
tech_challenge2/
+-- docs/                  # guias adicionais
+-- infra/                 # Terraform
+-- scripts/               # utilitários (ingestão)
+-- src/
¦   +-- ingestion/         # script yfinance
¦   +-- glue/              # script Spark do job Glue
¦   +-- lambda/start_glue_job/
+-- README.md
```

## Atualizações importantes
- `scripts/run_ingestion.sh` agora verifica a virtualenv e permite alterar datas/tickers via
  variáveis de ambiente.
- Terraform suporta tanto criação total (conta própria) quanto reaproveitamento de roles/perfis
  em ambientes restritos (
  `manage_iam`/`use_existing_iam_roles`).
- Veja `docs/architecture.md` para diagramas e decisões técnicas.

## Checklist de validação
- [ ] `terraform apply` executado com sucesso.
- [ ] Ingestão enviou arquivos para `raw/b3/`.
- [ ] Glue job finalizou com `SUCCEEDED` e criou `refined/b3/`.
- [ ] Tabelas `b3_daily_quotes` e `b3_daily_quotes_refined` acessíveis via Athena.

Com isso, o pipeline pode ser executado em qualquer conta AWS (laboratório ou pessoal). Bons estudos!
