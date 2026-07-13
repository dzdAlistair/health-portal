#!/usr/bin/env python3
"""Scrape and normalize provincial medical-resource data from NBS China Data.

Running this file performs a fresh website crawl and overwrites the CSV in the
same directory. Python Playwright and Chromium are required for live crawling.

Setup once:
    pip install playwright
    python -m playwright install chromium

Run:
    python scrape_national_medical_resources.py
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


SOURCE_URL = "https://data.stats.gov.cn/dg/website/page.html#/pc/national/fsYearData"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_RAW_JSON = SCRIPT_DIR / "nbs_raw_province_medical.json"
DEFAULT_OUTPUT = SCRIPT_DIR / "national_provincial_medical_resources_2014_2023.csv"
DEFAULT_REPORT = SCRIPT_DIR / "national_provincial_medical_resources_quality_report.json"
START_YEAR = 2014
END_YEAR = 2023
UNKNOWN = "无法确认"

PROVINCES = {
    "北京市": "110000",
    "天津市": "120000",
    "河北省": "130000",
    "山西省": "140000",
    "内蒙古自治区": "150000",
    "辽宁省": "210000",
    "吉林省": "220000",
    "黑龙江省": "230000",
    "上海市": "310000",
    "江苏省": "320000",
    "浙江省": "330000",
    "安徽省": "340000",
    "福建省": "350000",
    "江西省": "360000",
    "山东省": "370000",
    "河南省": "410000",
    "湖北省": "420000",
    "湖南省": "430000",
    "广东省": "440000",
    "广西壮族自治区": "450000",
    "海南省": "460000",
    "重庆市": "500000",
    "四川省": "510000",
    "贵州省": "520000",
    "云南省": "530000",
    "西藏自治区": "540000",
    "陕西省": "610000",
    "甘肃省": "620000",
    "青海省": "630000",
    "宁夏回族自治区": "640000",
    "新疆维吾尔自治区": "650000",
}

METRICS = {
    "医疗卫生机构数 (个)": ("medical_health_institutions", 1),
    "医院数 (个)": ("hospitals", 1),
    "基层医疗卫生机构数 (个)": ("primary_healthcare_institutions", 1),
    "专业公共卫生机构数 (个)": ("specialized_public_health_institutions", 1),
    "卫生技术人员数 (万人)": ("health_technicians", 10_000),
    "执业 (助理) 医师数 (万人)": ("licensed_assistant_physicians", 10_000),
    "注册护士数 (万人)": ("registered_nurses", 10_000),
    "医疗卫生机构床位数 (万张)": ("medical_health_beds", 10_000),
    "医院床位数 (万张)": ("hospital_beds", 10_000),
    "基层医疗卫生机构床位数 (万张)": ("primary_healthcare_beds", 10_000),
    "年末常住人口 (万人)": ("permanent_population", 10_000),
}

FIELDS = [
    "record_id",
    "year",
    "province_code",
    "province",
    "medical_health_institutions",
    "hospitals",
    "primary_healthcare_institutions",
    "specialized_public_health_institutions",
    "medical_health_beds",
    "hospital_beds",
    "primary_healthcare_beds",
    "health_technicians",
    "licensed_assistant_physicians",
    "registered_nurses",
    "permanent_population",
    "beds_per_1000_people",
    "physicians_per_1000_people",
    "nurses_per_1000_people",
    "institutions_per_10000_people",
    "hospital_beds_share",
    "primary_institution_share",
    "source",
    "update_date",
]


def parse_number(value: str, multiplier: int) -> int | None:
    text = value.strip().replace(",", "")
    if not text or text in {"-", "--", "..."}:
        return None
    number = float(text)
    return int(round(number * multiplier))


def safe_rate(numerator: int | None, denominator: int | None, scale: int) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return round(numerator / denominator * scale, 4)


def normalize_snapshot(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    rows_by_key: dict[tuple[str, int], dict[str, Any]] = {}

    for province_table in snapshot["data"]:
        province = province_table["province"]
        if province not in PROVINCES:
            raise ValueError(f"Unexpected province in source data: {province}")

        headers = province_table["headers"]
        years = [int(match.group(1)) for header in headers[1:] if (match := re.fullmatch(r"(\d{4})年", header))]
        if not years:
            raise ValueError(f"No year headers found for {province}")

        metric_values: dict[str, dict[int, int | None]] = {}
        for source_row in province_table["rows"]:
            if not source_row:
                continue
            metric_name = source_row[0]
            if metric_name not in METRICS:
                continue
            field_name, multiplier = METRICS[metric_name]
            raw_values = source_row[1 : 1 + len(years)]
            raw_values += [""] * (len(years) - len(raw_values))
            metric_values[field_name] = {
                year: parse_number(raw, multiplier)
                for year, raw in zip(years, raw_values, strict=True)
            }

        missing_metrics = sorted(set(field for field, _ in METRICS.values()) - set(metric_values))
        if missing_metrics:
            raise ValueError(f"Missing metrics for {province}: {', '.join(missing_metrics)}")

        for year in range(START_YEAR, END_YEAR + 1):
            row: dict[str, Any] = {
                "record_id": f"CN-{PROVINCES[province]}-{year}",
                "year": year,
                "province_code": PROVINCES[province],
                "province": province,
            }
            for field_name in (field for field, _ in METRICS.values()):
                row[field_name] = metric_values[field_name].get(year)

            population = row["permanent_population"]
            row["beds_per_1000_people"] = safe_rate(row["medical_health_beds"], population, 1_000)
            row["physicians_per_1000_people"] = safe_rate(
                row["licensed_assistant_physicians"], population, 1_000
            )
            row["nurses_per_1000_people"] = safe_rate(row["registered_nurses"], population, 1_000)
            row["institutions_per_10000_people"] = safe_rate(
                row["medical_health_institutions"], population, 10_000
            )
            row["hospital_beds_share"] = safe_rate(
                row["hospital_beds"], row["medical_health_beds"], 1
            )
            row["primary_institution_share"] = safe_rate(
                row["primary_healthcare_institutions"], row["medical_health_institutions"], 1
            )
            row["source"] = SOURCE_URL
            row["update_date"] = date.today().isoformat()
            rows_by_key[(province, year)] = row

    return [
        rows_by_key[(province, year)]
        for province in PROVINCES
        for year in range(START_YEAR, END_YEAR + 1)
    ]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: UNKNOWN if row[field] is None else row[field] for field in FIELDS})


def validate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    expected_rows = len(PROVINCES) * (END_YEAR - START_YEAR + 1)
    ids = [row["record_id"] for row in rows]
    errors: list[str] = []
    if len(rows) != expected_rows:
        errors.append(f"expected {expected_rows} rows, found {len(rows)}")
    if len(ids) != len(set(ids)):
        errors.append("duplicate record_id")

    for row in rows:
        for field in (
            "medical_health_institutions",
            "hospitals",
            "primary_healthcare_institutions",
            "medical_health_beds",
            "health_technicians",
            "permanent_population",
        ):
            value = row[field]
            if value is not None and (not isinstance(value, int) or value < 0):
                errors.append(f"invalid {field} in {row['record_id']}: {value}")
        for field in ("hospital_beds_share", "primary_institution_share"):
            value = row[field]
            if value is not None and not (0 <= value <= 1):
                errors.append(f"out-of-range {field} in {row['record_id']}: {value}")

    missing_counts = {
        field: sum(row[field] is None for row in rows)
        for field in FIELDS
        if field not in {"source", "update_date"}
    }
    return {
        "row_count": len(rows),
        "expected_row_count": expected_rows,
        "province_count": len({row["province"] for row in rows}),
        "year_min": min(row["year"] for row in rows),
        "year_max": max(row["year"] for row in rows),
        "missing_counts": missing_counts,
        "errors": errors,
    }


def capture_with_playwright(path: Path, headed: bool) -> None:
    try:
        from playwright.sync_api import Page, sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Python Playwright is required for live crawling. Install it with "
            "'pip install playwright' and then run 'playwright install chromium'."
        ) from exc

    metric_groups = {
        "医疗卫生机构": [
            "医疗卫生机构数 (个)",
            "医院数 (个)",
            "基层医疗卫生机构数 (个)",
            "专业公共卫生机构数 (个)",
        ],
        "卫生人员": [
            "卫生技术人员数 (万人)",
            "执业 (助理) 医师数 (万人)",
            "注册护士数 (万人)",
        ],
        "医疗卫生机构床位": [
            "医疗卫生机构床位数 (万张)",
            "医院床位数 (万张)",
            "基层医疗卫生机构床位数 (万张)",
        ],
    }

    def click_tree(page: Page, label: str) -> None:
        label_node = page.get_by_text(label, exact=True)
        candidates = label_node.locator("xpath=ancestor::*[@role='treeitem'][1]")
        if candidates.count() != 1:
            raise RuntimeError(f"Tree label is not unique: {label}")
        candidates.click()

    def select_metric(page: Page, label: str) -> None:
        candidate = page.locator("span.label").get_by_text(label, exact=True)
        if candidate.count() != 1:
            raise RuntimeError(f"Metric label is not unique: {label}")
        candidate.click()

    def extract_table(page: Page) -> dict[str, Any]:
        return page.evaluate(
            """
            () => {
              const headers = Array.from(document.querySelectorAll('table.el-table__header')[0].querySelectorAll('th'))
                .map(x => (x.textContent || '').trim());
              const rows = Array.from(document.querySelectorAll('table.el-table__body')[0].querySelectorAll('tr'))
                .map(r => Array.from(r.querySelectorAll('td')).map(x => (x.textContent || '').trim()));
              const selects = Array.from(document.querySelectorAll('input[placeholder="请选择"]')).map(x => x.value);
              return {province: selects[0] || '', headers, rows};
            }
            """
        )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(SOURCE_URL, wait_until="domcontentloaded", timeout=60_000)
        announcement_close = page.get_by_role("button", name="×", exact=True)
        if announcement_close.count() == 1 and announcement_close.is_visible():
            announcement_close.click()
        page.get_by_text("高级查询", exact=True).wait_for(timeout=60_000)
        page.get_by_text("高级查询", exact=True).click()
        click_tree(page, "卫生")
        for group, labels in metric_groups.items():
            click_tree(page, group)
            for label in labels:
                select_metric(page, label)
        click_tree(page, "人口")
        click_tree(page, "总人口")
        select_metric(page, "年末常住人口 (万人)")

        page.get_by_role("tab", name="地区", exact=True).click()
        click_tree(page, "全部地区")
        page.get_by_text("全选", exact=True).click()
        page.get_by_text("查询数据", exact=True).click()

        selects = page.get_by_role("textbox", name="请选择", exact=True)
        if selects.count() != 2:
            raise RuntimeError(f"Expected two region/time selectors, found {selects.count()}")
        selects.nth(1).click()
        page.locator("li").get_by_text("最近15年", exact=True).click()
        page.wait_for_timeout(800)

        captured: list[dict[str, Any]] = []
        for province in PROVINCES:
            current = extract_table(page)
            if current["province"] != province:
                previous_signature = json.dumps(current["rows"], ensure_ascii=False)
                selects.nth(0).click()
                option = page.locator("li").get_by_text(province, exact=True)
                option.wait_for(state="visible", timeout=15_000)
                option.click()
                for _ in range(50):
                    time.sleep(0.2)
                    table = extract_table(page)
                    signature = json.dumps(table["rows"], ensure_ascii=False)
                    if (
                        table["province"] == province
                        and len(table["rows"]) == len(METRICS)
                        and signature != previous_signature
                    ):
                        break
                else:
                    raise RuntimeError(f"Timed out loading fresh data for {province}")
            else:
                table = current
                if len(table["rows"]) != len(METRICS):
                    raise RuntimeError(f"Incomplete table for {province}")
            captured.append(table)

        browser.close()

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "source_url": SOURCE_URL,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "data": captured,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Crawl NBS provincial medical-resource data and overwrite a CSV "
            "in this script's directory."
        )
    )
    parser.add_argument("--raw-json", type=Path, default=DEFAULT_RAW_JSON)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--from-snapshot",
        action="store_true",
        help="skip live crawling and rebuild the CSV from --raw-json",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="show the Chromium window while crawling",
    )
    args = parser.parse_args()

    if not args.from_snapshot:
        print(f"Crawling official NBS data: {SOURCE_URL}")
        capture_with_playwright(args.raw_json, args.headed)

    snapshot = json.loads(args.raw_json.read_text(encoding="utf-8"))
    rows = normalize_snapshot(snapshot)
    report = validate(rows)
    report.update(
        {
            "source_url": SOURCE_URL,
            "source_snapshot_captured_at": snapshot.get("captured_at"),
            "crawl_run_date": date.today().isoformat(),
            "year_range": f"{START_YEAR}-{END_YEAR}",
            "units": {
                "institution_fields": "count",
                "bed_fields": "beds",
                "personnel_fields": "people",
                "permanent_population": "people",
                "per_capita_fields": "count per stated population denominator",
                "share_fields": "0-1 ratio",
            },
        }
    )
    if report["errors"]:
        raise ValueError("Validation failed: " + "; ".join(report["errors"]))

    write_csv(args.output, rows)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"CSV overwritten: {args.output.resolve()}")
    print(f"Quality report overwritten: {args.report.resolve()}")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
