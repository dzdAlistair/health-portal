# 第八组 统一项目契约

> **所有人必须遵守。** 字段名、表名、API 路径不能自行修改。

## 项目信息
- 项目名称：基于 Hadoop 的健康大数据门户平台与资源管理系统
- GitHub 仓库：https://github.com/dzdAlistair/health-portal
- VM 目录：/home/alistair/projects/health-portal
- HDFS 根路径：/health_portal/
- Hive 数据库：health_dw
- MySQL 数据库：health_portal

## 5 个核心数据文件（文件名不可改）
medical_institutions.csv  | 医疗机构数据
health_statistics.csv     | 健康统计数据
health_industry.csv       | 健康产业数据
weather_environment.csv   | 气象环境数据
portal_contents.csv       | 门户内容数据

## 5 个分析结果 CSV
institution_by_region.csv | region, count
institution_type.csv      | name, value
medical_resources.csv     | region, beds, doctors, nurses
content_trend.csv         | month, news, policy, knowledge
resource_category.csv     | name, value

## MySQL 表名 (health_portal)
sys_user, portal_content, content_category, application_info, resource_category, data_resource

## Hive 表名 (health_dw)
ODS: ods_medical_institution, ods_health_statistics, ods_health_industry, ods_weather_environment, ods_portal_content
DWD: dwd_medical_institution, dwd_health_statistics, dwd_health_industry, dwd_weather_environment, dwd_portal_content
ADS: ads_institution_by_region, ads_institution_type, ads_medical_resources, ads_content_trend, ads_resource_category

## HDFS 路径
/health_portal/raw/{medical,health_statistics,industry,weather,internet}/
/health_portal/clean/{medical,health_statistics,industry,weather,internet}/
/health_portal/output/{institution_by_region,institution_type,medical_resources,content_trend,resource_category}/

## Flask API 契约
GET /api/analysis/institution_by_region  → {region: [], count: []}
GET /api/analysis/institution_type       → [{name, value}, ...]
GET /api/analysis/medical_resources     → {region: [], beds: [], doctors: [], nurses: []}
GET /api/analysis/content_trend         → {month: [], news: [], policy: [], knowledge: []}
GET /api/analysis/resource_category      → [{name, value}, ...]
GET /api/resources                       → 公开资源列表
GET /api/health                          → {status: "ok"}

## 协作规则
1. 每人只改自己分区的文件
2. 每天: git pull → 写代码 → git add → git commit → git push
3. 公共字段变更前必须在群里说
4. 模拟数据标记 data_source=simulation
5. 不采集真实个人医疗隐私数据
