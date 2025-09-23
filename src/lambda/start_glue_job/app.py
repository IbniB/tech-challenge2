"""Lambda handler that starts a Glue job when an object is created in S3."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List

import boto3

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

glue = boto3.client("glue")


def extract_s3_details(records: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    details: List[Dict[str, str]] = []
    for record in records:
        s3_info = record.get("s3", {})
        bucket = s3_info.get("bucket", {}).get("name")
        key = s3_info.get("object", {}).get("key")
        if bucket and key:
            details.append({"bucket": bucket, "key": key})
    return details


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    LOGGER.info("Incoming event: %s", json.dumps(event))
    job_name = os.environ.get("GLUE_JOB_NAME")
    if not job_name:
        raise RuntimeError("Environment variable GLUE_JOB_NAME is not set")

    records = event.get("Records", [])
    objects = extract_s3_details(records)
    if not objects:
        LOGGER.warning("No S3 objects found in the event payload")
        return {"status": "ignored"}

    payload = json.dumps(objects)
    arguments = {"--ingestion_manifest": payload}
    LOGGER.info("Starting Glue job %s with arguments %s", job_name, arguments)
    response = glue.start_job_run(JobName=job_name, Arguments=arguments)
    job_run_id = response.get("JobRunId")
    LOGGER.info("Glue job %s started with JobRunId=%s", job_name, job_run_id)
    return {"status": "started", "jobRunId": job_run_id, "objects": objects}
