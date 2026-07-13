# 导入依赖函数（执行代码前先运行这一行）
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, countDistinct, date_format

spark = SparkSession.builder \
    .appName("portal_contents") \
    .getOrCreate()

# ========== ODS层：读取原始数据 ==========
odsDF = spark.read \
    .option("header", "true") \
    .option("encoding", "utf-8") \
    .csv("file:///home/alistair/projects/health-portal/data/clean/portal_contents.csv")

# 原始数据探查
print("原始数据总行数:", odsDF.count())
odsDF.show(10)

# ========== DWD层：清洗校验 ==========
dwdDF = odsDF \
    .filter(col("content_id").isNotNull()) \
    .filter(col("content_type").isNotNull()) \
    .filter(col("title").isNotNull()) \
    .filter(col("category").isNotNull()) \
    .filter(col("publish_date").isNotNull()) \
    .filter(col("source").isNotNull()) \
    .filter(col("source_url").isNotNull()) \
    .filter(col("status").isNotNull()) \
    .filter(col("content_type").isin("knowledge", "news", "policy")) \
    .filter(col("status").isin("published")) \
    .filter(col("category").isin(
        "传染病", "慢性非传染性疾病", "免疫规划", "公共卫生事件",
        "烟草控制", "营养与健康", "环境健康", "职业健康与中毒控制",
        "放射卫生", "中心要闻", "工作动态", "政策文件",
        "规范性文件", "政策解读"
    )) \
    .filter(col("publish_date").cast("date").isNotNull()) \
    .dropDuplicates(["content_id"])

# 清洗后校验
print("清洗后数据行数:", dwdDF.count())
dwdDF.show(10)

# ========== ADS层：分组聚合 ==========
adsDF = dwdDF \
    .withColumn("publish_month", date_format(col("publish_date"), "yyyy-MM")) \
    .groupBy("publish_month", "content_type", "category") \
    .agg(
        count("*").alias("article_total"),
        countDistinct("source").alias("source_count")
    ) \
    .orderBy("publish_month", "content_type", "category")

# 聚合结果预览
print("聚合后数据行数:", adsDF.count())
adsDF.show(10)

# ========== 落地写入 ==========
dwdDF.write \
    .mode("overwrite") \
    .option("header", "true") \
    .csv("file:///home/alistair/projects/health-portal/data/analysis/5.5门户内容数据/dwd_portal_contents")

adsDF.write \
    .mode("overwrite") \
    .option("header", "true") \
    .csv("file:///home/alistair/projects/health-portal/data/analysis/5.5门户内容数据/ads_portal_contents")