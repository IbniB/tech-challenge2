import sys
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from awsglue.dynamicframe import DynamicFrame
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql import Window

args = getResolvedOptions(sys.argv, [
    "JOB_NAME",
    "raw_path",
    "output_path",
    "catalog_database",
    "raw_table",
    "refined_table"
])

sc = SparkContext()
glue_context = GlueContext(sc)
spark = glue_context.spark_session
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

raw_path = args["raw_path"].rstrip("/")
output_path = args["output_path"].rstrip("/")
raw_database = args["catalog_database"]
raw_table = args["raw_table"]
refined_table = args["refined_table"]

raw_frame = glue_context.create_dynamic_frame_from_catalog(
    database=raw_database,
    table_name=raw_table
)
raw_df = raw_frame.toDF()

if "ticker_symbol" not in raw_df.columns:
    if "ticker" in raw_df.columns:
        raw_df = raw_df.withColumnRenamed("ticker", "ticker_symbol")
    else:
        available = ", ".join(raw_df.columns)
        raise ValueError(f"Ticker column not found in raw dataset. Available columns: {available}")

if "trade_date" not in raw_df.columns:
    raise ValueError("trade_date column not found in raw dataset")

window_spec = Window.partitionBy("ticker_symbol").orderBy("trade_date")
rolling_window = window_spec.rowsBetween(-4, 0)

aggregated = (
    raw_df.groupBy("ticker_symbol", "trade_date")
    .agg(
        F.first("open_price").alias("opening_price"),
        F.first("high_price").alias("high_price"),
        F.first("low_price").alias("low_price"),
        F.first("close_price").alias("closing_price"),
        F.first("adj_close_price").alias("adjusted_close"),
        F.sum("volume").alias("volume_total"),
    )
    .withColumn("close_ma_5", F.avg("closing_price").over(rolling_window))
    .withColumn(
        "close_delta",
        F.col("closing_price") - F.lag("closing_price").over(window_spec)
    )
    .withColumn("dt", F.date_format("trade_date", "yyyy-MM-dd"))
    .withColumn("ticker", F.col("ticker_symbol"))
)

refined_df = aggregated.select(
    "trade_date",
    "opening_price",
    "high_price",
    "low_price",
    "closing_price",
    "adjusted_close",
    "volume_total",
    "close_ma_5",
    "close_delta",
    "dt",
    "ticker"
)

refined_dynamic = DynamicFrame.fromDF(refined_df, glue_context, "refined_dynamic")

sink = glue_context.getSink(
    connection_type="s3",
    path=output_path,
    enableUpdateCatalog=True,
    updateBehavior="UPDATE_IN_DATABASE",
    partitionKeys=["dt", "ticker"],
)
sink.setFormat("glueparquet")
sink.setCatalogInfo(catalogDatabase=raw_database, catalogTableName=refined_table)
sink.writeFrame(refined_dynamic)

job.commit()
