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
    TODO: 需要原始医疗机构类型数据，暂时从 HDFS ADS 估算
    """
    # 从省份聚合数据推算出全国各类机构总数较为困难
    # 此处生成占位数据，待成员3补充机构类型维度数据后替换
    types = [
        ('综合医院', 3890),
        ('专科医院', 2150),
        ('社区卫生服务中心', 9800),
        ('乡镇卫生院', 35200),
        ('村卫生室', 608000),
        ('门诊部', 11200),
        ('妇幼保健机构', 3050),
    ]
    df = pd.DataFrame(types, columns=['name', 'value'])
    out = os.path.join(ANALYSIS_DIR, 'institution_type.csv')
    df.to_csv(out, index=False, encoding='utf-8')
    print(f"[OK] {out} ({len(df)} rows) [注: 占位数据，待成员3更新]")
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
    TODO: 应从 MySQL resource_category 表读取，暂时生成占位数据
    """
    categories = [
        ('传染病数据', 45),
        ('慢性病数据', 38),
        ('免疫规划数据', 30),
        ('公共卫生数据', 42),
        ('环境健康数据', 25),
        ('气象数据', 60),
        ('健康产业数据', 35),
        ('门户内容数据', 124),
    ]
    df = pd.DataFrame(categories, columns=['name', 'value'])
    out = os.path.join(ANALYSIS_DIR, 'resource_category.csv')
    df.to_csv(out, index=False, encoding='utf-8')
    print(f"[OK] {out} ({len(df)} rows) [注: 占位数据，待接入MySQL]")
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
