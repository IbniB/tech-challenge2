#!/usr/bin/env bash
set -euo pipefail

TICKERS=${TICKERS:-"PETR4.SA VALE3.SA ITUB4.SA BBDC4.SA BBAS3.SA ABEV3.SA MGLU3.SA LREN3.SA B3SA3.SA WEGE3.SA SUZB3.SA KLBN11.SA GGBR4.SA CSNA3.SA PRIO3.SA ELET3.SA RADL3.SA HAPV3.SA BRFS3.SA"}
START_DATE=${START_DATE:-"$(date -u -d '7 days ago' +%Y-%m-%d)"}
END_DATE=${END_DATE:-"$(date -u +%Y-%m-%d)"}
S3_PREFIX=${S3_PREFIX:-"raw/b3"}

if [[ -z "${RAW_BUCKET:-}" ]]; then
  echo "RAW_BUCKET environment variable not set." >&2
  exit 1
fi

PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source "${PROJECT_DIR}/.venvs/tech/bin/activate"
cd "${PROJECT_DIR}"

python src/ingestion/fetch_b3_data.py \
  --tickers ${TICKERS} \
  --s3-bucket "${RAW_BUCKET}" \
  --s3-prefix "${S3_PREFIX}" \
  --start "${START_DATE}" \
  --end "${END_DATE}" \
  --overwrite
