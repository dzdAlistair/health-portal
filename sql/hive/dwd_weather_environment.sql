-- ============================================================
-- DWD 层：全国城市气象环境清洗明细表
-- 来源  : ods_weather_environment
-- 清洗规则:
--   1. 核心字段非空过滤 (日期/城市/温度/湿度/降水/风速)
--   2. 数值列 CAST 为 DOUBLE，剔除转换失败行
--   3. 日期格式校验
--   4. 按 record_date + region 联合去重
-- 行数  : ≤ 600
-- ============================================================
CREATE DATABASE IF NOT EXISTS health_portal;
USE health_portal;

DROP TABLE IF EXISTS dwd_weather_environment;
CREATE TABLE dwd_weather_environment (
    record_date   DATE    COMMENT '记录日期',
    region        STRING  COMMENT '城市名称',
    temperature   DOUBLE  COMMENT '气温(℃)',
    humidity      DOUBLE  COMMENT '湿度(%)',
    precipitation DOUBLE  COMMENT '降水量(mm)',
    wind_speed    DOUBLE  COMMENT '风速(m/s)',
    source        STRING  COMMENT '数据来源'
)
COMMENT 'DWD层 — 全国城市气象环境清洗明细'
STORED AS TEXTFILE;

INSERT OVERWRITE TABLE dwd_weather_environment
SELECT DISTINCT
    try_cast(record_date AS DATE) AS record_date,
    region,
    try_cast(temperature AS DOUBLE) AS temperature,
    try_cast(humidity AS DOUBLE) AS humidity,
    try_cast(precipitation AS DOUBLE) AS precipitation,
    try_cast(wind_speed AS DOUBLE) AS wind_speed,
    source
FROM ods_weather_environment
WHERE record_date IS NOT NULL
  AND region IS NOT NULL
  AND temperature IS NOT NULL
  AND humidity IS NOT NULL
  AND precipitation IS NOT NULL
  AND wind_speed IS NOT NULL
  AND try_cast(temperature AS DOUBLE) IS NOT NULL
  AND try_cast(humidity AS DOUBLE) IS NOT NULL
  AND try_cast(precipitation AS DOUBLE) IS NOT NULL
  AND try_cast(wind_speed AS DOUBLE) IS NOT NULL
  AND try_cast(record_date AS DATE) IS NOT NULL;

SELECT COUNT(*) AS dwd_row_count FROM dwd_weather_environment;
SELECT * FROM dwd_weather_environment LIMIT 5;
