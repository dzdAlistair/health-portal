-- 补充种子数据：数据资源 + 应用中心
-- 运行方式: sudo mysql < scripts/seed_extra_data.sql
USE health_portal;

TRUNCATE TABLE data_resource;
INSERT INTO data_resource (resource_name, resource_type, category_id, source_type, file_format, record_count, security_level, resource_status, description) VALUES
('全国医疗机构基础数据集', '结构化数据', 1, '公开数据下载', 'CSV', 35862, '公开', '已发布', '全国各级医疗机构名称、地址、等级、床位数等基础信息，31个省份。'),
('全国卫生技术人员统计', '统计数据', 1, '官方发布', 'CSV', 3168, '公开', '已发布', '各省份执业医师、注册护士、药师等卫生技术人员数量统计。'),
('健康产业市场规模数据', '产业数据', 2, '公开数据下载', 'CSV', 86, '公开', '已发布', '医疗健康、养老、保健品等细分产业市场规模与增速数据。'),
('全国主要城市气象数据集', '结构化数据', 3, 'API接口', 'CSV', 43800, '公开', '已发布', '2024-2026年全国主要城市逐日气温、降水量、空气质量数据。'),
('互联网健康舆情数据集', '文本内容', 4, '网页采集', 'JSON', 15280, '公开', '已发布', '主流媒体与社交平台健康相关话题舆情数据，含情感标签。'),
('健康门户内容资源库', '文本内容', 5, '网页采集', 'CSV', 742, '公开', '已发布', '国家卫健委、中国疾控中心等权威来源的新闻、政策、知识内容，共742条。'),
('全国居民健康统计年报', '统计数据', 2, '官方发布', 'XLSX', 1258, '公开', '已发布', '历年人口健康指标、慢性病患病率、医疗服务利用等统计数据。'),
('传染病监测数据集', '结构化数据', 1, 'API接口', 'JSON', 5670, '内部', '已发布', '全国法定传染病月度报告数据，含病种分类与地域分布。');

TRUNCATE TABLE application_info;
INSERT INTO application_info (app_name, app_desc, app_icon, app_url, sort, status) VALUES
('数据大屏', '多维度健康数据可视化分析，机构分布、医疗资源、内容趋势等5大图表。', NULL, '/dashboard', 1, 1),
('资源目录', '健康大数据资源目录，按安全等级分类浏览与下载。', NULL, '/resources', 2, 1),
('内容管理', '健康门户内容发布管理，新闻、政策、知识分类维护。', NULL, '/admin/content', 3, 1);
