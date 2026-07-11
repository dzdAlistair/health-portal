"""数据资源路由 — 资源目录"""
from flask import Blueprint, jsonify
import pymysql
from config import Config

resource_bp = Blueprint('resource', __name__)


def get_db():
    """获取数据库连接"""
    return pymysql.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        charset=Config.MYSQL_CHARSET,
        cursorclass=pymysql.cursors.DictCursor
    )


@resource_bp.route('/resources')
def list_resources():
    """公开数据资源列表 (安全等级 = 公开)"""
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT resource_id, resource_name, resource_type,
                       source_type, file_format, record_count,
                       update_time, security_level, description
                FROM data_resource
                WHERE security_level = '公开' AND resource_status = '已发布'
                ORDER BY update_time DESC
            """)
            rows = cur.fetchall()
        conn.close()
        return jsonify({'code': 200, 'data': rows})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


@resource_bp.route('/health')
def health_check():
    """Flask 健康检查"""
    return jsonify({'status': 'ok', 'service': 'health-portal'})
