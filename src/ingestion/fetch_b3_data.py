# -*- coding: utf-8 -*-
"""Daily B3 data ingestion script."""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional

import boto3
import pandas as pd
import yfinance as yf
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


RENAMED_COLUMNS = {
    "Open": "open_price",
    "High": "high_price",
    "Low": "low_price",
    "Close": "close_price",
    "Adj Close": "adj_close_price",
    "Volume": "volume",
}
EXPECTED_ORDER = [
    "trade_date",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "adj_close_price",
    "volume",
    "ticker_symbol",
]
NUMERIC_COLUMNS = [
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "adj_close_price",
    "volume",
]


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest B3 quotes and upload Parquet files to S3")
    parser.add_argument("--tickers", nargs="*", default=["^BVSP"], help="Lista de tickers B3 (sufixo .SA)")
    parser.add_argument("--start", type=str, help="Data inicial (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="Data final (YYYY-MM-DD)")
    parser.add_argument("--s3-bucket", type=str, help="Bucket de destino no S3")
    parser.add_argument("--s3-prefix", default="raw", help="Prefixo/pasta base para dados brutos")
    parser.add_argument("--local-output", type=str, help="Diretorio local para testes (Parquet)")
    parser.add_argument("--overwrite", action="store_true", help="Sobrescreve arquivos existentes no S3")
    parser.add_argument("--dry-run", action="store_true", help="Nao envia ao S3; usa saida local se fornecida")
    return parser.parse_args(argv)


def resolve_dates(start: Optional[str], end: Optional[str]) -> tuple[dt.date, dt.date]:
    today = dt.date.today()
    default_end = today
    default_start = today - dt.timedelta(days=7)
    start_date = dt.datetime.strptime(start, "%Y-%m-%d").date() if start else default_start
    end_date = dt.datetime.strptime(end, "%Y-%m-%d").date() if end else default_end
    if start_date > end_date:
        raise ValueError("Data inicial nao pode ser maior que a data final")
    return start_date, end_date


def download_ticker_history(ticker: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    LOGGER.info("Baixando dados de %s de %s ate %s", ticker, start, end)
    data = yf.download(
        ticker,
        start=start.isoformat(),
        end=(end + dt.timedelta(days=1)).isoformat(),
        interval="1d",
        progress=False,
        auto_adjust=False,
    )
    if data.empty:
        LOGGER.warning("Ticker %s retornou dataframe vazio", ticker)
        return pd.DataFrame()

    data.reset_index(inplace=True)
    data.rename(columns={"Date": "trade_date"}, inplace=True)
    data.rename(columns=RENAMED_COLUMNS, inplace=True)
    data["trade_date"] = data["trade_date"].dt.date
    data["ticker_symbol"] = ticker

    missing_cols = set(EXPECTED_ORDER) - set(data.columns)
    if missing_cols:
        raise ValueError(f"Colunas ausentes apos renomear: {sorted(missing_cols)}")

    for column in NUMERIC_COLUMNS:
        if column == "volume":
            data[column] = pd.to_numeric(data[column], errors="coerce").astype("Int64")
        else:
            data[column] = pd.to_numeric(data[column], errors="coerce")

    data = data[EXPECTED_ORDER]
    return data.dropna(subset=["open_price", "close_price"]).reset_index(drop=True)


def partition_and_write(
    dataframe: pd.DataFrame,
    bucket: Optional[str],
    prefix: str,
    local_output: Optional[Path],
    overwrite: bool,
    dry_run: bool,
) -> None:
    if dataframe.empty:
        LOGGER.info("Nada para gravar")
        return

    s3_client = None
    if bucket and not dry_run:
        session = boto3.session.Session()
        s3_client = session.client("s3")

    grouped = dataframe.groupby("trade_date")
    for trade_date, group_df in grouped:
        sanitized_date = trade_date.isoformat()
        tickers = group_df["ticker_symbol"].unique()
        for ticker_symbol in tickers:
            ticker_df = group_df[group_df["ticker_symbol"] == ticker_symbol].copy()
            ticker_slug = ticker_symbol.replace(".", "_").replace("^", "idx_")
            key = f"{prefix}/dt={sanitized_date}/ticker={ticker_slug}/data.parquet"
            LOGGER.info("Gerando particao %s", key)

            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                ticker_df.to_parquet(tmp_path, index=False)

            if local_output:
                dest_dir = local_output / f"dt={sanitized_date}" / f"ticker={ticker_slug}"
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_file = dest_dir / "data.parquet"
                tmp_path.replace(dest_file)
                LOGGER.info("Arquivo local salvo em %s", dest_file)
                continue

            if not s3_client:
                LOGGER.info("Dry-run habilitado; arquivo temporario em %s", tmp_path)
                continue

            should_upload = True
            if not overwrite:
                try:
                    s3_client.head_object(Bucket=bucket, Key=key)
                    LOGGER.info("Pulando %s: ja existe (use --overwrite)", key)
                    should_upload = False
                except ClientError as exc:
                    if exc.response["Error"].get("Code") not in {"404", "NoSuchKey"}:
                        tmp_path.unlink(missing_ok=True)
                        raise

            if should_upload:
                LOGGER.info("Enviando arquivo %s", key)
                s3_client.upload_file(str(tmp_path), bucket, key)

            tmp_path.unlink(missing_ok=True)


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    start_date, end_date = resolve_dates(args.start, args.end)

    local_output = Path(args.local_output).resolve() if args.local_output else None
    if local_output:
        local_output.mkdir(parents=True, exist_ok=True)

    all_frames: List[pd.DataFrame] = []
    for ticker in args.tickers:
        frame = download_ticker_history(ticker, start_date, end_date)
        if not frame.empty:
            all_frames.append(frame)

    if not all_frames:
        LOGGER.warning("Nenhuma particao gerada")
        return

    full_df = pd.concat(all_frames, ignore_index=True)
    partition_and_write(
        full_df,
        bucket=args.s3_bucket,
        prefix=args.s3_prefix,
        local_output=local_output,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()

