# 前置依赖导入（首次运行执行一次即可）
from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder \
    .appName("medical_resources") \
    .getOrCreate()

# ========== ODS层：读取原始数据 ==========
csv_path = "hdfs://de2:9000/health_portal/clean/medical/medical_institutions.csv"
odsDF = spark.read \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .csv(csv_path)

print("===== ODS原始字段结构 =====")
odsDF.printSchema()

ods_count = odsDF.count()
print(f"\n原始CSV总记录：{ods_count} 条")

print("\n===== 原始数据抽样5行 =====")
odsDF.show(5)

# ========== DWD层：清洗校验 ==========
# 清洗规则：剔除全空无效行、过滤异常年份
dwdDF = odsDF.filter(
    ~(F.col("record_id").isNull() & F.col("year").isNull() & F.col("province").isNull())
).filter((F.col("year") >= 2014) & (F.col("year") <= 2023))

# 打印清洗前后数据量对比
dwd_count = dwdDF.count()
print(f"清洗前原始数据：{ods_count} 条")
print(f"清洗后有效明细数据：{dwd_count} 条")

# 预览清洗后数据
print("\n===== DWD清洗后数据抽样5行 =====")
dwdDF.show(5)

# 将清洗后的明细落地到规范HDFS output目录
dwdDF.write \
    .mode("overwrite") \
    .option("header", "true") \
    .csv("hdfs://de2:9000/health_portal/output/dwd_medical_resource")
print("\n✅ DWD清洗明细文件落地完成：/health_portal/output/dwd_medical_resource")

# ========== ADS层：省份年度聚合 ==========
# 按省份+年份分组，聚合大屏需要的医疗核心指标
adsDF = dwdDF.groupBy("province", "year") \
    .agg(
        F.sum("medical_health_institutions").alias("total_institutions"),
        F.sum("medical_health_beds").alias("total_beds"),
        F.sum("licensed_assistant_physicians").alias("total_doctors"),
        F.sum("registered_nurses").alias("total_nurses")
    )

# 打印统计结果样例
print("===== ADS 省份年度聚合指标抽样10行 =====")
adsDF.show(10)

# 聚合指标落地HDFS，后端读取给前端ECharts可视化使用
adsDF.write \
    .mode("overwrite") \
    .option("header", "true") \
    .csv("hdfs://de2:9000/health_portal/output/ads_medical_stat")
print("\n✅ ADS大屏统计指标文件落地完成：/health_portal/output/ads_medical_stat")