"""导入门户内容 — 将爬虫CSV灌入MySQL portal_content表
运行方式: python3 scripts/import_portal_content.py
"""
import csv
import os
import pymysql

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'clean', 'portal_contents.csv')

MYSQL_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'portal',
    'password': 'portal123',
    'database': 'health_portal',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}

# 内容类型映射（CSV中 content_type 可能是英文或中文）
TYPE_MAP = {
    'news': 'news',
    'policy': 'policy',
    'knowledge': 'knowledge',
    'application': 'application',
    '新闻': 'news',
    '政策': 'policy',
    '知识': 'knowledge',
    '应用': 'application',
}

# 分类名 → category_id 映射
CATEGORY_MAP = {
    'news': 1,   # 行业动态
    'policy': 2,  # 政策文件
    'knowledge': 3,  # 健康科普
    'application': 1,
}


def import_contents():
    if not os.path.exists(CSV_PATH):
        print(f"[ERROR] CSV 文件不存在: {CSV_PATH}")
        return

    conn = pymysql.connect(**MYSQL_CONFIG)

    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        print(f"共读取 {len(rows)} 条数据")

        inserted = 0
        skipped = 0
        with conn.cursor() as cursor:
            for row in rows:
                content_type = TYPE_MAP.get(row.get('content_type', ''), 'news')
                category_id = CATEGORY_MAP.get(content_type, 1)
                title = row.get('title', '').strip()
                if not title:
                    skipped += 1
                    continue

                summary = row.get('summary', '')[:500] if row.get('summary') else ''
                source = row.get('source', '')[:100] if row.get('source') else ''
                source_url = row.get('source_url', '')[:300] if row.get('source_url') else ''
                publishing_date = row.get('publish_date', '')[:10] if row.get('publish_date') else None
                status = row.get('status', '')
                status_val = 1 if status in ('published', '已发布', '1') else 0

                sql = """
                    INSERT INTO portal_content
                    (content_type, category_id, title, summary, source, source_url, publishing_date, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                try:
                    cursor.execute(sql, (
                        content_type, category_id, title, summary,
                        source, source_url, publishing_date, status_val
                    ))
                    inserted += 1
                except Exception:
                    skipped += 1

            conn.commit()

        print(f"✅ 导入完成: 成功 {inserted} 条, 跳过 {skipped} 条")

        # 验证
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT content_type, COUNT(*) as cnt
                FROM portal_content
                WHERE status = 1
                GROUP BY content_type
            """)
            stats = cursor.fetchall()
            print("\n各类型数量:")
            for s in stats:
                print(f"  {s['content_type']}: {s['cnt']} 条")
    finally:
        conn.close()


if __name__ == '__main__':
    import_contents()
