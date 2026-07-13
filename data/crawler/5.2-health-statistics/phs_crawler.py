#!/usr/bin/env python3
"""Public Health Science Data Center crawler and export normalizer.

The site exposes dataset descriptions publicly, while indicator query results
currently require login/application. This tool never bypasses that gate. It
audits public metadata and converts legitimately obtained results into a
seven-column schema containing only fields present in the source.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from datetime import date
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


STANDARD_COLUMNS = [
    "year",
    "category",
    "indicator_name",
    "indicator_value",
    "unit",
    "source_url",
    "retrieved_date",
]

BASE_URL = "https://www.phsciencedata.cn/Share/ky_sjml.jsp?id={}"
SOURCE_NAME = "公共卫生科学数据中心"
SCRIPT_DIR = Path(__file__).resolve().parent

AUTO_EXCLUDED_FILES = {
    "health_statistics.csv",
    "crawl_status.csv",
    "phs_dataset_catalog.csv",
    "manifest.csv",
    "manifest.example.csv",
}

AUTO_FILE_HINTS = [
    (
        ("hypertension", "high_blood_pressure", "高血压"),
        "35岁以上人口医生诊断高血压患病率",
        "‰",
        BASE_URL.format("cd1dc8ff-612d-44b0-913c-cdc5f27b6268"),
    ),
    (
        ("chronic", "慢性病"),
        "慢性病患病率",
        "‰",
        BASE_URL.format("a8c95cce-8e40-42f4-9ad0-af6a681a9bd8"),
    ),
    (
        ("diabetes", "糖尿病"),
        "糖尿病患病率",
        "‰",
        BASE_URL.format("6b6cd0a5-aa9e-4481-ad3a-d5bb3ccd9ad3"),
    ),
    (
        ("infectious", "传染病"),
        "",
        "1/10万",
        BASE_URL.format("a56cd203-cd11-414d-9efa-d1583b97476f"),
    ),
]


@dataclass(frozen=True)
class DatasetSpec:
    dataset_id: str
    dataset_name: str
    coverage_years: str
    dimensions: str
    indicator_definition: str
    access_status: str = "requires_login_or_application"

    @property
    def source_url(self) -> str:
        return BASE_URL.format(self.dataset_id)


DATASETS = [
    DatasetSpec(
        "cd1dc8ff-612d-44b0-913c-cdc5f27b6268",
        "高血压病",
        "1993;1998;2003;2008",
        "地区;年龄;性别",
        "调查地区35岁以上人口医生诊断的高血压患病率",
    ),
    DatasetSpec(
        "a8c95cce-8e40-42f4-9ad0-af6a681a9bd8",
        "慢性病患病率",
        "1993;1998;2003;2008",
        "地区;年龄;性别;疾病",
        "调查前半年内患病例数与调查总人数之比",
    ),
    DatasetSpec(
        "6b6cd0a5-aa9e-4481-ad3a-d5bb3ccd9ad3",
        "糖尿病",
        "",
        "以网站合法导出字段为准",
        "网站公开目录中的糖尿病数据集",
    ),
    DatasetSpec(
        "a56cd203-cd11-414d-9efa-d1583b97476f",
        "法定报告传染病",
        "",
        "地区;疾病;时间",
        "网站公开目录中的法定报告传染病数据集",
    ),
    DatasetSpec(
        "15883803-f005-408e-b4c9-f13697f5a19f",
        "中国健康与营养调查",
        "1989;1991;1993;1997;2000;2004;2006",
        "住户;成人;儿童;健康;营养",
        "调查数据和问卷；具体健康指标须以合法下载文件的数据字典为准",
    ),
]


HEADER_ALIASES = {
    "year": {"year", "年份", "年度", "调查年份", "时间", "数据时间"},
    "region": {"region", "地区", "地区别", "区域", "地域", "城乡", "地域别"},
    "indicator_name": {
        "indicator_name",
        "指标名称",
        "指标",
        "疾病",
        "疾病别",
        "病种",
        "统计指标",
    },
    "indicator_value": {
        "indicator_value",
        "指标值",
        "数值",
        "值",
        "患病率",
        "发病率",
        "死亡率",
    },
    "unit": {"unit", "单位", "计量单位"},
    "data_source": {"data_source", "数据来源", "来源"},
    "update_date": {"update_date", "更新日期", "发布日期", "采集日期"},
}


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            text = re.sub(r"\s+", " ", html.unescape(data)).strip()
            if text:
                self.parts.append(text)

    @property
    def text(self) -> str:
        return " ".join(self.parts)


def fetch_html(url: str, timeout: int, retries: int, delay: float) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "health-portal-teaching-project/1.0 (+low-frequency; public-data-audit)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
                try:
                    return raw.decode(charset)
                except UnicodeDecodeError:
                    return raw.decode("gb18030", errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(delay * (attempt + 1))
    raise RuntimeError(f"无法访问 {url}: {last_error}")


def parse_public_page(page_html: str) -> dict[str, str]:
    parser = VisibleTextParser()
    parser.feed(page_html)
    text = parser.text
    years = sorted(set(re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", text)))
    return {
        "page_text_excerpt": text[:500],
        "observed_years": ";".join(years),
        "has_login_link": str("登录" in text),
        "has_apply_data_link": str("申请数据" in text),
    }


def write_catalog(path: Path, rows: Iterable[dict[str, str]]) -> None:
    fields = [
        "dataset_id",
        "dataset_name",
        "coverage_years",
        "dimensions",
        "indicator_definition",
        "access_status",
        "source_url",
        "checked_date",
        "observed_years",
        "page_status",
        "note",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def audit_public_pages(output_dir: Path, offline: bool, timeout: int, delay: float) -> int:
    rows: list[dict[str, str]] = []
    for index, spec in enumerate(DATASETS):
        row = asdict(spec)
        row["source_url"] = spec.source_url
        row["checked_date"] = date.today().isoformat()
        row["observed_years"] = spec.coverage_years
        row["page_status"] = "embedded_metadata_verified_by_browser" if offline else "unknown"
        row["note"] = "指标查询值需登录或申请；未采集受限数据"
        if not offline:
            try:
                page = fetch_html(spec.source_url, timeout=timeout, retries=2, delay=delay)
                parsed = parse_public_page(page)
                row["observed_years"] = parsed["observed_years"] or spec.coverage_years
                row["page_status"] = "public_metadata_fetched"
                if parsed["has_login_link"] == "True" or parsed["has_apply_data_link"] == "True":
                    row["access_status"] = "requires_login_or_application"
            except RuntimeError as exc:
                row["page_status"] = "fetch_failed"
                row["note"] = str(exc)
        rows.append(row)
        if not offline and index < len(DATASETS) - 1:
            time.sleep(delay)

    write_catalog(output_dir / "phs_dataset_catalog.csv", rows)
    standard_path = output_dir / "health_statistics.csv"
    if not standard_path.exists():
        write_standard_csv(standard_path, [])
    write_status(
        output_dir / "crawl_status.csv",
        "blocked_by_access_control" if offline else "public_metadata_only",
        0,
        "查询按钮会跳转登录；未提供合法导出文件，因此不生成虚假指标值",
    )
    return 0


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames:
                    raise ValueError("CSV 缺少表头")
                return [clean_header(x) for x in reader.fieldnames], [
                    {clean_header(k): (v or "").strip() for k, v in row.items() if k is not None}
                    for row in reader
                ]
        except (UnicodeDecodeError, csv.Error, ValueError) as exc:
            last_error = exc
    raise ValueError(f"无法读取 CSV {path}: {last_error}")


def clean_header(value: str) -> str:
    return re.sub(r"\s+", "", value.strip().lstrip("\ufeff"))


def find_column(headers: Iterable[str], logical_name: str) -> str | None:
    aliases = {clean_header(x).lower() for x in HEADER_ALIASES[logical_name]}
    for header in headers:
        if clean_header(header).lower() in aliases:
            return header
    return None


def parse_number(raw: str) -> str | None:
    value = raw.strip().replace(",", "").replace("，", "")
    value = re.sub(r"[%％‰]$", "", value).strip()
    if not value or value in {"-", "--", "—", "暂无", "无", "NA", "N/A"}:
        return None
    try:
        number = Decimal(value)
    except InvalidOperation:
        return None
    normalized = format(number, "f").rstrip("0").rstrip(".")
    return normalized or "0"


def normalize_export(
    input_path: Path,
    default_indicator: str,
    default_unit: str,
    source_url: str,
    update_date: str,
) -> list[dict[str, str]]:
    headers, rows = read_csv_rows(input_path)
    year_columns = [h for h in headers if re.fullmatch(r"(?:19|20)\d{2}年?", h)]
    region_col = find_column(headers, "region")
    indicator_col = find_column(headers, "indicator_name")
    unit_col = find_column(headers, "unit")
    source_col = find_column(headers, "data_source")
    update_col = find_column(headers, "update_date")
    records: list[dict[str, str]] = []
    default_source = SOURCE_NAME if not source_url else f"{SOURCE_NAME} ({source_url})"

    if year_columns:
        if not default_indicator and not indicator_col:
            raise ValueError(f"宽表 {input_path.name} 缺少指标名称，请在 manifest 中填写 indicator_name")
        for row in rows:
            region = (row.get(region_col, "") if region_col else "") or "全国"
            indicator = (row.get(indicator_col, "") if indicator_col else "") or default_indicator
            unit = (row.get(unit_col, "") if unit_col else "") or default_unit
            source = (row.get(source_col, "") if source_col else "") or default_source
            updated = (row.get(update_col, "") if update_col else "") or update_date
            for year_col in year_columns:
                value = parse_number(row.get(year_col, ""))
                if value is None:
                    continue
                year = year_col.removesuffix("年")
                records.append(build_record(year, region, indicator, value, unit, source, updated))
        return records

    year_col = find_column(headers, "year")
    value_col = find_column(headers, "indicator_value")
    if not year_col or not value_col:
        raise ValueError(
            f"{input_path.name} 既不是年份宽表，也缺少年份/指标值列；表头为: {', '.join(headers)}"
        )
    for row in rows:
        year_match = re.search(r"(?:19|20)\d{2}", row.get(year_col, ""))
        value = parse_number(row.get(value_col, ""))
        if not year_match or value is None:
            continue
        region = (row.get(region_col, "") if region_col else "") or "全国"
        indicator = (row.get(indicator_col, "") if indicator_col else "") or default_indicator
        if not indicator:
            raise ValueError(f"长表 {input_path.name} 缺少指标名称，请在 manifest 中填写 indicator_name")
        unit = (row.get(unit_col, "") if unit_col else "") or default_unit
        source = (row.get(source_col, "") if source_col else "") or default_source
        updated = (row.get(update_col, "") if update_col else "") or update_date
        records.append(build_record(year_match.group(0), region, indicator, value, unit, source, updated))
    return records


def build_record(
    year: str,
    category: str,
    indicator: str,
    value: str,
    unit: str,
    source_url: str,
    retrieved: str,
) -> dict[str, str]:
    return {
        "year": year,
        "category": category,
        "indicator_name": indicator,
        "indicator_value": value,
        "unit": unit,
        "source_url": source_url,
        "retrieved_date": retrieved,
    }


def write_standard_csv(path: Path, records: Iterable[dict[str, str]]) -> int:
    unique: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for record in records:
        key = (record["year"], record["category"], record["indicator_name"], record["source_url"])
        unique[key] = record
    ordered = sorted(
        unique.values(),
        key=lambda r: (int(r["year"]), r["indicator_name"], r["category"]),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=STANDARD_COLUMNS)
        writer.writeheader()
        writer.writerows(ordered)
    return len(ordered)


def write_status(path: Path, status: str, records: int, note: str) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["status", "records", "checked_date", "note"])
        writer.writeheader()
        writer.writerow(
            {
                "status": status,
                "records": records,
                "checked_date": date.today().isoformat(),
                "note": note,
            }
        )


def normalize_manifest(manifest_path: Path, output_path: Path) -> int:
    _, manifest_rows = read_csv_rows(manifest_path)
    required = {"file", "indicator_name", "unit"}
    if manifest_rows and not required.issubset(manifest_rows[0]):
        raise ValueError("manifest 必须包含 file, indicator_name, unit 列")
    records: list[dict[str, str]] = []
    today = date.today().isoformat()
    for item in manifest_rows:
        input_path = (manifest_path.parent / item["file"]).resolve()
        if not input_path.is_file():
            raise FileNotFoundError(f"找不到合法导出文件: {input_path}")
        records.extend(
            normalize_export(
                input_path=input_path,
                default_indicator=item.get("indicator_name", ""),
                default_unit=item.get("unit", ""),
                source_url=item.get("source_url", ""),
                update_date=item.get("update_date", "") or today,
            )
        )
    count = write_standard_csv(output_path, records)
    write_status(
        output_path.parent / "crawl_status.csv",
        "normalized_from_legal_exports",
        count,
        f"已处理 {len(manifest_rows)} 个合法导出文件",
    )
    return count


def infer_defaults_from_filename(path: Path) -> tuple[str, str, str]:
    name = path.stem.lower()
    for keywords, indicator, unit, source_url in AUTO_FILE_HINTS:
        if any(keyword.lower() in name for keyword in keywords):
            return indicator, unit, source_url
    return "", "", ""


def auto_normalize(directory: Path, output_path: Path) -> int:
    inputs = sorted(
        path
        for path in directory.glob("*.csv")
        if path.name.lower() not in AUTO_EXCLUDED_FILES
    )
    records: list[dict[str, str]] = []
    errors: list[str] = []
    today = date.today().isoformat()

    if not inputs:
        note = "同目录未发现网站导出的原始 CSV；未生成或更新 health_statistics.csv"
        write_status(output_path.parent / "crawl_status.csv", "no_input_exports", 0, note)
        print(f"错误：{note}", file=sys.stderr)
        return -1

    for input_path in inputs:
        indicator, unit, source_url = infer_defaults_from_filename(input_path)
        try:
            records.extend(
                normalize_export(
                    input_path=input_path,
                    default_indicator=indicator,
                    default_unit=unit,
                    source_url=source_url,
                    update_date=today,
                )
            )
        except ValueError as exc:
            errors.append(f"{input_path.name}: {exc}")

    if not records:
        status = "input_parse_failed"
        note = "没有解析出任何真实指标记录；未生成或更新 health_statistics.csv"
        if errors:
            note += "；" + "；".join(errors)
        write_status(output_path.parent / "crawl_status.csv", status, 0, note)
        print(f"错误：{note}", file=sys.stderr)
        return -1

    count = write_standard_csv(output_path, records)
    if errors:
        status = "partial_success"
        note = f"已处理 {len(inputs) - len(errors)} 个文件；" + "；".join(errors)
    else:
        status = "normalized_from_legal_exports"
        note = f"自动处理同目录 {len(inputs)} 个合法导出文件"
    write_status(output_path.parent / "crawl_status.csv", status, count, note)
    print(f"已覆盖生成 {output_path}，共 {count} 条真实指标记录")
    if errors:
        for error in errors:
            print(f"跳过：{error}", file=sys.stderr)
    return count


EDGE_CRAWL_DATASETS = [
    {
        "name": "高血压病",
        "url": BASE_URL.format("cd1dc8ff-612d-44b0-913c-cdc5f27b6268"),
        "indicator": "高血压患病率",
        "unit": "‰",
    },
    {
        "name": "慢性病患病率",
        "url": BASE_URL.format("a8c95cce-8e40-42f4-9ad0-af6a681a9bd8"),
        "indicator": "慢性病患病率",
        "unit": "‰",
    },
    {
        "name": "糖尿病",
        "url": BASE_URL.format("6b6cd0a5-aa9e-4481-ad3a-d5bb3ccd9ad3"),
        "indicator": "糖尿病患病率",
        "unit": "‰",
    },
    {
        "name": "法定报告传染病",
        "url": BASE_URL.format("a56cd203-cd11-414d-9efa-d1583b97476f"),
        "indicator": "法定报告传染病发病率",
        "unit": "1/10万",
    },
]


def _option_items(select_locator) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for option in select_locator.locator("option").all():
        value = option.get_attribute("value") or ""
        label = option.inner_text().strip()
        if value or label:
            items.append((value, label))
    return items


def _activate_query_tab(page) -> bool:
    candidates = []
    for link in page.locator("a[href^='#tabs-']").all():
        label = link.inner_text().strip()
        if label and label not in {"数据库介绍", "元数据", "相关文档"}:
            candidates.append(link)
    if not candidates:
        return False
    candidates[-1].click()
    page.wait_for_timeout(300)
    return True


def _extract_result_matrices(page) -> list[list[list[str]]]:
    """Return only leaf tables; report viewers wrap the real table many times."""
    matrices: list[list[list[str]]] = []
    for frame in page.frames:
        if frame == page.main_frame or "login.jsp" in frame.url:
            continue
        try:
            tables = frame.locator("table").all()
        except Exception:
            continue
        for table in tables:
            try:
                if table.locator("table").count():
                    continue
            except Exception:
                continue
            matrix: list[list[str]] = []
            try:
                for row in table.locator("tr").all():
                    cells = [
                        re.sub(r"\s+", " ", cell.inner_text()).strip()
                        for cell in row.locator("th,td").all()
                    ]
                    if any(cells):
                        matrix.append(cells)
            except Exception:
                continue
            if len(matrix) >= 2 and max(len(row) for row in matrix) >= 2:
                matrices.append(matrix)
    return matrices


def _indicator_label(base: str, measure: str, result: str) -> str:
    if not result or result in {"合计", "全部", "全国", base}:
        return base
    return f"{base}（{result}）"


def _wide_matrix_layout(matrix: list[list[str]]) -> tuple[int, dict[int, str], int] | None:
    """Find a compact year-wide table and its category column."""
    if not 3 <= len(matrix) <= 30:
        return None
    for header_index, header in enumerate(matrix):
        year_columns: dict[int, str] = {}
        for index, cell in enumerate(header):
            match = re.fullmatch(r"\s*((?:19|20)\d{2})年?\s*", cell)
            if match:
                year_columns[index] = match.group(1)
        if len(year_columns) < 2:
            continue
        first_year = min(year_columns)
        if first_year < 1 or max(len(row) for row in matrix) > len(year_columns) + 2:
            continue
        category_column = first_year - 1
        valid_rows = 0
        for row in matrix[header_index + 1 :]:
            category = row[category_column].strip() if category_column < len(row) else ""
            if not category or parse_number(category) is not None:
                continue
            if any(column < len(row) and parse_number(row[column]) is not None for column in year_columns):
                valid_rows += 1
        if valid_rows:
            return header_index, year_columns, category_column
    return None


def _select_canonical_matrix(matrices: list[list[list[str]]]) -> list[list[str]] | None:
    candidates = [matrix for matrix in matrices if _wide_matrix_layout(matrix) is not None]
    if not candidates:
        return None
    return min(candidates, key=lambda matrix: len(matrix) * max(len(row) for row in matrix))


def _records_from_matrix(
    matrix: list[list[str]],
    dataset: dict[str, str],
    measure: str,
    result: str,
) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    indicator = _indicator_label(dataset["indicator"], measure, result)
    source = dataset["url"]
    updated = date.today().isoformat()

    layout = _wide_matrix_layout(matrix)
    if layout is None:
        return records
    header_index, year_columns, category_column = layout
    for row in matrix[header_index + 1 :]:
        category = row[category_column].strip() if category_column < len(row) else ""
        if not category or parse_number(category) is not None:
            continue
        for column, year in year_columns.items():
            value = parse_number(row[column]) if column < len(row) else None
            if value is None:
                continue
            number = Decimal(value)
            if dataset["unit"] == "‰" and not Decimal("0") <= number <= Decimal("1000"):
                continue
            records.append(build_record(year, category, indicator, value, dataset["unit"], source, updated))
    return records


def _is_login_gate(page) -> bool:
    if "login.jsp" in page.url:
        return True
    if page.locator("iframe[src*='login.jsp']").count():
        return True
    return any("login.jsp" in frame.url for frame in page.frames)


def _query_dataset(page, dataset: dict[str, str], delay_seconds: float) -> tuple[list[dict[str, str]], list[dict]]:
    page.goto(dataset["url"], wait_until="domcontentloaded", timeout=60000)
    if not _activate_query_tab(page):
        return [], [{"dataset": dataset["name"], "error": "未找到查询标签"}]

    measure_select = page.locator("select[name='measuretype_code']")
    query_button = page.locator("input[name^='reportCondiSubmit']")
    if measure_select.count() != 1 or query_button.count() != 1:
        return [], [{"dataset": dataset["name"], "error": "未找到指标选项或查询按钮"}]

    all_records: list[dict[str, str]] = []
    diagnostics: list[dict] = []
    for measure_value, measure_label in _option_items(measure_select):
        measure_select.select_option(value=measure_value)
        page.wait_for_timeout(400)
        result_select = page.locator("select[name='measureresult_code']")
        result_items = _option_items(result_select) if result_select.count() == 1 else [("", "合计")]
        for result_value, result_label in result_items:
            if result_select.count() == 1 and result_value:
                result_select.select_option(value=result_value)
            query_button.click()
            page.wait_for_timeout(max(1000, int(delay_seconds * 1000)))
            if _is_login_gate(page):
                raise RuntimeError("登录状态无效或该数据集仍需申请权限")
            matrices = _extract_result_matrices(page)
            canonical = _select_canonical_matrix(matrices)
            extracted = (
                _records_from_matrix(canonical, dataset, measure_label, result_label)
                if canonical is not None
                else []
            )
            all_records.extend(extracted)
            diagnostics.append(
                {
                    "dataset": dataset["name"],
                    "measure": measure_label,
                    "result": result_label,
                    "table_count": len(matrices),
                    "record_count": len(extracted),
                    "tables": matrices,
                }
            )
            time.sleep(delay_seconds)
    return all_records, diagnostics


def reparse_diagnostics(diagnostics_path: Path, output_path: Path) -> int:
    """Rebuild a clean CSV from a previous crawl without logging in again."""
    try:
        diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取诊断文件 {diagnostics_path}: {exc}") from exc

    datasets = {dataset["name"]: dataset for dataset in EDGE_CRAWL_DATASETS}
    records: list[dict[str, str]] = []
    skipped_queries = 0
    for entry in diagnostics:
        dataset = datasets.get(entry.get("dataset", ""))
        matrices = entry.get("tables", [])
        if dataset is None or not isinstance(matrices, list):
            skipped_queries += 1
            continue
        canonical = _select_canonical_matrix(matrices)
        if canonical is None:
            skipped_queries += 1
            continue
        records.extend(
            _records_from_matrix(
                canonical,
                dataset,
                str(entry.get("measure", "")),
                str(entry.get("result", "")),
            )
        )
    if not records:
        raise ValueError("诊断文件中没有可验证的指标数据，未覆盖原 CSV")
    count = write_standard_csv(output_path, records)
    write_status(
        output_path.parent / "crawl_status.csv",
        "reparsed_from_diagnostics",
        count,
        f"仅解析每次查询的规范数据表；跳过 {skipped_queries} 个无有效数据的查询；单位保留为千分率",
    )
    return count


def run_authenticated_edge_crawler(
    output_path: Path,
    profile_dir: Path,
    delay_seconds: float,
) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("缺少 playwright。请先执行：D:\\python\\python.exe -m pip install playwright", file=sys.stderr)
        return -1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    diagnostics_path = output_path.parent / "crawl_diagnostics.json"
    profile_dir.mkdir(parents=True, exist_ok=True)
    all_records: list[dict[str, str]] = []
    diagnostics: list[dict] = []

    with sync_playwright() as playwright:
        try:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                channel="msedge",
                headless=False,
                accept_downloads=True,
            )
        except Exception as exc:
            print(f"无法启动 Microsoft Edge：{exc}", file=sys.stderr)
            return -1
        context.add_init_script(
            """
            (() => {
              window.alert = (message) => console.info('[blocked alert]', String(message));
              window.confirm = (message) => {
                console.info('[auto-confirmed]', String(message));
                return true;
              };
              window.prompt = (message, value = '') => {
                console.info('[auto-prompted]', String(message));
                return value;
              };
            })();
            """
        )
        page = context.pages[0] if context.pages else context.new_page()

        def handle_dialog(dialog) -> None:
            try:
                print(f"网页提示：{dialog.message}")
                dialog.accept()
            except Exception:
                # Some old pages close their own dialog before Playwright handles it.
                pass

        page.on("dialog", handle_dialog)
        page.goto("https://www.phsciencedata.cn/Share/login.jsp", wait_until="domcontentloaded", timeout=60000)
        print("请在弹出的 Microsoft Edge 窗口中登录公共卫生科学数据中心。")
        input("登录完成后回到这里按 Enter 开始采集：")

        for dataset in EDGE_CRAWL_DATASETS:
            print(f"正在采集：{dataset['name']}")
            try:
                records, detail = _query_dataset(page, dataset, delay_seconds)
                all_records.extend(records)
                diagnostics.extend(detail)
                print(f"  已提取 {len(records)} 条")
            except Exception as exc:
                diagnostics.append({"dataset": dataset["name"], "error": str(exc)})
                print(f"  跳过：{exc}", file=sys.stderr)
                if "connection closed" in str(exc).lower() or "driver" in str(exc).lower():
                    print("浏览器自动化连接已断开，停止后续采集。", file=sys.stderr)
                    break
            time.sleep(delay_seconds)
        try:
            context.close()
        except Exception:
            pass

    diagnostics_path.write_text(
        json.dumps(diagnostics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not all_records:
        note = f"未从登录后查询结果提取到记录；诊断文件：{diagnostics_path.name}"
        write_status(output_path.parent / "crawl_status.csv", "crawl_failed_or_no_permission", 0, note)
        print(f"错误：{note}", file=sys.stderr)
        return -1
    count = write_standard_csv(output_path, all_records)
    write_status(
        output_path.parent / "crawl_status.csv",
        "crawled_from_authenticated_edge_session",
        count,
        f"通过专用 Edge 登录会话采集；诊断文件：{diagnostics_path.name}",
    )
    print(f"已覆盖生成 {output_path}，共 {count} 条真实指标记录")
    return count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="公共卫生科学数据中心 Edge 自动采集与 CSV 标准化工具")
    subparsers = parser.add_subparsers(dest="command")

    audit = subparsers.add_parser("audit", help="检查公开数据集页面；不会绕过登录")
    audit.add_argument("--output-dir", type=Path, default=SCRIPT_DIR)
    audit.add_argument("--offline", action="store_true", help="只输出已验证的数据集目录，不联网")
    audit.add_argument("--timeout", type=int, default=20)
    audit.add_argument("--delay", type=float, default=1.5)

    crawl = subparsers.add_parser("crawl", help="启动 Edge 登录会话并直接采集查询结果")
    crawl.add_argument("--output", type=Path, default=SCRIPT_DIR / "health_statistics.csv")
    crawl.add_argument("--profile-dir", type=Path, default=SCRIPT_DIR / ".edge_profile")
    crawl.add_argument("--delay", type=float, default=1.5)

    normalize = subparsers.add_parser("normalize", help="标准化从网站合法导出的 CSV")
    normalize.add_argument("--manifest", type=Path, default=SCRIPT_DIR / "manifest.csv")
    normalize.add_argument("--output", type=Path, default=SCRIPT_DIR / "health_statistics.csv")

    reparse = subparsers.add_parser("reparse", help="从已有诊断文件重新生成干净 CSV，无需重新登录")
    reparse.add_argument("--diagnostics", type=Path, default=SCRIPT_DIR / "crawl_diagnostics.json")
    reparse.add_argument("--output", type=Path, default=SCRIPT_DIR / "health_statistics.csv")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command is None:
            count = run_authenticated_edge_crawler(
                SCRIPT_DIR / "health_statistics.csv",
                SCRIPT_DIR / ".edge_profile",
                1.5,
            )
            return 0 if count >= 0 else 2
        if args.command == "audit":
            return audit_public_pages(args.output_dir, args.offline, args.timeout, args.delay)
        if args.command == "crawl":
            count = run_authenticated_edge_crawler(args.output, args.profile_dir, args.delay)
            return 0 if count >= 0 else 2
        if args.command == "reparse":
            count = reparse_diagnostics(args.diagnostics, args.output)
            print(f"已覆盖生成 {args.output}，共 {count} 条通过校验的指标记录")
            return 0
        count = normalize_manifest(args.manifest, args.output)
        print(f"已生成 {args.output}，共 {count} 条真实指标记录")
        return 0
    except (ValueError, FileNotFoundError, RuntimeError, PermissionError) as exc:
        if isinstance(exc, PermissionError):
            print("错误：输出 CSV 正被 Excel 或其他程序占用，请关闭文件后重新运行。", file=sys.stderr)
            return 2
        print(f"错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
