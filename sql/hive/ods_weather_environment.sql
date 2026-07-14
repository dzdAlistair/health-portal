-- ============================================================
-- ODS 层：全国城市气象环境原始数据（外部表）
-- 数据源：weather_environment.csv
-- HDFS : /health_portal/raw/weather/
-- 行数 : 600 (50 城市 × 12 月)
-- ============================================================
CREATE DATABASE IF NOT EXISTS health_portal;
USE health_portal;

CREATE EXTERNAL TABLE IF NOT EXISTS ods_weather_environment (
    record_date   STRING  COMMENT '记录日期',
    region        STRING  COMMENT '城市名称',
    temperature   STRING  COMMENT '气温(℃)',
    humidity      STRING  COMMENT '湿度(%)',
    precipitation STRING  COMMENT '降水量(mm)',
    wind_speed    STRING  COMMENT '风速(m/s)',
    source        STRING  COMMENT '数据来源'
)
COMMENT 'ODS层 — 全国城市气象环境原始数据'
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/health_portal/raw/weather/'
TBLPROPERTIES ('skip.header.line.count'='1');

SELECT COUNT(*) AS row_count FROM ods_weather_environment;
SELECT * FROM ods_weather_environment LIMIT 5;
