-- 修复应用中心占位跳转地址
-- 运行: sudo mysql < scripts/fix_app_urls.sql
USE health_portal;

UPDATE application_info SET app_url = '/dashboard'  WHERE app_name = '疫情监测';
UPDATE application_info SET app_url = '/dashboard'  WHERE app_name = '慢病管理';
UPDATE application_info SET app_url = '/resources'  WHERE app_name = '健康档案';

-- 验证
SELECT app_id, app_name, app_url FROM application_info ORDER BY sort;
