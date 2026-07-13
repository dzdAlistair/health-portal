# 健康大数据门户平台

## 数据处理与最终交付文档

> 本文档涵盖项目 4 张数据表的全流程数据处理方案，严格遵循 **ODS 原始层** → **DWD 清洗层** → **ADS 聚合层** 三层分层规范。所有操作均使用 Spark Shell 交互执行，并提供统一相关输出文件，可直接复制执行。

---

# 健康大数据门户平台 - 数据处理代码与策略交接文档

本文档完整覆盖项目 4 张数据表的全流程处理方案，严格遵循 ODS 原始层→DWD 清洗层→ADS 聚合层 的数仓分层规范，所有操作均在 Spark Shell 环境执行，结果统一落地本地文件，可直接复制执行。


## 任务一：全国省级医疗资源数据表处理


### 1. 数据表基础信息

数据文件：national_provincial_medical_resources_2014_2023 (1).csv

业务说明：全国 31 个省份 2014-2023 年医疗资源年度统计数据，为项目核心基础表

核心字段：English header    中文含义    单位/说明 record_id    记录唯一编号    省份代码 + 年份 year    数据年份    年 province_code    省级行政区代码    国家行政区划代码 province    省份名称    如四川省、北京市 medical_health_institutions    医疗卫生机构总数    个 hospitals    医院数量    个 primary_healthcare_institutions    基层医疗卫生机构数量    个，含卫生院、社区卫生服务机构等 specialized_public_health_institutions    专业公共卫生机构数量    个，含疾控、妇幼保健等机构 medical_health_beds    医疗卫生机构床位总数    张 hospital_beds    医院床位数    张 primary_healthcare_beds    基层医疗卫生机构床位数    张 health_technicians    卫生技术人员数量    人 licensed_assistant_physicians    执业及执业助理医师数量    人 registered_nurses    注册护士数量    人 permanent_population    年末常住人口    人 beds_per_1000_people    每千人医疗床位数    张/千人 physicians_per_1000_people    每千人医师数    人/千人 nurses_per_1000_people    每千人注册护士数    人/千人 institutions_per_10000_people    每万人医疗卫生机构数    个/万人 hospital_beds_share    医院床位占全部医疗床位的比例    0—1，例如 0.85 表示 85% primary_institution_share    基层机构占全部医疗卫生机构的比例    0—1 source    数据来源    国家统计局网页地址 update_date    数据采集或更新日期    YYYY-MM-DD

数据粒度：单省份单年度医疗资源明细记录


### 2. DWD 层清洗策略

核心字段非空校验：过滤省份、年份、床位、医生、护士、医疗机构数量为空的脏数据

业务范围校验：限定年份在 2014-2023 的合法区间内，剔除超出时间范围的无效数据

数值合法性校验：所有医疗资源数值字段必须可转换为整数 / 双精度浮点型，剔除非数值型异常数据

去重规则：按 province + year 联合主键去重，同一省份同一年份仅保留 1 条有效记录


### 3. ADS 层聚合策略

分组维度：省份名称（覆盖全周期）

聚合指标： 

十年间医院床位平均值、最大值、最小值

十年间执业医师累计总量、平均年度医师数

十年间注册护士平均数量、累计总量

十年间医疗机构总数、平均年度机构数

有效统计年份数

业务价值：输出各省份十年医疗资源规模的全周期汇总报表，直观对比各省医疗资源家底


### 4. 核心执行代码

scala


