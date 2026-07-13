-- 初始化基础数据
USE health_portal;

-- 1. 初始化内容分类
INSERT INTO `content_category` (`cate_name`, `content_type`, `sort`) VALUES
('行业动态', 'news', 1),
('政策文件', 'policy', 2),
('健康科普', 'knowledge', 3);

-- 2. 初始化资源分类
INSERT INTO `resource_category` (`cate_name`, `sort`) VALUES
('医疗资源', 1),
('健康统计', 2),
('健康产业', 3),
('气象环境', 4),
('互联网信息', 5);

-- 3. 测试门户内容（3条）
INSERT INTO `portal_content` (`content_type`, `category_id`, `title`, `summary`, `source`, `publish_date`, `status`, `views`) VALUES
('news', 1, '2026年全国医疗资源总量持续增长', '国家卫健委发布最新数据，全国医疗机构数量同比增长3.2%，床位数突破900万张。', '国家卫健委', '2026-06-15', 1, 128),
('policy', 2, '“健康中国2030”规划中期评估报告发布', '报告显示健康中国建设各项指标稳步推进，公共卫生服务体系持续完善。', '国家卫健委', '2026-05-20', 1, 256),
('knowledge', 3, '夏季常见传染病预防指南', '夏季高温高湿，肠道传染病、中暑等高发，需注意饮食卫生与防暑降温。', '中国疾控中心', '2026-07-01', 1, 342);

-- 4. 测试数据资源（3条）
INSERT INTO `data_resource` (`resource_name`, `resource_type`, `category_id`, `source_type`, `file_format`, `record_count`, `security_level`, `resource_status`, `description`) VALUES
('全国医疗机构基础数据集', '结构化数据', 1, '公开数据下载', 'CSV', 35862, '公开', '已发布', '包含全国各级医疗机构的名称、地址、等级、床位等基础信息。'),
('全国居民健康统计年报', '统计数据', 2, '官方发布', 'XLSX', 1258, '公开', '已发布', '涵盖历年人口健康指标、慢性病患病率、医疗服务利用等统计数据。'),
('健康产业市场规模数据', '产业数据', 3, '行业报告采集', 'CSV', 86, '公开', '已发布', '包含医疗健康、养老、保健品等细分产业的市场规模与增速数据。');