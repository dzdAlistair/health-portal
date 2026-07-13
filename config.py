import os

class Config:
    # Flask 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'health_portal_2026_secret_key'
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = 3600 * 2  # 登录态2小时过期

    # MySQL 数据库配置（严格对齐统一契约）
    MYSQL_HOST = '127.0.0.1'
    MYSQL_PORT = 3306
    MYSQL_USER = 'portal'
    MYSQL_PASSWORD = 'portal123'
    MYSQL_DB = 'health_portal'
    MYSQL_CHARSET = 'utf8mb4'

    # Redis 缓存配置
    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = 6379
    REDIS_DB = 0
    CACHE_TTL = 1800  # 默认缓存30分钟

    # 分析结果CSV存放目录（大数据成员输出的5个结果文件放这里）
    ANALYSIS_DIR = os.path.join(os.path.dirname(__file__), 'data', 'analysis')

    # 文件上传限制
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 单文件最大50M
    ALLOWED_EXTENSIONS = {'csv', 'json', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'}