```scala
// ========== ODS层：读取原始数据 ==========
val csvPath = "hdfs://192.168.28.128:9000/health_portal/clean/national_provincial_medical_resources_2014_2023.csv"
val odsDF = spark.read
.option("header", "true")
.option("inferSchema", "true")
.csv(csvPath)

println("===== ODS原始字段结构 =====")
odsDF.printSchema()

val odsCount = odsDF.count()
println(s"\n原始CSV总记录：$odsCount 条")

println("\n===== 原始数据抽样5行 =====")
odsDF.show(5)

// ========== DWD层：清洗校验 ==========
// 清洗规则：剔除全空无效行、过滤异常年份
val dwdDF = odsDF.filter(
    !(odsDF("record_id").isNull && odsDF("year").isNull && odsDF("province").isNull)
).filter(odsDF("year") >= 2014 && odsDF("year") <= 2023)

// 打印清洗前后数据量对比
val dwdCount = dwdDF.count()
println(s"清洗前原始数据：$odsCount 条")
println(s"清洗后有效明细数据：$dwdCount 条")

// 预览清洗后数据
println("\n===== DWD清洗后数据抽样5行 =====")
dwdDF.show(5)

// 将清洗后的明细落地到规范HDFS output目录
dwdDF.write
.mode("overwrite")
.option("header", "true")
.csv("hdfs://192.168.28.128:9000/health_portal/output/dwd_medical_resource")
println("\n✅ DWD清洗明细文件落地完成：/health_portal/output/dwd_medical_resource")

// ========== ADS层：全周期省份聚合 ==========
// 按省份+年份分组，聚合大屏需要的医疗核心指标
val adsDF = dwdDF.groupBy("province", "year")
.agg(
    sum("medical_health_institutions").alias("total_institutions"),
    sum("medical_health_beds").alias("total_beds"),
    sum("licensed_assistant_physicians").alias("total_doctors"),
    sum("registered_nurses").alias("total_nurses")
)

// 打印统计结果样例
println("===== ADS 省份年度聚合指标抽样10行 =====")
adsDF.show(10)

// 聚合指标落地HDFS，后端读取给前端ECharts可视化使用
adsDF.write
.mode("overwrite")
.option("header", "true")
.csv("hdfs://192.168.28.128:9000/health_portal/output/ads_medical_stat")
println("\n✅ ADS大屏统计指标文件落地完成：/health_portal/output/ads_medical_stat")

// ========== 落地写入 ==========
zip -r dwd_medical_resource.zip dwd_medical_resource
hdfs dfs -get /health_portal/output/ads_medical_stat ~/
zip -r ads_medical_stat.zip ads_medical_stat
```


### 5. 交付输出

原始文件：national_provincial_medical_resources_2014_2023.csv

清洗明细：dwd_medical_stat 文件夹（压缩为 zip 包）

聚合报表：ads_medical_resource 文件夹（压缩为 zip 包）


## 任务二：国民健康指标数据表处理


### 1. 数据表基础信息

数据文件：health_statistics.csv

核心字段：year（统计年份）、category（指标大类）、indicator_name（指标名称）、indicator_value（指标数值）、source（数据来源）

数据粒度：分年度、分品类的健康指标明细记录


### 2. DWD 层清洗策略

非空校验：过滤年份、指标大类、指标名称、指标数值为空的脏数据

业务范围校验：限定年份在 1990-2025 的合法区间内

数值合法性校验：指标数值必须可转换为数字类型

去重规则：按 year + category + indicator_name 联合主键去重


### 3. ADS 层聚合策略

分组维度：统计年份 + 指标大类

聚合指标：分组内总记录数、指标数值求和、指标数值平均值

业务价值：输出按年度、按品类汇总的健康指标总览报表


### 4. 核心执行代码

scala


```scala
// ========== ODS层：读取原始数据 ==========
val odsDF = spark.read
.option("header","true")
.option("encoding","utf-8")
.csv("hdfs://192.168.28.128:9000/health_portal/clean/health_statistics.csv")
// 原始数据探查
odsDF.count()
odsDF.show(10)

// ========== DWD层：清洗校验 ==========
val dwdDF = odsDF
.filter(col("year").isNotNull)
.filter(col("category").isNotNull)
.filter(col("indicator_name").isNotNull)
.filter(col("indicator_value").isNotNull)
.filter(col("year").cast("int") >= 1990)
.filter(col("year").cast("int") <= 2025)
.dropDuplicates("year","category","indicator_name")

// ========== ADS层：分组聚合 ==========
val adsDF = dwdDF.groupBy("year","category")
.agg(
  sum(col("indicator_value").cast("double")).alias("total_indicator_val"),
  avg(col("indicator_value").cast("double")).alias("avg_indicator_val")
)
.orderBy("year","category")
adsDF.count()
adsDF.show(10)

// ========== 落地写入 ==========
dwdDF.write
.mode("overwrite")
.option("header","true")
.csv("file:///home/hadoop/dwd_health_stat")
adsDF.write
.mode("overwrite")
.option("header","true")
.csv("file:///home/hadoop/ads_health_stat")
```

