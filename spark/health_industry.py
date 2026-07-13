# PySpark 前置依赖导入，首次运行执行一次即可
from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder \
    .appName("health_industry") \
    .getOrCreate()

# ========== ODS层：读取原始数据 ==========
odsDF = spark.read \
    .option("header", "true") \
    .option("encoding", "utf-8") \
    .csv("file:///home/alistair/projects/health-portal/data/clean/health_industry.csv")

print("原始数据总行数：", odsDF.count())
odsDF.show(10)

# ========== DWD层：清洗校验 ==========
dwdDF = odsDF \
    .filter(F.col("industry_id").isNotNull()) \
    .filter(F.col("industry_type").isNotNull()) \
    .filter(F.col("product_name").isNotNull()) \
    .filter(F.col("category").isNotNull()) \
    .filter(F.col("approval_date").isNotNull()) \
    .filter(F.col("status").isNotNull()) \
    .filter(F.col("industry_type").isin("医疗器械", "药品制造", "药品研发")) \
    .filter(F.col("approval_date").cast("date").isNotNull()) \
    .dropDuplicates(["industry_id", "product_name", "approval_date"])

print("清洗后有效数据行数：", dwdDF.count())
dwdDF.show(10)

# ========== ADS层：分组聚合 ==========
adsDF = dwdDF.groupBy("industry_type", "category") \
    .agg(
        F.count("*").alias("total_product_count"),
        F.countDistinct("product_name").alias("distinct_product_count"),
        F.min("approval_date").alias("earliest_approval_date"),
        F.max("approval_date").alias("latest_approval_date")
    ) \
    .orderBy("industry_type", "category")

# 聚合结果预览
print("聚合后数据总行数：", adsDF.count())
adsDF.show(10)

# ========== 分层落地写入本地文件 ==========
dwdDF.write \
    .mode("overwrite") \
    .option("header", "true") \
    .csv("file:///home/alistair/projects/health-portal/data/analysis/5.3健康产业数据/dwd_health_industry")

adsDF.write \
    .mode("overwrite") \
    .option("header", "true") \
    .csv("file:///home/alistair/projects/health-portal/data/analysis/5.3健康产业数据/ads_health_industry")