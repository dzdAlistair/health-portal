"""后台管理路由 — 登录、内容管理、资源管理"""
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from functools import wraps

admin_bp = Blueprint('admin', __name__)


def login_required(f):
    """登录校验装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """管理员登录"""
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        # TODO: 验证用户名密码 (bcrypt)
        if username == 'admin' and password == 'admin123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin.dashboard'))
        return render_template('admin/login.html', error='用户名或密码错误')
    return render_template('admin/login.html')


@admin_bp.route('/')
@login_required
def dashboard():
    """管理后台首页"""
    return render_template('admin/dashboard.html')


@admin_bp.route('/logout')
def logout():
    """退出登录"""
    session.clear()
    return redirect(url_for('admin.login'))
