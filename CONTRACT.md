# 第八组 统一项目契约

> **所有人必须遵守。** 字段名、表名、API 路径不能自行修改。
> 最后更新: 2026-07-14 | 版本: v2.0 (对照实际交付物校准)

## 项目信息
- 项目名称：基于 Hadoop 的健康大数据门户平台与资源管理系统
- GitHub 仓库：https://github.com/dzdAlistair/health-portal
- VM 目录：/home/alistair/projects/health-portal
- HDFS 根路径：/health_portal/
- Hive 数据库：health_portal
- MySQL 数据库：health_portal

## 5 个核心数据文件（文件名不可改）

| 文件 | 说明 | 行数 | 来源 |
|------|------|------|------|
| medical_institutions.csv | 全国省级医疗资源 (23列) | 310 | 国家统计局 |
| health_statistics.csv | 国民健康指标 (7列) | 1,793 | 公开统计 |
| health_industry.csv | 健康产业产品备案 (9列) | 500 | 公开数据 |
| weather_environment.csv | 城市气象环境 (7列) | 600 | 气象数据 |
| portal_contents.csv | 门户内容 (8列) | 742 | 爬虫采集 |

## 5 个分析结果 CSV（列名不可改，Flask API 依赖）

| CSV | 列名 | 生成方式 |
|-----|------|---------|
| institution_by_region.csv | `region`, `count` | data_bridge.py ← HDFS ADS |
| institution_type.csv | `name`, `value` | data_bridge.py ← DWD CSV (hospitals/primary/specialized 三列求和) |
| medical_resources.csv | `region`, `beds`, `doctors`, `nurses` | data_bridge.py ← HDFS ADS |
| content_trend.csv | `month`, `news`, `policy`, `knowledge` | data_bridge.py ← ADS pivot |
| resource_category.csv | `name`, `value` | data_bridge.py ← MySQL resource_category JOIN data_resource |

## MySQL 表名 (health_portal)

| 表名 | 说明 | 行数 |
|------|------|------|
| sys_user | 管理员用户 | 1+ |
| content_category | 内容分类 (news/policy/knowledge) | 3 |
| portal_content | 门户内容 | 745 |
| application_info | 应用中心 | 3 |
| resource_category | 资源分类 | 5 |
| data_resource | 数据资源目录 | 8 |

### 关键字段约定（已发现的冲突，修正后为准）

- **`publishing_date`** (不是 `publish_date`) — portal_content 表的发布日期字段
- **`content_type`** 取值: `news` | `policy` | `knowledge` (不含 `application`，已废弃)
- **`security_level`** 取值: `公开` | `内部` | `受限`
- **`source_type`** 取值: `公开数据下载` | `官方发布` | `API接口` | `网页采集`
- **`resource_status`** 取值: `已发布` | `草稿` | `下架`

## Hive 表名 (health_portal)

### ODS 层 (5 张外部表 → HDFS raw/)

| 表名 | 对应 CSV | DDL |
|------|---------|-----|
| ods_medical_resource | medical_institutions.csv | sql/hive/ods_medical_resource.sql |
| ods_health_statistics | health_statistics.csv | sql/hive/ods_health_statistics.sql |
| ods_health_industry | health_industry.csv | sql/hive/ods_health_industry.sql |
| ods_weather_environment | weather_environment.csv | sql/hive/ods_weather_environment.sql |
| ods_portal_contents | portal_contents.csv | sql/hive/ods_portal_contents.sql |

### DWD 层 (5 张清洗明细表)

| 表名 | DDL |
|------|-----|
| dwd_medical_resource | sql/hive/dwd_medical_resource.sql |
| dwd_health_stat | sql/hive/dwd_health_stat.sql |
| dwd_health_industry | sql/hive/dwd_health_industry.sql |
| dwd_weather_environment | sql/hive/dwd_weather_environment.sql |
| dwd_portal_contents | sql/hive/dwd_portal_contents.sql |

### ADS 层 (5 张聚合统计表)

| 表名 | 聚合维度 | 行数 | DDL |
|------|---------|------|-----|
| ads_medical_stat | province × year | 310 | sql/hive/ads_medical_stat.sql |
| ads_health_stat | year × category | 40 | sql/hive/ads_health_stat.sql |
| ads_health_industry | industry_type × category | 22 | sql/hive/ads_health_industry.sql |
| ads_weather_environment | quarter × region | 200 | sql/hive/ads_weather_environment.sql |
| ads_portal_contents | month × type × category | 231 | sql/hive/ads_portal_contents.sql |