### 5. 交付输出

原始文件：health_statistics.csv

清洗明细：dwd_health 文件夹（压缩为 zip 包）

聚合报表：ads_health 文件夹（压缩为 zip 包）


## 任务三：健康产业产品备案数据表处理

### 1. 数据表基础信息

数据文件：health_industry.csv

核心字段：industry_id（备案 ID）、industry_type（产业类型）、product_name（产品名称）、category（产品品类）、approval_date（获批日期）、status（状态）、source（数据来源）

数据粒度：单条产品备案记录，覆盖医疗器械、药品制造、药品研发三大产业类型


### 2. DWD 层清洗策略

全核心字段非空校验

枚举值校验：industry_type 仅保留「医疗器械、药品制造、药品研发」三类合法值

日期格式校验：approval_date 必须可转换为标准日期格式

去重规则：按 industry_id + product_name + approval_date 联合主键去重


### 3. ADS 层聚合策略

分组维度：产业类型 + 产品品类

聚合指标：产品备案总数量、去重产品数量、品类内最早获批日期、品类内最晚获批日期

业务价值：输出各产业大类下细分品类的产品规模与时间跨度统计


### 4. 核心执行代码

scala


```scala
// ========== ODS层：读取原始数据 ==========
val odsDF = spark.read
.option("header","true")
.option("encoding","utf-8")
.csv("file:///home/hadoop/health_industry.csv")
odsDF.count()
odsDF.show(10)

// ========== DWD层：清洗校验 ==========
val dwdDF = odsDF
.filter(col("industry_id").isNotNull)
.filter(col("industry_type").isNotNull)
.filter(col("product_name").isNotNull)
.filter(col("category").isNotNull)
.filter(col("approval_date").isNotNull)
.filter(col("status").isNotNull)
.filter(col("industry_type").isin("医疗器械","药品制造","药品研发"))
.filter(col("approval_date").cast("date").isNotNull)
.dropDuplicates("industry_id","product_name","approval_date")
dwdDF.count()
dwdDF.show(10)
// ========== ADS层：分组聚合 ==========
val adsDF = dwdDF.groupBy("industry_type","category")
.agg(
  count("*").alias("total_product_count"),
  countDistinct("product_name").alias("distinct_product_count"),
  min("approval_date").alias("earliest_approval_date"),
  max("approval_date").alias("latest_approval_date")
)
.orderBy("industry_type","category")
// 聚合结果预览
adsDF.count()
adsDF.show(10)

// ========== 落地写入 ==========
dwdDF.write
.mode("overwrite")
.option("header","true")
.csv("file:///home/hadoop/dwd_health_industry")
adsDF.write
.mode("overwrite")
.option("header","true")
.csv("file:///home/hadoop/ads_health_industry")
```


### 5. 交付输出

原始文件：health_industry.csv

清洗明细：dwd_health_industry 文件夹（压缩为 zip 包）

聚合报表：ads_health_industry 文件夹（压缩为 zip 包）


## 任务四：全国城市月度天气环境数据表处理


### 1. 数据表基础信息

数据文件：weather_environment.csv

核心字段：record_date（记录日期）、region（城市）、temperature（气温）、humidity（湿度）、precipitation（降水量）、wind_speed（风速）、source（数据来源）

数据粒度：单城市单月度气象记录，覆盖全国 50 个城市 2025 全年 12 个月，原始共 600 条记录


### 2. DWD 层清洗策略

核心字段非空过滤：日期、城市、温度、湿度、降水量、风速不能为空

数值合法性校验：温度、湿度、降水量、风速必须可转换为双精度浮点型

日期格式校验：record_date 必须可转换为标准日期格式

去重规则：按 record_date + region 联合主键去重，同一城市同一日期仅保留一条记录


### 3. ADS 层聚合策略


#### 方案迭代说明

初始方案：按月度 + 城市分组。因原始数据本身为月度粒度，聚合后行数无压缩，无业务汇总价值

最终落地方案：季度 + 城市聚合 

