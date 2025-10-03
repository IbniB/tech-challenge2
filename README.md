# Tech Challenge � B3 Batch Pipeline

Este reposit�rio cont�m uma solu��o completa para o desafio do pipeline batch da B3. O objetivo �
coletar cota��es di�rias via `yfinance`, armazen�-las em S3 (camada *raw*), acionar uma Lambda que
inicia um job Glue Spark respons�vel pelo refino (*silver*) e disponibilizar os dados via
Athena/Glue Data Catalog.

> **Arquitetura detalhada:** veja `docs/architecture.md`.

## Vis�o geral do fluxo
1. **Terraform** provisiona buckets, EC2 de ingest�o, Lambda, Glue Job e cat�logos.
2. **Ingest�o (`scripts/run_ingestion.sh`)** executa na EC2, baixa cota��es e envia Parquet para
   `s3://<raw-bucket>/raw/b3/dt=YYYY-MM-DD/ticker=XXX/`.
3. **Evento S3** dispara a Lambda (`start_glue_job`) que inicia o job Glue `refine_job`.
4. **Glue** agrega, renomeia colunas e calcula m�tricas (`close_ma_5`, `close_delta`), escrevendo
   `s3://<raw-bucket>/refined/b3/` particionado por `dt` e `ticker`, al�m de atualizar a
   tabela `b3_daily_quotes_refined` no Data Catalog.
5. **Athena** consulta tanto `b3_daily_quotes` (bronze) quanto `b3_daily_quotes_refined`.

## Requisitos
- Terraform 1.6+ e AWS CLI configurados.
- Python 3.10+ (para criar a virtualenv na EC2 e localmente).
- Uma key pair EC2 (`.pem`) registrada na conta para acesso SSH.

> **Ambientes restritos (ex.: LabRole)**: veja [Executando em ambientes restritos](#executando-em-ambientes-restritos).

## Passo a passo

### 1. Preparar vari�veis do Terraform
```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
```
Edite `terraform.tfvars` e informe:
- `key_pair_name`: nome da sua key pair.
- `project_name`/`environment`: usados na composi��o dos nomes.
- `manage_iam` / `use_existing_iam_roles`: mantenha `true/false` em contas pr�prias; veja nota para labs.
- Opcional: `subnet_id` se quiser usar uma subnet espec�fica.

### 2. Provisionar infraestrutura
```bash
terraform init
terraform apply
```
Anote os `outputs` (`raw_data_bucket`, `athena_results_bucket`, `ec2_instance_id`, `glue_job_name`, etc.).

### 3. Preparar a EC2 de ingest�o
```bash
ssh -i /caminho/minha-chave.pem ec2-user@<dns-p�blico>

git clone https://github.com/<usuario>/tech_challenge2.git ~/tech_challenge2
cd ~/tech_challenge2
python3 -m venv .venvs/tech
source .venvs/tech/bin/activate
pip install -r requirements.txt
```

### 4. Executar a ingest�o
```bash
export RAW_BUCKET=<raw_data_bucket>
# Ajuste TICKERS/START_DATE/END_DATE se quiser
scripts/run_ingestion.sh
```
O script grava Parquet em `raw/b3/...` e o evento S3 inicia o Glue job automaticamente.

### 5. Validar o pipeline
1. **Glue**: Console ? Glue ? Jobs ? `tech_challenge2_<env>_refine_job`. Verifique o status `SUCCEEDED`.
2. **S3**: confirme arquivos nas pastas `raw/b3/` e `refined/b3/`.
3. **Athena** (workgroup `tech_challenge2_<env>_wg`):
   ```sql
   MSCK REPAIR TABLE b3_daily_quotes;
   MSCK REPAIR TABLE b3_daily_quotes_refined;
   SELECT * FROM b3_daily_quotes_refined LIMIT 20;
   ```

### 6. Encerramento
```bash
terraform destroy
```
Isso remove EC2, buckets, Lambda, Glue e cat�logos criados.

## Execu��o em ambientes restritos
O perfil `LabRole` n�o permite criar IAM roles/policies. Ajuste `terraform.tfvars`:
```hcl
manage_iam             = false
existing_instance_profile_name = "LabInstanceProfile"
use_existing_iam_roles = true
existing_glue_role_arn   = "arn:aws:iam::<id>:role/LabRole"
existing_lambda_role_arn = "arn:aws:iam::<id>:role/LabRole"
```
Se a cria��o de buckets tamb�m estiver bloqueada, crie-os manualmente e atualize os nomes no state/output.

## Estrutura dos diret�rios
```
tech_challenge2/
+-- docs/                  # guias adicionais (VS Code, arquitetura)
+-- infra/                 # Terraform
+-- scripts/               # utilit�rios (ingest�o)
+-- src/
�   +-- ingestion/         # script yfinance
�   +-- glue/              # script Spark do job Glue
�   +-- lambda/start_glue_job/
+-- README.md
```

## Troubleshooting r�pido
- **Glue falha / �Ticker column not found�**: geralmente os arquivos `raw/b3/` ainda n�o foram criados.
  Rode `aws s3 ls s3://<raw_bucket>/raw/b3/` para conferir; se estiver vazio, execute a ingest�o novamente.
- **Nenhum dado processado**: o job agora encerra silenciosamente quando n�o encontra registros.
- **Organiza��o trocou os nomes dos buckets**: atualize `terraform.tfvars` e reaplique.
- **Atualizar o script do Glue** ap�s altera��es: `terraform apply -target=aws_s3_object.glue_script`
  ou `aws s3 cp glue/refine_job.py s3://<athena-bucket>/scripts/refine_job.py`.

## Checklist final
- [ ] `terraform apply` executado sem erros.
- [ ] Ingest�o gerou parti��es em `raw/b3/`.
- [ ] Glue job finalizou com `SUCCEEDED`.
- [ ] Athena retorna linhas de `b3_daily_quotes_refined`.

Com isso, o pipeline est� pronto para rodar tanto na sua conta AWS quanto em ambientes controlados. Boas an�lises!
