"""
门户内容数据清洗脚本 — 5.5 数据清洗任务

读取爬虫原始 CSV，执行文本清理、空值处理、去重、
URL 规范化、日期规范化、摘要截断、类型校验，输出
清洗后 CSV 和数据质量报告。
"""

import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# ── 路径配置 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_CSV = PROJECT_ROOT / "data" / "crawler" / "portal_contents_raw.csv"
CLEAN_CSV = PROJECT_ROOT / "data" / "clean" / "portal_contents.csv"
REPORT_FILE = PROJECT_ROOT / "data" / "analysis" / "portal_content_quality_report.txt"

# ── 固定列顺序 ──
COLUMNS = [
    "title", "content_type", "category", "publish_date",
    "summary", "source", "source_url", "security_level", "data_source"
]

# ── 类型映射 ──
TYPE_TO_CATEGORY = {
    "news": "新闻公告",
    "policy": "政策资讯",
    "knowledge": "健康知识",
}

VALID_CONTENT_TYPES = {"news", "policy", "knowledge"}


# ══════════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════════

def clean_text(text):
    """清洗文本字段：去 HTML 标签、压缩空白、去首尾空格"""
    if pd.isna(text) or text is None:
        return ""
    text = str(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()


def normalize_url(url_str):
    """URL 规范化：去空格、去锚点、保留查询参数"""
    if pd.isna(url_str) or not url_str:
        return ""
    url_str = str(url_str).strip()
    # 去除 fragment
    fragment_pos = url_str.find("#")
    if fragment_pos >= 0:
        url_str = url_str[:fragment_pos]
    return url_str


def is_valid_url(url_str):
    """校验 URL 合法性"""
    if not url_str:
        return False
    return url_str.startswith("http://") or url_str.startswith("https://")


def parse_date(date_str):
    """将常见日期格式统一为 YYYY-MM-DD，无法解析返回空字符串"""
    if pd.isna(date_str) or not date_str:
        return ""
    date_str = str(date_str).strip()
    patterns = [
        (r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", None),
        (r"(\d{4})年(\d{1,2})月(\d{1,2})日", None),
    ]
    for pattern, _ in patterns:
        m = re.search(pattern, date_str)
        if m:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                return f"{y:04d}-{mo:02d}-{d:02d}"
            except ValueError:
                return ""
    return ""


def truncate_summary(text, max_chars=200):
    """截断摘要到指定长度，超出添加中文省略号"""
    if pd.isna(text) or not text:
        return ""
    text = str(text)
    if len(text) > max_chars:
        return text[:max_chars] + "…"
    return text


def infer_content_type(row):
    """根据已有信息推断 content_type"""
    ct = row["content_type"]
    if pd.isna(ct) or str(ct).strip() == "":
        # 尝试从 category 推断
        cat = str(row.get("category", "")).strip()
        for t, c in TYPE_TO_CATEGORY.items():
            if cat == c:
                return t
        # 尝试从 source_url 域名推断
        url = str(row.get("source_url", ""))
        if "nhc.gov.cn" in url:
            return "news"
        if "gov.cn" in url:
            return "policy"
        if "chinacdc.cn" in url:
            return "knowledge"
        return ""
    return str(ct).strip()


# ══════════════════════════════════════════════════════════════════
# 主处理流程
# ══════════════════════════════════════════════════════════════════

def main():
    # ── 统计变量 ──
    stats = {
        "raw_total": 0,
        "title_empty_removed": 0,
        "url_empty_removed": 0,
        "url_invalid_removed": 0,
        "url_dedup_removed": 0,
        "combo_dedup_removed": 0,
        "date_unparseable": 0,
        "summary_truncated": 0,
        "content_type_invalid": 0,
        "security_level_fixed": 0,
        "data_source_fixed": 0,
    }

    # ── 1. 读取 ──
    if not RAW_CSV.exists():
        print(f"错误: 输入文件不存在 — {RAW_CSV}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(RAW_CSV, encoding="utf-8-sig")
    stats["raw_total"] = len(df)

    # 检查必需字段
    missing_cols = set(COLUMNS) - set(df.columns)
    if missing_cols:
        print(f"错误: 缺少必需字段 — {missing_cols}", file=sys.stderr)
        sys.exit(1)

    print(f"读取原始数据: {len(df)} 条")

    # ── 2. 文本清理 ──
    for col in ["title", "summary", "source", "category"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_text)

    # ── 3. 空值处理 ──
    before = len(df)
    title_empty = df["title"].isna() | (df["title"].str.strip() == "")
    stats["title_empty_removed"] = title_empty.sum()
    df = df[~title_empty]
    print(f"删除空标题: {stats['title_empty_removed']} 条")

    url_empty = df["source_url"].isna() | (df["source_url"].str.strip() == "")
    stats["url_empty_removed"] = url_empty.sum()
    df = df[~url_empty]
    print(f"删除空 URL: {stats['url_empty_removed']} 条")

    # URL 格式校验
    url_invalid = ~df["source_url"].apply(is_valid_url)
    stats["url_invalid_removed"] = url_invalid.sum()
    df = df[~url_invalid]
    print(f"删除非法 URL: {stats['url_invalid_removed']} 条")

    # ── 4. URL 规范化 ──
    df["source_url"] = df["source_url"].apply(normalize_url)

    # ── 5. 去重 ──
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["source_url"], keep="first")
    stats["url_dedup_removed"] = before_dedup - len(df)
    print(f"URL 去重: {stats['url_dedup_removed']} 条")

    # 组合字段去重 (title + source + publish_date)
    before_combo = len(df)
    combo_cols = ["title", "source", "publish_date"]
    # 按摘要非空排序，保留摘要更完整的
    df["_summary_len"] = df["summary"].apply(lambda x: len(str(x)) if pd.notna(x) else 0)
    df = df.sort_values("_summary_len", ascending=False)
    df = df.drop_duplicates(subset=combo_cols, keep="first")
    df = df.drop(columns=["_summary_len"])
    stats["combo_dedup_removed"] = before_combo - len(df)
    print(f"组合字段去重: {stats['combo_dedup_removed']} 条")

    # ── 6. 日期规范化 ──
    date_before = df["publish_date"].notna() & (df["publish_date"].astype(str).str.strip() != "")
    date_non_empty_before = date_before.sum()
    df["publish_date"] = df["publish_date"].apply(parse_date)
    date_after = df["publish_date"].notna() & (df["publish_date"].astype(str).str.strip() != "")
    stats["date_unparseable"] = date_non_empty_before - date_after.sum()
    print(f"无法解析日期: {stats['date_unparseable']} 条")

    # ── 7. 摘要处理 ──
    df["summary"] = df["summary"].apply(clean_text)
    summary_before = df["summary"].apply(lambda x: len(str(x)) if x else 0)
    df["summary"] = df["summary"].apply(lambda x: truncate_summary(x, 200))
    summary_after = df["summary"].apply(lambda x: len(str(x)) if x else 0)
    stats["summary_truncated"] = (summary_before > 200).sum()
    print(f"摘要截断: {stats['summary_truncated']} 条")

    # ── 8. 类型与分类校验 ──
    invalid_mask = ~df["content_type"].isin(VALID_CONTENT_TYPES)
    stats["content_type_invalid"] = invalid_mask.sum()
    if stats["content_type_invalid"] > 0:
        print(f"非法 content_type: {stats['content_type_invalid']} 条, 尝试推断...")
        df["content_type"] = df.apply(
            lambda row: infer_content_type(row) if row.name in df[invalid_mask].index
            else row["content_type"],
            axis=1,
        )

    # 根据 content_type 统一设置 category
    df["category"] = df["content_type"].map(TYPE_TO_CATEGORY).fillna("")

    # ── 9. 固定字段校验 ──
    sec_fix = (df["security_level"] != "公开").sum()
    if sec_fix > 0:
        df["security_level"] = "公开"
        stats["security_level_fixed"] = sec_fix
        print(f"修正 security_level: {sec_fix} 条")

    ds_fix = (df["data_source"] != "crawler").sum()
    if ds_fix > 0:
        df["data_source"] = "crawler"
        stats["data_source_fixed"] = ds_fix
        print(f"修正 data_source: {ds_fix} 条")

    # ── 10. 排序 ──
    # publish_date 降序，空日期放最后，再按 content_type 和 title
    df["_date_sort"] = df["publish_date"].apply(
        lambda x: x if x and str(x).strip() else "0000-00-00"
    )
    df = df.sort_values(
        by=["_date_sort", "content_type", "title"],
        ascending=[False, True, True]
    )
    df = df.drop(columns=["_date_sort"])

    # ── 11. 输出 ──
    # 确保列顺序
    df = df[COLUMNS]

    CLEAN_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEAN_CSV, index=False, encoding="utf-8-sig")
    print(f"清洗后数据已保存: {CLEAN_CSV} ({len(df)} 条)")

    # ── 12. 质量报告 ──
    clean_total = len(df)
    news_count = (df["content_type"] == "news").sum()
    policy_count = (df["content_type"] == "policy").sum()
    knowledge_count = (df["content_type"] == "knowledge").sum()
    empty_summary = (df["summary"].isna() | (df["summary"].str.strip() == "")).sum()
    empty_date = (df["publish_date"].isna() | (df["publish_date"].astype(str).str.strip() == "")).sum()

    has_dup_urls = not df["source_url"].is_unique
    has_empty_title = df["title"].isna().any() or (df["title"].str.strip() == "").any()
    has_empty_url = (df["source_url"].str.strip() == "").any()
    has_invalid_type = (~df["content_type"].isin(VALID_CONTENT_TYPES)).any()
    date_format_ok = df["publish_date"].dropna().astype(str).str.match(
        r"^\d{4}-\d{2}-\d{2}$"
    ).all() if empty_date < clean_total else True
    all_types_present = news_count > 0 and policy_count > 0 and knowledge_count > 0
    all_crawler = (df["data_source"] == "crawler").all()

    report_lines = []
    report_lines.append("=" * 50)
    report_lines.append("数据质量报告 — portal_contents.csv")
    report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 50)
    report_lines.append("")
    report_lines.append("【基本统计】")
    report_lines.append(f"原始数据总行数: {stats['raw_total']}")
    report_lines.append(f"清洗后数据总行数: {clean_total}")
    report_lines.append("")
    report_lines.append("【删除统计】")
    report_lines.append(f"基于URL删除的重复记录数: {stats['url_dedup_removed']}")
    report_lines.append(f"基于组合字段删除的重复记录数: {stats['combo_dedup_removed']}")
    report_lines.append(f"标题为空删除数: {stats['title_empty_removed']}")
    report_lines.append(f"URL为空删除数: {stats['url_empty_removed']}")
    report_lines.append(f"非法URL删除数: {stats['url_invalid_removed']}")
    report_lines.append("")
    report_lines.append("【数据质量统计】")
    report_lines.append(f"无法解析日期数量: {stats['date_unparseable']}")
    report_lines.append(f"摘要截断数量: {stats['summary_truncated']}")
    report_lines.append(f"非法content_type数量: {stats['content_type_invalid']}")
    report_lines.append(f"固定字段修正数量: {stats['security_level_fixed'] + stats['data_source_fixed']}")
    report_lines.append("")
    report_lines.append("【分类统计】")
    report_lines.append(f"news 记录数量: {news_count}")
    report_lines.append(f"policy 记录数量: {policy_count}")
    report_lines.append(f"knowledge 记录数量: {knowledge_count}")
    report_lines.append(f"空摘要记录数量: {empty_summary}")
    report_lines.append(f"空发布日期记录数量: {empty_date}")
    report_lines.append("")
    report_lines.append("【质量检查结论】")
    report_lines.append(f"是否存在重复URL: {'是' if has_dup_urls else '否'}")
    report_lines.append(f"是否存在空标题: {'是' if has_empty_title else '否'}")
    report_lines.append(f"是否存在空URL: {'是' if has_empty_url else '否'}")
    report_lines.append(f"是否存在非法content_type: {'是' if has_invalid_type else '否'}")
    report_lines.append(f"日期格式是否全部符合要求: {'是' if date_format_ok else '否'}")
    report_lines.append(f"三种内容类型是否均有数据: {'是' if all_types_present else '否'}")
    report_lines.append(f"正式数据中是否全部为 data_source=crawler: {'是' if all_crawler else '否'}")

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"质量报告已保存: {REPORT_FILE}")
    print("\n".join(report_lines))


if __name__ == "__main__":
    main()