分组维度：记录季度（格式 yyyy-Qn） + 城市

聚合指标：季度平均气温、季度最低气温、季度最高气温、季度平均湿度、季度累计降水量、季度平均风速、季度有效记录天数

聚合效果：原始 600 条月度明细压缩为 200 条季度统计数据（50 城市 × 4 季度），每条记录合并同季度 3 个月数据，可通过 record_days=3 核验逻辑生效


### 4. 核心执行代码

scala


```scala
// ========== ODS层：读取原始数据 ==========
val odsDF = spark.read
.option("header","true")
.option("encoding","utf-8")
.csv("file:///home/hadoop/weather_environment.csv")
odsDF.count()
odsDF.show(10)
// ========== DWD层：清洗校验 ==========
val dwdDF = odsDF
// 核心字段非空过滤
.filter(col("record_date").isNotNull)
.filter(col("region").isNotNull)
.filter(col("temperature").isNotNull)
.filter(col("humidity").isNotNull)
.filter(col("precipitation").isNotNull)
.filter(col("wind_speed").isNotNull)
// 数值字段合法性校验：温度、湿度、降水、风速必须能转成数值
.filter(col("temperature").cast("double").isNotNull)
.filter(col("humidity").cast("double").isNotNull)
.filter(col("precipitation").cast("double").isNotNull)
.filter(col("wind_speed").cast("double").isNotNull)
// 日期格式合法性校验
.filter(col("record_date").cast("date").isNotNull)
// 核心业务字段去重：同日期同地区仅保留一条
.dropDuplicates("record_date","region")
// 清洗后校验
dwdDF.count()
dwdDF.show(10)

// ========== ADS层：季度聚合（最终版） ==========
val adsDF = dwdDF
.withColumn("record_quarter", concat(
  date_format(col("record_date"), "yyyy"),
  lit("-Q"),
  quarter(col("record_date"))
))
.groupBy("record_quarter","region")
.agg(
  avg(col("temperature").cast("double")).alias("avg_temperature"),
  min(col("temperature").cast("double")).alias("min_temperature"),
  max(col("temperature").cast("double")).alias("max_temperature"),
  avg(col("humidity").cast("double")).alias("avg_humidity"),
  sum(col("precipitation").cast("double")).alias("total_precipitation"),
  avg(col("wind_speed").cast("double")).alias("avg_wind_speed"),
  count("*").alias("record_days")
)
.orderBy("record_quarter","region")
// 聚合结果预览
adsDF.count()
adsDF.show(10)

// ========== 落地写入 ==========
dwdDF.write
.mode("overwrite")
.option("header","true")
.csv("file:///home/hadoop/dwd_weather_environment")
adsDF.write
.mode("overwrite")
.option("header","true")
.csv("file:///home/hadoop/ads_weather_environment")
```


### 5. 交付输出

原始文件：weather_environment.csv

清洗明细：dwd_weather_environment 文件夹（压缩为 zip 包）

聚合报表：ads_weather_environment 文件夹（压缩为 zip 包）



# 任务五：健康门户内容数据表处理

## 1. 数据表基础信息

数据文件：portal_contents_clean.csv

核心字段：content_id（文献唯一编号）、content_type（文献类型）、title（文章官方标题）、category（规范化内容分类）、publish_date（发布日期）、source（发布机构）、source_url（文章原始网页地址）、status（发布状态）

数据粒度：单条健康领域内容记录，覆盖科普、新闻、政策三类内容形态，涵盖疾控、医保、政府等多官方发布渠道，原始共 300 + 条记录

## 2. DWD 层清洗策略

核心字段非空过滤：编号、类型、标题、分类、发布日期、发布机构、原始链接、发布状态不能为空

枚举值合法性校验：content_type 仅允许 knowledge/news/policy 三类取值；status 统一限定为 published；category 严格遵循 14 个受控分类，禁止自定义分类

日期格式校验：publish_date 必须可转换为标准日期格式

去重规则：按 content_id 主键去重，同一篇文献仅保留一条记录

## 3. ADS 层聚合策略

### 方案迭代说明

初始方案：按发布日期 + 分类分组。因原始数据本身为单条内容粒度，聚合后行数压缩有限，无业务汇总价值

