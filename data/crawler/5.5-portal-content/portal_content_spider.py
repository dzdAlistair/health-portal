"""
门户内容采集脚本 — 5.5 数据采集任务 (v2 优化版)

从中国政府网 (gov.cn) 和中国疾控中心 (chinacdc.cn) 采集
政策、健康知识公开内容。国家卫健委 (nhc.gov.cn) 因 WAF 防护
(HTTP 412) 在所有入口均被封锁，已确认无法访问。

优化记录（基于 5.1-5.4 组员代码参考 + 实际页面结构分析）：
- 日期提取：新增 meta[firstpublishedtime]、h5 发布时间正则、隐藏 div 日期
- URL 过滤：跳过目录页（/结尾）、非 .htm/.html 页
- 标题清洗：去除日期前缀、面包屑导航、站点名
- 来源提取：从 h5 标签解析 "来源：XXX 发布时间：YYY"
- 摘要回退：增加 .trs_editor_view, .wzboxtext 等 CDC 内容区选择器

采集策略：低频、克制、合规
- 请求间隔 5-10 秒随机，重试递增 2s-4s-8s
- 超时 10 秒，最多 3 次重试
- 不绕过验证码/登录/限流/WAF
"""

import logging
import re
import sys
import time
import random
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ── 路径配置 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "crawler"
ANALYSIS_DIR = PROJECT_ROOT / "data" / "analysis"
RAW_CSV = RAW_DATA_DIR / "portal_contents_raw.csv"
LOG_FILE = ANALYSIS_DIR / "portal_content_spider.log"

# ── 固定列顺序 ──
COLUMNS = [
    "title", "content_type", "category", "publish_date",
    "summary", "source", "source_url", "security_level", "data_source"
]

# ── 日志配置 ──
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# 公共工具函数
# ══════════════════════════════════════════════════════════════════

