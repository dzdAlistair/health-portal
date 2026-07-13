# PySpark 前置依赖导入，首次运行执行一次即可
from pyspark.sql import functions as F

# ========== ODS层：读取原始数据 ==========
odsDF = spark.read \
    .option("header", "true") \
    .option("encoding", "utf-8") \
    .csv("file:///home/hadoop/weather_environment.csv")

print("原始数据总行数：", odsDF.count())
odsDF.show(10)

# ========== DWD层：清洗校验 ==========
dwdDF = odsDF \
    .filter(F.col("record_date").isNotNull()) \
    .filter(F.col("region").isNotNull()) \
    .filter(F.col("temperature").isNotNull()) \
    .filter(F.col("humidity").isNotNull()) \
    .filter(F.col("precipitation").isNotNull()) \
    .filter(F.col("wind_speed").isNotNull()) \
    .filter(F.col("temperature").cast("double").isNotNull()) \
    .filter(F.col("humidity").cast("double").isNotNull()) \
    .filter(F.col("precipitation").cast("double").isNotNull()) \
    .filter(F.col("wind_speed").cast("double").isNotNull()) \
    .filter(F.col("record_date").cast("date").isNotNull()) \
    .dropDuplicates(["record_date", "region"])

# 清洗后校验
print("清洗后有效数据行数：", dwdDF.count())
dwdDF.show(10)

# ========== ADS层：季度聚合（最终版） ==========
adsDF = dwdDF \
    .withColumn("record_quarter", F.concat(
        F.date_format(F.col("record_date"), "yyyy"),
        F.lit("-Q"),
        F.quarter(F.col("record_date"))
    )) \
    .groupBy("record_quarter", "region") \
    .agg(
        F.avg(F.col("temperature").cast("double")).alias("avg_temperature"),
        F.min(F.col("temperature").cast("double")).alias("min_temperature"),
        F.max(F.col("temperature").cast("double")).alias("max_temperature"),
        F.avg(F.col("humidity").cast("double")).alias("avg_humidity"),
        F.sum(F.col("precipitation").cast("double")).alias("total_precipitation"),
        F.avg(F.col("wind_speed").cast("double")).alias("avg_wind_speed"),
        F.count("*").alias("record_days")
    ) \
    .orderBy("record_quarter", "region")

# 聚合结果预览
print("聚合后数据总行数：", adsDF.count())
adsDF.show(10)

# ========== 分层落地写入本地文件 ==========
dwdDF.write \
    .mode("overwrite") \
    .option("header", "true") \
    .csv("file:///home/hadoop/dwd_weather_environment")

adsDF.write \
    .mode("overwrite") \
    .option("header", "true") \
    .csv("file:///home/hadoop/ads_weather_environment")