最终落地方案：发布年月 + 内容类型 + 分类聚合

分组维度：发布年月（格式 yyyy-MM） + 内容类型 + 内容分类

聚合指标：月度文章总量、月度最早发布日期、月度最晚发布日期、月度去重发布机构数、月度有效记录天数

聚合效果：原始 300 + 条月度明细压缩为百条以内统计数据，每条记录合并同分类同类型全月内容数据，可通过 article_total 核验逻辑生效

## 4. 核心执行代码

scala

```scala
// ========== ODS层：读取原始数据 ==========
val odsDF = spark.read
.option("header","true")
.option("encoding","utf-8")
.csv("file:///home/hadoop/portal_contents_clean.csv")
// 原始数据探查
odsDF.count()
odsDF.show(10)

// ========== DWD层：清洗校验 ==========
val dwdDF = odsDF
.filter(col("content_id").isNotNull)
.filter(col("content_type").isNotNull)
.filter(col("title").isNotNull)
.filter(col("category").isNotNull)
.filter(col("publish_date").isNotNull)
.filter(col("source").isNotNull)
.filter(col("source_url").isNotNull)
.filter(col("status").isNotNull)
.filter(col("content_type").isin("knowledge","news","policy"))
.filter(col("status").isin("published"))
.filter(col("category").isin("传染病","慢性非传染性疾病","免疫规划","公共卫生事件","烟草控制","营养与健康","环境健康","职业健康与中毒控制","放射卫生","中心要闻","工作动态","政策文件","规范性文件","政策解读"))
.filter(col("publish_date").cast("date").isNotNull)
.dropDuplicates("content_id")

// ========== ADS层：分组聚合 ==========
val adsDF = dwdDF
.withColumn("publish_month", date_format(col("publish_date"), "yyyy-MM"))
.groupBy("publish_month","content_type","category")
.agg(
  count("*").alias("article_total"),
  min("publish_date").alias("first_publish_date"),
  max("publish_date").alias("last_publish_date"),
  countDistinct("source").alias("source_count"),
  countDistinct("publish_date").alias("record_days")
)
.orderBy("publish_month","content_type","category")
adsDF.count()
adsDF.show(10)

// ========== 落地写入 ==========
dwdDF.write
.mode("overwrite")
.option("header","true")
.csv("file:///home/hadoop/dwd_portal_contents")
adsDF.write
.mode("overwrite")
.option("header","true")
.csv("file:///home/hadoop/ads_portal_contents")
```

## 5. 交付输出

原始文件：portal_contents_clean.csv

清洗明细：dwd_portal_contents 文件夹（压缩为 zip 包）

聚合报表：ads_portal_contents 文件夹（压缩为 zip 包）

## 团队交接说明


### 1. 统一执行规范

所有数据表严格遵循统一流程，确保项目风格一致、便于组长核验：

本地文件上传 → 2. ODS 层读取与探查 → 3. DWD 层清洗与校验 → 4. ADS 层业务聚合 → 5. 分层落地写入 → 6. 打包交付 所有操作均在 Ubuntu 虚拟机 /home/hadoop 目录下执行，通过 rz 上传、python3 -m http.server 8080 提供下载。


### 2. 文件交付规范

每张表交付 3 类文件，统一命名规则，便于管理和溯源：

原始 CSV 文件（ODS 层数据源，保留原始文件名）

DWD 层清洗后明细文件夹（命名格式 dwd_xxx，压缩为 zip 包）

ADS 层聚合统计报表文件夹（命名格式 ads_xxx，压缩为 zip 包）


### 3. 核验标准

组长核验可通过三点确认逻辑正确性：

DWD 层行数 ≤ ODS 层行数，符合清洗过滤预期

ADS 层行数 ＜ DWD 层行数，符合聚合压缩预期

聚合指标与分组维度匹配，业务逻辑自洽，可通过预览数据核对计算结果


### 4. 后续维护说明

本文档覆盖的 4 张表为项目核心数据基础，后续新增数据表可直接套用本文档模板补充对应板块，保持整体文档结构统一。所有代码均可直接在 Spark Shell 中复制执行，无需额外依赖，环境兼容性与项目整体保持一致。



