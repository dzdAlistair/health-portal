"""数据桥接脚本 — 将 Spark ADS 输出转换为 Flask API 所需 CSV
运行方式: python3 scripts/data_bridge.py
"""
import pandas as pd
import os
import sys

ANALYSIS_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'analysis')
ANALYSIS_DIR = os.path.abspath(ANALYSIS_DIR)
os.makedirs(ANALYSIS_DIR, exist_ok=True)


def ensure_dir():
    os.makedirs(ANALYSIS_DIR, exist_ok=True)


def bridge_institution_by_region():
    """从 HDFS ADS 生成 institution_by_region.csv (region, count)"""
    # 需要先从 HDFS 拉到本地
    local_file = os.path.join(ANALYSIS_DIR, '..', '..', 'hdfs_ads_medical_stat.csv')
    if os.path.exists(local_file):
        df = pd.read_csv(local_file, encoding='utf-8')
    else:
        # 尝试从 spark-submit 历史输出
        print("[WARN] HDFS ADS 数据未拉到本地，请先执行:")
        print("  hdfs dfs -cat /health_portal/output/ads_medical_stat/part-*.csv > /tmp/ads_medical_stat.csv")
        return False

    # group by province, sum total_institutions
    agg = df.groupby('province')['total_institutions'].sum().reset_index()
    agg.columns = ['region', 'count']
    out = os.path.join(ANALYSIS_DIR, 'institution_by_region.csv')
    agg.to_csv(out, index=False, encoding='utf-8')
    print(f"[OK] {out} ({len(agg)} rows)")
    return True


def bridge_institution_type():
    """生成 institution_type.csv (name, value)
    从 DWD 清洗层读取 hospitals / primary_healthcare_institutions /
    specialized_public_health_institutions 三列，做全国汇总。

    DWD CSV 含 31 省 × 10 年 = 310 行明细，每行有三类机构分列。
    此处将 310 行分别按三类求和，得到饼图所需的全国机构类型分布。
    """
    import glob
    candidates = glob.glob(os.path.join(
        ANALYSIS_DIR, '5.1医疗资源数据', 'dwd_medical_resource',
        '**', '*.csv'), recursive=True)
    dwd_csv = candidates[0] if candidates else None

    if dwd_csv is None or not os.path.exists(dwd_csv):
        print("[WARN] DWD 医疗资源 CSV 未找到，使用占位数据")
        types = [('医院', 328301), ('基层医疗卫生机构', 9539508), ('专业公共卫生机构', 198034)]
        df = pd.DataFrame(types, columns=['name', 'value'])
        out = os.path.join(ANALYSIS_DIR, 'institution_type.csv')
        df.to_csv(out, index=False, encoding='utf-8')
        print(f"[OK] {out} ({len(df)} rows) [占位 — DWD 文件缺失]")
        return True

    df = pd.read_csv(dwd_csv, encoding='utf-8')
    hosp = int(df['hospitals'].sum())
    primary = int(df['primary_healthcare_institutions'].sum())
    specialized = int(df['specialized_public_health_institutions'].sum())

    types = [
        ('医院', hosp),
        ('基层医疗卫生机构', primary),
        ('专业公共卫生机构', specialized),
    ]
    result = pd.DataFrame(types, columns=['name', 'value'])
    out = os.path.join(ANALYSIS_DIR, 'institution_type.csv')
    result.to_csv(out, index=False, encoding='utf-8')
    print(f"[OK] {out} ({len(result)} rows, 全国汇总 {hosp + primary + specialized} 家机构, from DWD)")
    return True


def bridge_medical_resources():
    """从 HDFS ADS 生成 medical_resources.csv (region, beds, doctors, nurses)"""
    local_file = os.path.join(ANALYSIS_DIR, '..', '..', 'hdfs_ads_medical_stat.csv')
    if not os.path.exists(local_file):
        print("[WARN] HDFS ADS 数据未拉到本地")
        return False

    df = pd.read_csv(local_file, encoding='utf-8')
    agg = df.groupby('province').agg({
        'total_beds': 'sum',
        'total_doctors': 'sum',
        'total_nurses': 'sum'
    }).reset_index()
    agg.columns = ['region', 'beds', 'doctors', 'nurses']
    out = os.path.join(ANALYSIS_DIR, 'medical_resources.csv')
    agg.to_csv(out, index=False, encoding='utf-8')
    print(f"[OK] {out} ({len(agg)} rows)")
    return True


