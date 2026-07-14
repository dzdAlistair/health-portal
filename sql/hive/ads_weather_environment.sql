-- ============================================================
-- ADS 层：全国城市季度气象聚合统计表
-- 来源  : dwd_weather_environment
-- 聚合  : GROUP BY record_quarter, region
-- 指标  : avg/min/max temperature, avg humidity,
--         total precipitation, avg wind_speed, record_days
-- 行数  : 200 (50 城市 × 4 季度, 原始 600 行压缩至 200)
-- ============================================================
CREATE DATABASE IF NOT EXISTS health_portal;
USE health_portal;

DROP TABLE IF EXISTS ads_weather_environment;
CREATE TABLE ads_weather_environment (
    record_quarter      STRING COMMENT '记录季度 (yyyy-Qn)',
    region              STRING COMMENT '城市名称',
    avg_temperature     DOUBLE COMMENT '季度平均气温',
    min_temperature     DOUBLE COMMENT '季度最低气温',
    max_temperature     DOUBLE COMMENT '季度最高气温',
    avg_humidity        DOUBLE COMMENT '季度平均湿度',
    total_precipitation DOUBLE COMMENT '季度累计降水量',
    avg_wind_speed      DOUBLE COMMENT '季度平均风速',
    record_days         BIGINT COMMENT '季度有效记录天数'
)
COMMENT 'ADS层 — 全国城市季度气象汇总'
STORED AS TEXTFILE;

INSERT OVERWRITE TABLE ads_weather_environment
SELECT
    CONCAT(YEAR(record_date), '-Q', QUARTER(record_date)) AS record_quarter,
    region,
    AVG(temperature)   AS avg_temperature,
    MIN(temperature)   AS min_temperature,
    MAX(temperature)   AS max_temperature,
    AVG(humidity)      AS avg_humidity,
    SUM(precipitation) AS total_precipitation,
    AVG(wind_speed)    AS avg_wind_speed,
    COUNT(*)           AS record_days
FROM dwd_weather_environment
GROUP BY CONCAT(YEAR(record_date), '-Q', QUARTER(record_date)), region
ORDER BY record_quarter, region;

-- 核验: ADS 200 行 < DWD 600 行
SELECT COUNT(*) AS ads_row_count FROM ads_weather_environment;
SELECT * FROM ads_weather_environment LIMIT 10;
