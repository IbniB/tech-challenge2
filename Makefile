TF_DIR=infra
TF=terraform
SSH_KEY?=C:/Users/ibnib/Downloads/tech-key-pair2209.pem
EC2_HOST?=ec2-user@54.162.181.131
SYNC_PATH?=$(EC2_HOST):~/tech_challenge2

.PHONY: tf-init tf-plan tf-apply tf-destroy sync-code ssh

tf-init:
	cd $(TF_DIR) && $(TF) init

# assumes AWS credentials already exported in the shell
# you can override TF_CLI_ARGS_plan/apply with -var-file etc.
tf-plan:
	cd $(TF_DIR) && $(TF) plan

tf-apply:
	cd $(TF_DIR) && $(TF) apply

tf-destroy:
	cd $(TF_DIR) && $(TF) destroy

sync-code:
	scp -i "$(SSH_KEY)" -r src requirements.txt $(SYNC_PATH)/

ssh:
	ssh -i "$(SSH_KEY)" $(EC2_HOST)
