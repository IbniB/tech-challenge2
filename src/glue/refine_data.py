"""Refine B3 parquet data locally using pandas."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable, Optional

import boto3
import pandas as pd
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)

RENAME_MAP = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "adj_close",
    "Volume": "volume",
}


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refina dados parquet gerados pela ingestão")
    parser.add_argument("--input", required=True, help="Diretório local ou prefixo S3 com dados brutos")
    parser.add_argument("--output", required=True, help="Diretório local para salvar parquet refinado")
    parser.add_argument("--s3-bucket", help="Bucket S3 para upload opcional")
    parser.add_argument("--s3-prefix", default="refined", help="Prefixo S3 para upload opcional")
    parser.add_argument("--overwrite", action="store_true", help="Sobrescreve partições existentes no S3")
    parser.add_argument("--dry-run", action="store_true", help="Não envia ao S3 mesmo se bucket for informado")
    return parser.parse_args(argv)


def sanitize_ticker(ticker: str) -> str:
    return ticker.replace(".", "_").replace("^", "idx_")


def load_dataset(path: str) -> pd.DataFrame:
    LOGGER.info("Lendo parquet de %s", path)
    df = pd.read_parquet(path, engine="pyarrow")
    if "trade_date" in df.columns:
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
    return df


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    existing = {key: value for key, value in RENAME_MAP.items() if key in df.columns}
    return df.rename(columns=existing)


def apply_transformations(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["ticker", "trade_date"], as_index=False)
        .agg(
            open_price=("open", "first"),
            high_price=("high", "first"),
            low_price=("low", "first"),
            close_price=("close", "first"),
            adj_close_price=("adj_close", "first"),
            volume_total=("volume", "sum"),
        )
    )
    grouped.sort_values(["ticker", "trade_date"], inplace=True)

    grouped["close_ma_5"] = (
        grouped.groupby("ticker")["close_price"].transform(lambda s: s.rolling(5, min_periods=1).mean())
    )
    grouped["close_delta"] = grouped.groupby("ticker")["close_price"].diff()
    grouped["dt"] = pd.to_datetime(grouped["trade_date"]).dt.strftime("%Y-%m-%d")
    grouped["ticker_partition"] = grouped["ticker"].map(sanitize_ticker)
    return grouped


def write_partitions(df: pd.DataFrame, output_dir: Path) -> None:
    for (dt_value, ticker_part), subset in df.groupby(["dt", "ticker_partition"]):
        target_dir = output_dir / f"dt={dt_value}" / f"ticker={ticker_part}"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / "data.parquet"
        subset.drop(columns=["ticker_partition"], inplace=False).to_parquet(target_file, index=False)
        LOGGER.info("Partição escrita em %s", target_file)


def upload_partitions(output_dir: Path, bucket: str, prefix: str, overwrite: bool, dry_run: bool) -> None:
    if dry_run:
        LOGGER.info("Dry-run habilitado; pulando upload")
        return

    prefix = prefix.strip("/")
    client = boto3.client("s3")
    for file_path in output_dir.rglob("data.parquet"):
        relative = file_path.relative_to(output_dir).as_posix()
        key = f"{prefix}/{relative}"
        try:
            if not overwrite:
                client.head_object(Bucket=bucket, Key=key)
                LOGGER.info("Pulando upload de %s (já existe)", key)
                continue
        except ClientError as exc:
            if exc.response["Error"].get("Code") not in {"404", "NoSuchKey"}:
                raise
        LOGGER.info("Enviando %s", key)
        client.upload_file(str(file_path), bucket, key)


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataset(args.input)
    if df.empty:
        LOGGER.warning("DataFrame vazio; nada a fazer")
        return

    renamed = rename_columns(df)
    refined = apply_transformations(renamed)
    write_partitions(refined, output_dir)

    if args.s3_bucket:
        upload_partitions(output_dir, args.s3_bucket, args.s3_prefix, args.overwrite, args.dry_run)


if __name__ == "__main__":
    main()