def make_session():
    """创建 Session，复用连接，设置浏览器级请求头"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
    })
    return session


def fetch_url(session, url, timeout=10, max_retries=3):
    """
    GET 请求，递增重试。
    仅对超时、连接错误和 5xx 重试。403/412/429 等直接放弃。
    """
    retry_waits = [2, 4, 8]
    for attempt in range(max_retries + 1):
        try:
            resp = session.get(url, timeout=timeout)
            status = resp.status_code

            if status == 200:
                return resp

            if status in (401, 403, 412, 429):
                logger.warning("状态码 %d — 跳过: %s", status, url)
                return None

            if 400 <= status < 500 and status != 408:
                logger.warning("状态码 %d — 跳过: %s", status, url)
                return None

            if attempt < max_retries:
                wait = retry_waits[min(attempt, len(retry_waits) - 1)]
                logger.info("状态码 %d — %d 秒后重试 (%d/%d)",
                            status, wait, attempt + 1, max_retries)
                time.sleep(wait)
            else:
                logger.warning("状态码 %d — 已达最大重试: %s", status, url)
                return None

        except (requests.Timeout, requests.ConnectionError) as e:
            if attempt < max_retries:
                wait = retry_waits[min(attempt, len(retry_waits) - 1)]
                logger.info("%s — %d 秒后重试 (%d/%d)",
                            type(e).__name__, wait, attempt + 1, max_retries)
                time.sleep(wait)
            else:
                logger.warning("%s — 已达最大重试: %s", type(e).__name__, url)
                return None
        except requests.RequestException as e:
            logger.warning("%s — 请求失败: %s", type(e).__name__, url)
            return None
    return None


def check_robots(domain, session):
    """检查 robots.txt"""
    robots_url = f"https://{domain}/robots.txt"
    try:
        resp = session.get(robots_url, timeout=10)
        if resp.status_code == 200:
            rp = RobotFileParser()
            rp.parse(resp.text.splitlines())
            logger.info("已读取 robots.txt: %s", robots_url)
            return rp
        else:
            logger.info("robots.txt 不可用 (%d): %s", resp.status_code, robots_url)
            return None
    except Exception:
        logger.info("无法获取 robots.txt: %s", robots_url)
        return None


def clean_text(text):
    """去 HTML 标签、压缩空白、清控制字符，使用 NFKC 规范化"""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text))
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()


def clean_title(title):
    """清洗标题：去除日期前缀、面包屑、站点名"""
    title = clean_text(title)
    if not title:
        return ""
    # 去除 "YYYY-MM-DD" 或 "YYYY年M月D日" 日期前缀
    title = re.sub(r"^(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})\s*", "", title)
    title = re.sub(r"^(\d{4}年\d{1,2}月\d{1,2}日)\s*", "", title)
    # 面包屑 "首页>xxx>" → 去除
    title = re.sub(r"^首页\s*[>\s]+\s*", "", title)
    title = re.sub(r"[>\s]*中心要闻[>\s]*", "", title)
    title = title.strip()
    return title


def parse_date(date_str):
    """解析常见日期格式 → YYYY-MM-DD，失败返回空"""
    if not date_str:
        return ""
    date_str = str(date_str).strip()
    # 标准格式
    patterns = [
        r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})",
        r"(\d{4})年(\d{1,2})月(\d{1,2})日",
    ]
    for pattern in patterns:
        m = re.search(pattern, date_str)
        if m:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                return f"{y:04d}-{mo:02d}-{d:02d}"
            except ValueError:
                return ""
    return ""


def normalize_url(href, base_url):
    """相对链接→绝对链接，去锚点，仅保留 http/https"""
    if not href:
        return ""
    full = urljoin(base_url, href)
    parsed = urlparse(full)
    if parsed.scheme not in ("http", "https"):
        return ""
    clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if parsed.query:
        clean += f"?{parsed.query}"
    return clean


def is_article_url(url):
    """判断是否为文章详情页 URL（排除列表/导航/目录页）"""
    if not url:
        return False
    # 目录页：以 / 结尾且路径层级少
    path = urlparse(url).path
    if path.endswith("/") and path.count("/") <= 2:
        return False
    # 必须有 .htm 或 .html 扩展名
    if not re.search(r"\.html?", path):
        # 除非是 gov.cn content_ 格式
        if "content_" not in path:
            return False
    # 排除明确的导航关键字
    skip_kw = ["javascript:", "mailto:", "#", "english/", "EN/"]
    if any(kw in url for kw in skip_kw):
        return False
    return True


def extract_detail(session, detail_url):
    """
    访问详情页，返回 (publish_date, summary, source)。
    v2: 扩展日期选择器覆盖 gov /content/ 模板和 ivdc CDC 页面。
    """
    publish_date = ""
    summary = ""
    source = ""

    resp = fetch_url(session, detail_url)
    if not resp:
        return publish_date, summary, source

    soup = BeautifulSoup(resp.text, "html.parser")

    # ── 日期提取 ──────────────────────────────────────────
    # 优先级：meta 标签 > CSS 选择器 > 正则文本匹配
    date_selectors = [
        # meta 标签（gov.cn /content/ 模板用 firstpublishedtime）
        "meta[name=\"firstpublishedtime\"]",
        "meta[name=\"lastmodifiedtime\"]",
        "meta[name=\"publishdate\"]",
        "meta[name=\"PubDate\"]",
        "meta[name=\"weibo:article:create_at\"]",
        # CSS 选择器
        ".pages-date",          # gov.cn /zhengce/ 模板
        ".date",                # chinacdc.cn 文章页通用
        ".info span",
        ".source span",
        ".article-info time",
        ".time",
        ".pubTime",
    ]
    for sel in date_selectors:
        elem = soup.select_one(sel)
        if elem:
            text = elem.get("content", "") if elem.name == "meta" else elem.get_text()
            parsed = parse_date(text)
            if parsed:
                publish_date = parsed
                break

    # 回退 1: 隐藏 div 日期（gov.cn /content/ 模板）
    if not publish_date:
        for div in soup.select("div[style*=\"display:none\"]"):
            parsed = parse_date(div.get_text())
            if parsed:
                publish_date = parsed
                break

    # 回退 2: h5 标签 "发布时间：YYYY-MM-DD"（ivdc CDC 页面）
    if not publish_date:
        for tag in soup.find_all(["h5", "h4", "h6", "span", "p", "div"]):
            text = tag.get_text()
            m = re.search(r"发布时间[：:]\s*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})", text)
            if m:
                publish_date = parse_date(m.group(1))
                break

    # 回退 3: 全文正则匹配日期（gov.cn /content/ 模板文字日期）
    if not publish_date:
        text = soup.get_text()
        m = re.search(r"(\d{4}年\d{1,2}月\d{1,2}日)", text)
        if m:
            publish_date = parse_date(m.group(1))

    # ── 来源提取 ──────────────────────────────────────────
    # 优先从 h5 等标签中提取 "来源：XXX 发布时间"
    #   (?<!图片) 排除 "（图片来源：）" 被误识别为来源
    for tag in soup.find_all(["h5", "h4", "span", "div", "p"]):
        text = tag.get_text()
        m = re.search(r"(?<!图片)来源[：:]\s*(.+?)(?:\s+发布时间|\s+\d{4}|\s*$)", text)
        if m:
            source = m.group(1).strip()
            if len(source) > 50:
                source = source[:50]
            break

    # 回退: CSS 选择器
    if not source:
        for sel in [".source", ".info span", ".article-source"]:
            elem = soup.select_one(sel)
            if elem:
                text = elem.get_text().strip()
                m = re.search(r"(?<!图片)来源[：:]\s*(.+?)(?:\s|$)", text)
                if m:
                    source = m.group(1).strip()
                    if len(source) > 50:
                        source = source[:50]
                break

    # 来源校验: 排除明显异常的提取结果
    if source:
        source = source.rstrip("，。、,.")
        # 1. 过短（<2字符）→ 无效
        # 2. 含版权关键词 → 大概率是版权声明文本
        # 3. 英文占比 >80%（ASCII字母 > 中文）→ 非来源名称
        copyright_words = ["版权", "免责", "所有文字", "音视频", "稿件"]
        ascii_alpha = sum(1 for c in source if c.isascii() and c.isalpha())
        chinese = sum(1 for c in source if '一' <= c <= '鿿')
        is_english_text = ascii_alpha > 0 and chinese == 0 and ascii_alpha > len(source) * 0.5
        if len(source) < 2 or any(w in source for w in copyright_words) or is_english_text:
            source = ""

    # ── 摘要提取 ──────────────────────────────────────────
    # meta description
    meta_desc = soup.find("meta", {"name": "description"})
    if meta_desc and meta_desc.get("content"):
        summary = clean_text(meta_desc["content"])

    # 回退: 正文首段
    if not summary:
        content_selectors = [
            ".pages-content", ".TRS_Editor", ".trs_editor_view",
            ".wzboxtext",                    # ivdc CDC 正文容器
            ".article", ".article-content",
            ".content", ".con", "#xw_box", ".text", ".detail-con",
        ]
        for sel in content_selectors:
            content_el = soup.select_one(sel)
            if content_el:
                first_p = content_el.find("p")
                if first_p:
                    candidate = clean_text(first_p.get_text())
                    if len(candidate) > 10:
                        summary = candidate
                        break
        # 如果正文选择器都没找到，取第一个有内容的 p
        if not summary:
            for p in soup.find_all("p"):
                candidate = clean_text(p.get_text())
                if len(candidate) > 15:
                    summary = candidate
                    break

    if summary and len(summary) > 200:
        summary = summary[:200] + "…"

    return publish_date, summary, source


# ══════════════════════════════════════════════════════════════════
# 网站一：中国政府网 (gov.cn) — policy
# ══════════════════════════════════════════════════════════════════

def crawl_gov(session):
    """采集中国政府网政策文件"""
    site_name = "中国政府网"
    content_type = "policy"
    default_source = "中国政府网"

    logger.info("===== 开始采集: %s (%s) =====", site_name, content_type)

    rp = check_robots("www.gov.cn", session)

    records = []
    pages_requested = 0
    requests_failed = 0
    pages_skipped = 0

    list_urls = [
        "https://www.gov.cn/zhengce/",              # 最新政策（/zhengce/ 模板）
        "https://www.gov.cn/zhengce/zuixin/",        # 最新政策列表
        "https://www.gov.cn/zhengce/zhengceku/",     # 政策库
    ]

    seen_urls = set()

    for list_url in list_urls:
        if rp and not rp.can_fetch(session.headers["User-Agent"], list_url):
            logger.info("robots.txt 禁止: %s", list_url)
            pages_skipped += 1
            continue

        pages_requested += 1
        resp = fetch_url(session, list_url)
        if not resp:
            requests_failed += 1
            logger.info("%s 返回非 200，跳过列表页", list_url)
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup.select("a[href]"):
            href = tag.get("href", "")
            title = tag.get_text(strip=True)

            if len(title) < 10:
                continue
            if "content_" not in href and "/content/" not in href:
                if "/zhengce/" not in href:
                    continue

            detail_url = normalize_url(href, list_url)
            if not detail_url or "gov.cn" not in detail_url:
                continue
            if detail_url in seen_urls:
                continue
            seen_urls.add(detail_url)

            # 跳过非文章页面
            if not is_article_url(detail_url):
                continue

            time.sleep(random.uniform(5, 10))
            pages_requested += 1
            publish_date, summary, actual_source = extract_detail(session, detail_url)
            source = actual_source if actual_source else default_source

            title_clean = clean_title(title)
            if len(title_clean) < 6:
                continue

            records.append({
                "title": title_clean,
                "content_type": content_type,
                "category": "政策资讯",
                "publish_date": publish_date,
                "summary": summary,
                "source": source,
                "source_url": detail_url,
                "security_level": "公开",
                "data_source": "crawler",
            })

    logger.info("%s: 请求 %d 页, 失败 %d, 跳过 %d, 采集 %d 条",
                site_name, pages_requested, requests_failed, pages_skipped, len(records))
    return records, pages_requested, requests_failed, pages_skipped


# ══════════════════════════════════════════════════════════════════
# 网站二：中国疾控中心 (chinacdc.cn) — knowledge
# ══════════════════════════════════════════════════════════════════

def crawl_chinacdc(session):
    """采集中国疾控中心健康知识（含子域 ivdc/other）"""
    site_name = "中国疾控中心"
    content_type = "knowledge"
    base_url = "https://www.chinacdc.cn"
    default_source = "中国疾病预防控制中心"

    logger.info("===== 开始采集: %s (%s) =====", site_name, content_type)

    rp = check_robots("www.chinacdc.cn", session)

    records = []
    pages_requested = 0
    requests_failed = 0
    pages_skipped = 0
    seen_urls = set()

    pages_requested += 1
    home_resp = fetch_url(session, base_url + "/")
    if not home_resp:
        logger.warning("CDC 首页不可访问")
        return records, pages_requested, 1, pages_skipped

    soup = BeautifulSoup(home_resp.text, "html.parser")

    # 提取子栏目链接
    sub_links = set()
    for tag in soup.select("a[href]"):
        href = tag.get("href", "")
        full = normalize_url(href, base_url)
        if full and "chinacdc.cn" in full:
            skip_patterns = ["javascript:", "mailto:", "#", "english", "EN", "gjzx"]
            if not any(p in full for p in skip_patterns):
                sub_links.add(full)

    logger.info("CDC 子栏目入口: %d 个", len(sub_links))

    for sub_url in list(sub_links)[:25]:
        if rp and not rp.can_fetch(session.headers["User-Agent"], sub_url):
            pages_skipped += 1
            continue

        time.sleep(random.uniform(5, 10))
        pages_requested += 1
        sub_resp = fetch_url(session, sub_url)
        if not sub_resp:
            requests_failed += 1
            continue

        try:
            sub_soup = BeautifulSoup(sub_resp.text, "html.parser")
        except Exception:
            continue

        for tag in sub_soup.select("a[href]"):
            href = tag.get("href", "")
            title = tag.get_text(strip=True)

            if len(title) < 6:
                continue

            detail_url = normalize_url(href, sub_url)
            if not detail_url or "chinacdc.cn" not in detail_url:
                continue
            if detail_url in seen_urls:
                continue
            seen_urls.add(detail_url)

            # 过滤列表/导航页
            if not is_article_url(detail_url):
                continue

            time.sleep(random.uniform(5, 10))
            pages_requested += 1
            publish_date, summary, actual_source = extract_detail(session, detail_url)
            source = actual_source if actual_source else default_source

            title_clean = clean_title(title)
            if len(title_clean) < 6:
                continue
            # 过滤纯站点名
            if title_clean in ("中国疾病预防控制中心", "中国疾控中心"):
                continue

            records.append({
                "title": title_clean,
                "content_type": content_type,
                "category": "健康知识",
                "publish_date": publish_date,
                "summary": summary,
                "source": source,
                "source_url": detail_url,
                "security_level": "公开",
                "data_source": "crawler",
            })

    logger.info("%s: 请求 %d 页, 失败 %d, 跳过 %d, 采集 %d 条",
                site_name, pages_requested, requests_failed, pages_skipped, len(records))
    return records, pages_requested, requests_failed, pages_skipped


# ══════════════════════════════════════════════════════════════════
# 网站三：国家卫健委 (nhc.gov.cn) — 因 WAF 跳过
# ══════════════════════════════════════════════════════════════════

def crawl_nhc(session):
    """
    国家卫健委 — 全部入口 HTTP 412 / 连接中断 / 超时。
    已测试 HTTP/HTTPS、子域名、具体文章页、移动端等 6 种入口，均被 WAF 封锁。
    不尝试绕过，直接返回空结果。
    """
    logger.info("===== 国家卫健委: 已跳过 (HTTP 412 WAF 全站封锁) =====")
    return [], 0, 0, 0


# ══════════════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════════════

def save_raw_csv(records, path):
    """保存到 CSV (UTF-8 BOM)，固定 9 列"""
    df = pd.DataFrame(records, columns=COLUMNS)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    logger.info("原始数据已保存: %s (%d 条)", path, len(df))


def main():
    logger.info("=" * 60)
    logger.info("5.5 门户内容数据采集 v2 — 开始运行")
    logger.info("项目根目录: %s", PROJECT_ROOT)
    logger.info("=" * 60)

    session = make_session()
    all_records = []
    stats = {}

    for crawler, name in [
        (crawl_gov, "中国政府网"),
        (crawl_chinacdc, "中国疾控中心"),
        (crawl_nhc, "国家卫健委"),
    ]:
        records, req, fail, skip = crawler(session)
        all_records.extend(records)
        stats[name] = {
            "records": len(records),
            "pages_requested": req,
            "requests_failed": fail,
            "pages_skipped": skip,
        }

    save_raw_csv(all_records, RAW_CSV)

    # ── 统计 ──
    logger.info("=" * 60)
    logger.info("采集完成 — 统计报告")
    logger.info("=" * 60)
    total_req = total_fail = total_skip = 0
    for name, s in stats.items():
        logger.info("%s: 请求 %d 页, 失败 %d, 跳过 %d, 采集 %d 条",
                    name, s["pages_requested"], s["requests_failed"],
                    s["pages_skipped"], s["records"])
        total_req += s["pages_requested"]
        total_fail += s["requests_failed"]
        total_skip += s["pages_skipped"]
    logger.info("---")
    logger.info("请求页面总数: %d", total_req)
    logger.info("请求失败数: %d", total_fail)
    logger.info("跳过页面数: %d", total_skip)
    logger.info("原始记录总数: %d", len(all_records))
    logger.info("原始数据文件: %s", RAW_CSV)
    logger.info("运行日志文件: %s", LOG_FILE)

    # 日期覆盖率统计
    dated = sum(1 for r in all_records if r["publish_date"])
    logger.info("有日期记录: %d / %d (%.1f%%)", dated, len(all_records),
                100 * dated / max(len(all_records), 1))

    type_counts = {}
    for r in all_records:
        t = r["content_type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    for t, c in type_counts.items():
        logger.info("content_type=%s: %d 条", t, c)

    logger.info("任务完成。")
    session.close()


if __name__ == "__main__":
    main()