## HDFS 路径

```
/health_portal/
├── raw/{medical,health_statistics,industry,weather,internet}/
├── clean/{medical,health_statistics,industry,weather,internet}/
└── output/{dwd_medical_resource,ads_medical_stat,...}/
```

## Flask 路由契约

### 门户页面 (portal_bp)

| 路由 | 模板 | 数据来源 |
|------|------|---------|
| GET `/` | portal/index.html | MySQL: 最新内容 + 应用列表 |
| GET `/news` | portal/news.html | JS → /api/contents?type=news |
| GET `/policy` | portal/policy.html | JS → /api/contents?type=policy |
| GET `/knowledge` | portal/knowledge.html | JS → /api/contents?type=knowledge |
| GET `/apps` | portal/apps.html | MySQL: application_info |
| GET `/resources` | portal/resources.html | MySQL: data_resource |
| GET `/dashboard` | portal/dashboard.html | JS → /api/analysis/* |

### 分析 API (analysis_bp, /api)

| 路由 | JSON 结构 |
|------|-----------|
| GET `/api/analysis/institution_by_region` | `{region: [], count: []}` |
| GET `/api/analysis/institution_type` | `[{name, value}]` |
| GET `/api/analysis/medical_resources` | `{region: [], beds: [], doctors: [], nurses: []}` |
| GET `/api/analysis/content_trend` | `{month: [], news: [], policy: [], knowledge: []}` |
| GET `/api/analysis/resource_category` | `[{name, value}]` |

### 资源 API (resource_bp, /api)

| 路由 | 说明 |
|------|------|
| GET `/api/contents?type=&page=&pageSize=` | 门户内容列表 (type=news\|policy\|knowledge) |
| GET `/api/resources?page=&pageSize=` | 公开数据资源列表 |
| GET `/api/health` | 健康检查 `{status: "ok"}` |

### 后台管理 (admin_bp, /admin)

| 路由 | 说明 |
|------|------|
| GET/POST `/admin/login` | 登录 |
| GET `/admin/` | 管理仪表盘 |
| GET/POST `/admin/content` | 内容列表 |
| GET/POST `/admin/content/add` | 新增内容 |
| GET `/admin/content/delete/<id>` | 删除内容 |
| GET/POST `/admin/resource/add` | 新增资源 |
| GET `/admin/resource/delete/<id>` | 删除资源 |
| GET/POST `/admin/apps` | 应用列表 |
| GET/POST `/admin/apps/add` | 新增应用 |
| GET `/admin/apps/delete/<id>` | 删除应用 |
| GET `/admin/users` | 用户列表 |
| GET/POST `/admin/users/add` | 新增用户 |
| GET `/admin/users/delete/<id>` | 删除用户 |

## 协作规则

1. 每人只改自己分区的文件
2. 每天: git pull → 写代码 → git add → git commit → git push
3. 公共字段变更前必须在群里说
4. 模拟数据标记 data_source=simulation
5. 不采集真实个人医疗隐私数据

## 已知差异记录 (v1.0 → v2.0)

| 项目 | v1.0 契约 | v2.0 实际 | 原因 |
|------|----------|----------|------|
| Hive 数据库 | `health_dw` | `health_portal` | 与 MySQL 保持一致 |
| ODS 表 #1 | `ods_medical_institution` | `ods_medical_resource` | 对齐文件名 |
| ODS 表 #5 | `ods_portal_content` | `ods_portal_contents` | 对齐文件名 (复数) |
| ADS 表名 | `ads_institution_by_region` 等 | `ads_medical_stat` 等 | 对齐 Spark 输出目录名 |
| 内容 API | 未定义 | `/api/contents?type=` | 实际需求新增 |
| 门户路由 | 未列出 | 7 个页面路由 | 实际需求新增 |
| 后台路由 | 未列出 | 12 个 CRUD 路由 | 实际需求新增 |
| `publish_date` | (未约定) | 统一为 `publishing_date` | 对齐 MySQL DDL |
| 应用数量 | 6 | 3 | 去重合并 |
