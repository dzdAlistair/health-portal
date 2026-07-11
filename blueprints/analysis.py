"""分析 API 路由 — 5 个图表数据接口 + Redis 缓存"""
from flask import Blueprint, jsonify
import pandas as pd
import redis
import json
from config import Config

analysis_bp = Blueprint('analysis', __name__)


def get_cache():
    """获取 Redis 连接 (不可用时返回 None)"""
    try:
        r = redis.Redis(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            db=Config.REDIS_DB,
            socket_connect_timeout=2
        )
        r.ping()
        return r
    except Exception:
        return None


def cached_or_compute(cache_key, csv_filename, compute_fn):
    """缓存优先：先查 Redis，未命中则计算并缓存"""
    r = get_cache()
    if r:
        cached = r.get(cache_key)
        if cached:
            return json.loads(cached)

    result = compute_fn()

    if r:
        r.setex(cache_key, Config.CACHE_TTL, json.dumps(result, ensure_ascii=False))
    return result


def read_csv(filename):
    """读取分析结果 CSV"""
    import os
    path = os.path.join(Config.ANALYSIS_DIR, filename)
    return pd.read_csv(path, encoding='utf-8')


# ─── 1. 各地区医疗机构数量 ───
@analysis_bp.route('/analysis/institution_by_region')
def institution_by_region():
    try:
        df = read_csv('institution_by_region.csv')
        return jsonify({
            'code': 200,
            'data': {
                'region': df['region'].tolist(),
                'count': df['count'].tolist()
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


# ─── 2. 医疗机构类型分布 ───
@analysis_bp.route('/analysis/institution_type')
def institution_type():
    try:
        df = read_csv('institution_type.csv')
        return jsonify({
            'code': 200,
            'data': df[['name', 'value']].to_dict(orient='records')
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


# ─── 3. 医疗资源统计 (床位/医生/护士) ───
@analysis_bp.route('/analysis/medical_resources')
def medical_resources():
    try:
        df = read_csv('medical_resources.csv')
        return jsonify({
            'code': 200,
            'data': {
                'region': df['region'].tolist(),
                'beds': df['beds'].tolist(),
                'doctors': df['doctors'].tolist(),
                'nurses': df['nurses'].tolist()
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


# ─── 4. 门户内容发布趋势 ───
@analysis_bp.route('/analysis/content_trend')
def content_trend():
    try:
        df = read_csv('content_trend.csv')
        return jsonify({
            'code': 200,
            'data': {
                'month': df['month'].tolist(),
                'news': df['news'].tolist() if 'news' in df.columns else [],
                'policy': df['policy'].tolist() if 'policy' in df.columns else [],
                'knowledge': df['knowledge'].tolist() if 'knowledge' in df.columns else []
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


# ─── 5. 数据资源类别分布 ───
@analysis_bp.route('/analysis/resource_category')
def resource_category():
    try:
        df = read_csv('resource_category.csv')
        return jsonify({
            'code': 200,
            'data': df[['name', 'value']].to_dict(orient='records')
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})
