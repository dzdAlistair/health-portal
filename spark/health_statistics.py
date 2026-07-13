# PySpark 前置导入，运行前执行一次
from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder \
    .appName("health_statistics") \
    .getOrCreate()

# ========== ODS层：读取原始数据 ==========
odsDF = spark.read \
    .option("header", "true") \
    .option("encoding", "utf-8") \
    .csv("hdfs://de2:9000/health_portal/clean/health_statistics/health_statistics.csv")

# 原始数据探查
print("原始数据总行数：", odsDF.count())
odsDF.show(10)

# ========== DWD层：清洗校验 ==========
dwdDF = odsDF \
    .filter(F.col("year").isNotNull()) \
    .filter(F.col("category").isNotNull()) \
    .filter(F.col("indicator_name").isNotNull()) \
    .filter(F.col("indicator_value").isNotNull()) \
    .filter(F.col("year").cast("int") >= 1990) \
    .filter(F.col("year").cast("int") <= 2025) \
    .dropDuplicates(["year", "category", "indicator_name"])

# ========== ADS层：分组聚合 ==========
adsDF = dwdDF.groupBy("year", "category") \
    .agg(
        F.sum(F.col("indicator_value").cast("double")).alias("total_indicator_val"),
        F.avg(F.col("indicator_value").cast("double")).alias("avg_indicator_val")
    ) \
    .orderBy("year", "category")

print("聚合后数据总行数：", adsDF.count())
adsDF.show(10)

# ========== 分层落地写入本地文件 ==========
dwdDF.write \
    .mode("overwrite") \
    .option("header", "true") \
    .csv("file:///home/alistair/projects/health-portal/data/analysis/dwd_health_stat")

adsDF.write \
    .mode("overwrite") \
    .option("header", "true") \
    .csv("file:///home/alistair/projects/health-portal/data/analysis/ads_health_stat")