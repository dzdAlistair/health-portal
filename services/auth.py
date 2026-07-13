from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import session, redirect, url_for

def hash_password(password):
    """生成密码哈希（初始化管理员时用）"""
    return generate_password_hash(password)

def verify_password(password_hash, password):
    """校验密码"""
    return check_password_hash(password_hash, password)

def login_required(f):
    """后台登录校验装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated