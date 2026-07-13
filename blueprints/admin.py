"""后台管理路由 — 登录、内容管理、资源管理"""
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from services.db import query_one, query_all, execute
from services.auth import verify_password, login_required
from services.redis_cache import delete_cache

admin_bp = Blueprint('admin', __name__)


# ─── 登录登出 ───
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """管理员登录"""
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        user = query_one("SELECT * FROM sys_user WHERE username = %s AND status = 1", (username,))
        if user and verify_password(user['password_hash'], password):
            session['admin_logged_in'] = True
            session['admin_user'] = user['username']
            session['admin_role'] = user['role']
            return redirect(url_for('admin.dashboard'))
        return render_template('admin/login.html', error='用户名或密码错误')
    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    """退出登录"""
    session.clear()
    return redirect(url_for('admin.login'))


@admin_bp.route('/')
@login_required
def dashboard():
    """管理后台首页"""
    # 统计数据
    content_count = query_one("SELECT COUNT(*) as cnt FROM portal_content WHERE status = 1")['cnt']
    resource_count = query_one("SELECT COUNT(*) as cnt FROM data_resource WHERE resource_status = '已发布'")['cnt']
    return render_template('admin/dashboard.html', content_count=content_count, resource_count=resource_count)


# ─── 内容管理 CRUD ───
@admin_bp.route('/content')
@login_required
def content_list():
    """内容列表页"""
    content_type = request.args.get('type', 'news')
    contents = query_all("""
        SELECT c.*, cate.cate_name 
        FROM portal_content c 
        LEFT JOIN content_category cate ON c.category_id = cate.cate_id
        WHERE c.content_type = %s 
        ORDER BY c.update_time DESC
    """, (content_type,))
    return render_template('admin/content_list.html', contents=contents, content_type=content_type)


@admin_bp.route('/content/add', methods=['GET', 'POST'])
@login_required
def content_add():
    """新增内容"""
    if request.method == 'POST':
        data = request.form
        execute("""
            INSERT INTO portal_content (content_type, category_id, title, summary, content, source, publish_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data.get('content_type'), data.get('category_id'), data.get('title'),
            data.get('summary'), data.get('content'), data.get('source'),
            data.get('publish_date'), data.get('status', 0)
        ))
        # 清缓存
        delete_cache('portal:latest:*')
        return redirect(url_for('admin.content_list', type=data.get('content_type')))

    categories = query_all("SELECT * FROM content_category WHERE status = 1 ORDER BY sort")
    return render_template('admin/content_form.html', categories=categories, content=None)


@admin_bp.route('/content/delete/<int:content_id>')
@login_required
def content_delete(content_id):
    """删除内容"""
    execute("DELETE FROM portal_content WHERE content_id = %s", (content_id,))
    delete_cache('portal:latest:*')
    return redirect(url_for('admin.content_list'))


# ─── 资源管理 CRUD ───
@admin_bp.route('/resource')
@login_required
def resource_list():
    """资源列表页"""
    resources = query_all("""
        SELECT r.*, cate.cate_name 
        FROM data_resource r 
        LEFT JOIN resource_category cate ON r.category_id = cate.cate_id
        ORDER BY r.update_time DESC
    """)
    return render_template('admin/resource_list.html', resources=resources)


@admin_bp.route('/resource/add', methods=['GET', 'POST'])
@login_required
def resource_add():
    """新增资源"""
    if request.method == 'POST':
        data = request.form
        execute("""
            INSERT INTO data_resource 
            (resource_name, resource_type, category_id, source_type, file_format, 
             storage_location, hdfs_path, record_count, security_level, resource_status, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data.get('resource_name'), data.get('resource_type'), data.get('category_id'),
            data.get('source_type'), data.get('file_format'), data.get('storage_location'),
            data.get('hdfs_path'), data.get('record_count', 0), data.get('security_level'),
            data.get('resource_status', '草稿'), data.get('description')
        ))
        delete_cache('resource:list:*')
        return redirect(url_for('admin.resource_list'))

    categories = query_all("SELECT * FROM resource_category WHERE status = 1 ORDER BY sort")
    return render_template('admin/resource_form.html', categories=categories, resource=None)


@admin_bp.route('/resource/delete/<int:resource_id>')
@login_required
def resource_delete(resource_id):
    """删除资源"""
    execute("DELETE FROM data_resource WHERE resource_id = %s", (resource_id,))
    delete_cache('resource:list:*')
    return redirect(url_for('admin.resource_list'))