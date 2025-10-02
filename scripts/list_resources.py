#!/usr/bin/env python
"""Script that enumerates AWS resource types per provider/service."""
AWS_SERVICES = {
    "compute": [
        "aws_instance",
        "aws_autoscaling_group",
        "aws_launch_template",
        "aws_key_pair",
        "aws_security_group",
        "aws_ebs_volume"
    ],
    "glue": [
        "aws_glue_job",
        "aws_glue_catalog_database",
        "aws_glue_catalog_table"
    ],
    "s3": [
        "aws_s3_bucket",
        "aws_s3_object",
        "aws_s3_bucket_notification",
        "aws_s3_bucket_public_access_block",
        "aws_s3_bucket_server_side_encryption_configuration",
        "aws_s3_bucket_versioning"
    ],
    "lambda": [
        "aws_lambda_function",
        "aws_lambda_permission"
    ],
    "iam": [
        "aws_iam_role",
        "aws_iam_policy",
        "aws_iam_instance_profile",
        "aws_iam_role_policy_attachment"
    ]
}

if __name__ == "__main__":
    for service, resources in AWS_SERVICES.items():
        print(f"service: {service}")
        for resource in resources:
            print(f"  - {resource}")
