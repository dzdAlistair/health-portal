"""初始化管理员账号
运行方式: python3 scripts/init_admin.py
生成 sys_user 表的初始 admin 账号（默认密码 admin123）
"""
from werkzeug.security import generate_password_hash

# 默认管理员账号
USERNAME = 'admin'
PASSWORD = 'admin123'

password_hash = generate_password_hash(PASSWORD)

print(f"""
-- 管理员账号初始化 SQL（复制到 mysql 执行）
USE health_portal;

INSERT INTO sys_user (username, password_hash, role, status)
VALUES ('{USERNAME}', '{password_hash}', 'super_admin', 1)
ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash);

-- 验证
SELECT user_id, username, role, status FROM sys_user;

-- 登录地址: http://<VM_IP>/admin/login
-- 用户名: {USERNAME}
-- 密码:   {PASSWORD}
""")
