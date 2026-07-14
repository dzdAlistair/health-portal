"""门户页面路由 — 首页、新闻、政策、健康知识、应用中心、资源中心"""
from flask import Blueprint, render_template, request
from services.db import query_all, query_one

portal_bp = Blueprint('portal', __name__)


@portal_bp.route('/')
def index():
    """门户首页 — 最新内容 + 应用入口"""
    # 最新6条新闻
    latest_news = query_all("""
        SELECT content_id, title, summary, publishing_date, source
        FROM portal_content
        WHERE content_type = 'news' AND status = 1
        ORDER BY publishing_date DESC
        LIMIT 6
    """)
    # 最新3条政策
    latest_policy = query_all("""
        SELECT content_id, title, summary, publishing_date, source
        FROM portal_content
        WHERE content_type = 'policy' AND status = 1
        ORDER BY publishing_date DESC
        LIMIT 3
    """)
    # 最新3条健康知识
    latest_knowledge = query_all("""
        SELECT content_id, title, summary, publishing_date, source
        FROM portal_content
        WHERE content_type = 'knowledge' AND status = 1
        ORDER BY publishing_date DESC
        LIMIT 3
    """)
    # 启用的应用列表
    apps = query_all("""
        SELECT app_id, app_name, app_desc, app_icon, app_url
        FROM application_info
        WHERE status = 1
        ORDER BY sort
    """)
    return render_template('portal/index.html',
                           latest_news=latest_news,
                           latest_policy=latest_policy,
                           latest_knowledge=latest_knowledge,
                           apps=apps)


@portal_bp.route('/news')
def news():
    """新闻公告列表 — JS 通过 /api/contents?type=news 加载数据"""
    page = request.args.get('page', 1, type=int)
    total = query_one("""
        SELECT COUNT(*) as cnt FROM portal_content
        WHERE content_type = 'news' AND status = 1
    """)['cnt']
    return render_template('portal/news.html', page=page, total=total)


@portal_bp.route('/policy')
def policy():
    """政策资讯列表 — JS 通过 /api/contents?type=policy 加载数据"""
    page = request.args.get('page', 1, type=int)
    total = query_one("""
        SELECT COUNT(*) as cnt FROM portal_content
        WHERE content_type = 'policy' AND status = 1
    """)['cnt']
    return render_template('portal/policy.html', page=page, total=total)


@portal_bp.route('/knowledge')
def knowledge():
    """健康知识库 — JS 通过 /api/contents?type=knowledge 加载数据"""
    page = request.args.get('page', 1, type=int)
    total = query_one("""
        SELECT COUNT(*) as cnt FROM portal_content
        WHERE content_type = 'knowledge' AND status = 1
    """)['cnt']
    return render_template('portal/knowledge.html', page=page, total=total)


@portal_bp.route('/apps')
def apps():
    """应用中心"""
    app_list = query_all("""
        SELECT app_id, app_name, app_desc, app_icon, app_url, sort
        FROM application_info
        WHERE status = 1
        ORDER BY sort
    """)
    return render_template('portal/apps.html', apps=app_list)


@portal_bp.route('/resources')
def resources():
    """数据资源中心 — 公开资源列表"""
    page = request.args.get('page', 1, type=int)
    page_size = 10
    offset = (page - 1) * page_size

    total = query_one("""
        SELECT COUNT(*) as cnt FROM data_resource
        WHERE security_level = '公开' AND resource_status = '已发布'
    """)['cnt']

    resource_list = query_all("""
        SELECT resource_id, resource_name, resource_type,
               source_type, file_format, record_count,
               update_time, security_level, description
        FROM data_resource
        WHERE security_level = '公开' AND resource_status = '已发布'
        ORDER BY update_time DESC
        LIMIT %s OFFSET %s
    """, (page_size, offset))

    return render_template('portal/resources.html',
                           resources=resource_list,
                           total=total, page=page)


@portal_bp.route('/dashboard')
def dashboard():
    """数据可视化大屏 — ECharts 通过 /api/analysis/* 加载"""
    return render_template('portal/dashboard.html')