def bridge_content_trend():
    """从 #5 ADS 生成 content_trend.csv (month, news, policy, knowledge)"""
    src = os.path.join(ANALYSIS_DIR, '5.5门户内容数据', 'ads_portal_contents',
                       'part-00000-d9ee6a1a-1e8e-4306-9238-fa827d7b2fde-c000.csv')
    if not os.path.exists(src):
        # try glob
        import glob
        candidates = glob.glob(os.path.join(
            ANALYSIS_DIR, '5.5门户内容数据', 'ads_portal_contents', 'part-*.csv'))
        if candidates:
            src = candidates[0]
        else:
            print(f"[WARN] 未找到 ADS 门户内容数据: {src}")
            return False

    df = pd.read_csv(src, encoding='utf-8')
    # pivot: publish_month x content_type → article_total
    pivot = df.pivot_table(
        index='publish_month', columns='content_type',
        values='article_total', aggfunc='sum', fill_value=0
    ).reset_index()
    pivot.columns.name = None

    # ensure all 3 columns exist
    for col in ['news', 'policy', 'knowledge']:
        if col not in pivot.columns:
            pivot[col] = 0

    result = pivot[['publish_month', 'news', 'policy', 'knowledge']]
    result.columns = ['month', 'news', 'policy', 'knowledge']
    out = os.path.join(ANALYSIS_DIR, 'content_trend.csv')
    result.to_csv(out, index=False, encoding='utf-8')
    print(f"[OK] {out} ({len(result)} rows)")
    return True


def bridge_resource_category():
    """生成 resource_category.csv (name, value)
    从 MySQL resource_category + data_resource 统计各分类资源数量，回退到占位
    """
    out = os.path.join(ANALYSIS_DIR, 'resource_category.csv')

    try:
        import pymysql
        conn = pymysql.connect(
            host='127.0.0.1', port=3306,
            user='portal', password='portal123',
            database='health_portal', charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
        )
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT rc.cate_name AS name, COUNT(dr.resource_id) AS value
                    FROM resource_category rc
                    LEFT JOIN data_resource dr
                        ON rc.cate_id = dr.category_id
                        AND dr.resource_status = '已发布'
                    WHERE rc.status = 1
                    GROUP BY rc.cate_id, rc.cate_name
                    ORDER BY rc.sort
                """)
                rows = cur.fetchall()
        finally:
            conn.close()

        if rows:
            df = pd.DataFrame(rows, columns=['name', 'value'])
            df.to_csv(out, index=False, encoding='utf-8')
            print(f"[OK] {out} ({len(df)} rows, from MySQL)")
            return True
        else:
            print("[WARN] MySQL resource_category 为空")
            return False
    except Exception as e:
        print(f"[WARN] MySQL 连接失败: {e}")
        # 回退 — resource_category 表中共5个分类
        categories = [
            ('医疗资源', 2), ('健康统计', 1), ('健康产业', 1),
            ('气象环境', 1), ('互联网信息', 1),
        ]
        df = pd.DataFrame(categories, columns=['name', 'value'])
        df.to_csv(out, index=False, encoding='utf-8')
        print(f"[OK] {out} ({len(df)} rows) [回退占位]")
        return True


def main():
    ensure_dir()
    print("=== 数据桥接脚本 ===\n")

    results = []
    results.append(('institution_by_region', bridge_institution_by_region()))
    results.append(('institution_type', bridge_institution_type()))
    results.append(('medical_resources', bridge_medical_resources()))
    results.append(('content_trend', bridge_content_trend()))
    results.append(('resource_category', bridge_resource_category()))

    print("\n=== 结果汇总 ===")
    success = 0
    for name, ok in results:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")
        if ok:
            success += 1
    print(f"\n{success}/{len(results)} 个 CSV 已生成")


if __name__ == '__main__':
    main()
