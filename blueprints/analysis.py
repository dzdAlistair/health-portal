"""分析 API 路由 — 5 个图表数据接口 + Redis 缓存"""
from flask import Blueprint, jsonify
import pandas as pd
import os
from config import Config
from services.redis_cache import get_cache, set_cache

analysis_bp = Blueprint('analysis', __name__)


def read_analysis_csv(filename):
    """读取分析结果CSV，文件不存在返回空结构"""
    path = os.path.join(Config.ANALYSIS_DIR, filename)
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, encoding='utf-8')


# ─── 1. 各地区医疗机构数量 ───
@analysis_bp.route('/analysis/institution_by_region')
def institution_by_region():
    cache_key = 'analysis:institution_by_region'
    cached = get_cache(cache_key)
    if cached:
        return jsonify({'code': 200, 'msg': 'success', 'data': cached})

    try:
        df = read_analysis_csv('institution_by_region.csv')
        data = {
            'region': df['region'].tolist() if not df.empty else [],
            'count': df['count'].tolist() if not df.empty else []
        }
        set_cache(cache_key, data)
        return jsonify({'code': 200, 'msg': 'success', 'data': data})
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e), 'data': None})


# ─── 2. 医疗机构类型分布 ───
@analysis_bp.route('/analysis/institution_type')
def institution_type():
    cache_key = 'analysis:institution_type'
    cached = get_cache(cache_key)
    if cached:
        return jsonify({'code': 200, 'msg': 'success', 'data': cached})

    try:
        df = read_analysis_csv('institution_type.csv')
        data = df[['name', 'value']].to_dict(orient='records') if not df.empty else []
        set_cache(cache_key, data)
        return jsonify({'code': 200, 'msg': 'success', 'data': data})
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e), 'data': None})


# ─── 3. 医疗资源统计 (床位/医生/护士) ───
@analysis_bp.route('/analysis/medical_resources')
def medical_resources():
    cache_key = 'analysis:medical_resources'
    cached = get_cache(cache_key)
    if cached:
        return jsonify({'code': 200, 'msg': 'success', 'data': cached})

    try:
        df = read_analysis_csv('medical_resources.csv')
        data = {
            'region': df['region'].tolist() if not df.empty else [],
            'beds': df['beds'].tolist() if not df.empty else [],
            'doctors': df['doctors'].tolist() if not df.empty else [],
            'nurses': df['nurses'].tolist() if not df.empty else []
        }
        set_cache(cache_key, data)
        return jsonify({'code': 200, 'msg': 'success', 'data': data})
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e), 'data': None})


# ─── 4. 门户内容发布趋势 ───
@analysis_bp.route('/analysis/content_trend')
def content_trend():
    cache_key = 'analysis:content_trend'
    cached = get_cache(cache_key)
    if cached:
        return jsonify({'code': 200, 'msg': 'success', 'data': cached})

    try:
        df = read_analysis_csv('content_trend.csv')
        data = {
            'month': df['month'].tolist() if not df.empty else [],
            'news': df['news'].tolist() if 'news' in df.columns else [],
            'policy': df['policy'].tolist() if 'policy' in df.columns else [],
            'knowledge': df['knowledge'].tolist() if 'knowledge' in df.columns else []
        }
        set_cache(cache_key, data)
        return jsonify({'code': 200, 'msg': 'success', 'data': data})
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e), 'data': None})


# ─── 5. 数据资源类别分布 ───
@analysis_bp.route('/analysis/resource_category')
def resource_category():
    cache_key = 'analysis:resource_category'
    cached = get_cache(cache_key)
    if cached:
        return jsonify({'code': 200, 'msg': 'success', 'data': cached})

    try:
        df = read_analysis_csv('resource_category.csv')
        data = df[['name', 'value']].to_dict(orient='records') if not df.empty else []
        set_cache(cache_key, data)
        return jsonify({'code': 200, 'msg': 'success', 'data': data})
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e), 'data': None})