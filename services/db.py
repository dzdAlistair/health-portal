import pymysql
from config import Config

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

def query_one(sql, args=None):
    """查询单条数据"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            return cursor.fetchone()
    finally:
        conn.close()

def query_all(sql, args=None):
    """查询多条数据"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            return cursor.fetchall()
    finally:
        conn.close()

def execute(sql, args=None):
    """执行增删改，返回影响行数"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            rows = cursor.execute(sql, args)
            conn.commit()
            return rows
    finally:
        conn.close()