"""门户页面路由 — 首页、新闻、政策、健康知识、应用中心"""
from flask import Blueprint, render_template

portal_bp = Blueprint('portal', __name__)


@portal_bp.route('/')
def index():
    """门户首页"""
    return render_template('portal/index.html')


@portal_bp.route('/news')
def news():
    """新闻公告列表"""
    return render_template('portal/news.html')


@portal_bp.route('/policy')
def policy():
    """政策资讯列表"""
    return render_template('portal/policy.html')


@portal_bp.route('/knowledge')
def knowledge():
    """健康知识库"""
    return render_template('portal/knowledge.html')


@portal_bp.route('/apps')
def apps():
    """应用中心"""
    return render_template('portal/apps.html')


@portal_bp.route('/resources')
def resources():
    """数据资源中心"""
    return render_template('portal/resources.html')


@portal_bp.route('/dashboard')
def dashboard():
    """数据可视化大屏"""
    return render_template('portal/dashboard.html')
