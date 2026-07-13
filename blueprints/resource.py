"""数据资源路由 — 资源目录API"""
from flask import Blueprint, jsonify, request
from services.db import query_all
from services.redis_cache import get_cache, set_cache

resource_bp = Blueprint('resource', __name__)


@resource_bp.route('/resources')
def list_resources():
    """公开数据资源列表 (安全等级 = 公开)，支持分页"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('pageSize', 10, type=int)
    offset = (page - 1) * page_size

    cache_key = f'resource:list:{page}:{page_size}'
    cached = get_cache(cache_key)
    if cached:
        return jsonify({'code': 200, 'msg': 'success', **cached})

    try:
        # 查询总数
        count_sql = """
            SELECT COUNT(*) as total FROM data_resource 
            WHERE security_level = '公开' AND resource_status = '已发布'
        """
        total = query_all(count_sql)[0]['total']

        # 查询分页数据
        list_sql = """
            SELECT resource_id, resource_name, resource_type,
                   source_type, file_format, record_count,
                   update_time, security_level, description
            FROM data_resource
            WHERE security_level = '公开' AND resource_status = '已发布'
            ORDER BY update_time DESC
            LIMIT %s OFFSET %s
        """
        rows = query_all(list_sql, (page_size, offset))

        result = {'data': rows, 'total': total, 'page': page, 'pageSize': page_size}
        set_cache(cache_key, result, 3600)
        return jsonify({'code': 200, 'msg': 'success', **result})
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e), 'data': None})


@resource_bp.route('/health')
def health_check():
    """Flask 健康检查"""
    return jsonify({'status': 'ok', 'service': 'health-portal', 'code': 200})