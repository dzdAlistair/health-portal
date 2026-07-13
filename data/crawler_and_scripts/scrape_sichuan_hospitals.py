#!/usr/bin/env python3
"""Scrape and normalize Sichuan hospital records from an official notice.

The script first attempts to fetch the source page with Python. If outbound
network access is blocked, it falls back to an accessible-text copy of the
same official attachment captured locally from the public Office viewer.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path


SOURCE_URL = (
    "https://wsjkw.sc.gov.cn/scwsjkw/gggs/2022/8/4/"
    "102c243368424b3fa16d977239f3eff4.shtml"
)
SOURCE_DATE = "2022-08-04"
UNKNOWN = "无法确认"

FIELDS = [
    "institution_id",
    "institution_name",
    "region",
    "institution_type",
    "institution_level",
    "approved_beds",
    "open_beds",
    "clinical_departments",
    "ct_available",
    "mri_available",
    "dsa_available",
    "source",
    "update_date",
]

# The official attachment groups consecutive records by city/prefecture.
REGION_BY_ROW = {
    **dict.fromkeys(range(1, 13), "成都"),
    13: "自贡",
    14: "攀枝花",
    **dict.fromkeys(range(15, 18), "泸州"),
    **dict.fromkeys(range(18, 22), "德阳"),
    **dict.fromkeys(range(22, 26), "绵阳"),
    **dict.fromkeys(range(26, 28), "广元"),
    28: "遂宁",
    **dict.fromkeys(range(29, 34), "内江"),
    34: "乐山",
    **dict.fromkeys(range(35, 37), "南充"),
    37: "广安",
    38: "巴中",
    39: "雅安",
    **dict.fromkeys(range(40, 42), "资阳"),
    **dict.fromkeys(range(42, 44), "阿坝"),
    44: "甘孜",
}

SPECIAL_NAME_FIXES = {
    22: "四川绵阳四〇四医院",
    25: "九〇三医院",
    32: "资中县人民医院",
}


def fetch_with_python(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "health-portal-course-project/1.0 (+educational-use)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        encoding = response.headers.get_content_charset() or "utf-8"
        return body.decode(encoding, errors="replace")


def normalize_tokens(text: str) -> list[str]:
    return [re.sub(r"\s+", "", line) for line in text.splitlines() if line.strip()]


def parse_official_attachment(text: str) -> list[dict[str, str]]:
    marker = "年度三级医院复审名单"
    marker_pos = text.find(marker)
    if marker_pos < 0:
        raise ValueError(f"Official list marker not found: {marker}")

    tokens = normalize_tokens(text[marker_pos:])
    expected = 1
    current_parts: list[str] = []
    parsed: list[tuple[int, list[str], str]] = []

    for token in tokens:
        if expected > 44:
            break
        if not current_parts:
            if token == str(expected):
                current_parts = [token]
            continue

        if token in {"甲等", "乙等"}:
            parsed.append((expected, current_parts[1:], token))
            expected += 1
            current_parts = []
            continue

        if token not in {"序号", "市（州）", "机构", "等次"}:
            current_parts.append(token)

    if len(parsed) != 44:
        raise ValueError(f"Expected 44 rows, parsed {len(parsed)}")

    rows: list[dict[str, str]] = []
    for row_number, parts, _grade in parsed:
        if row_number in SPECIAL_NAME_FIXES:
            name = SPECIAL_NAME_FIXES[row_number]
        else:
            hospital_parts = [part for part in parts if "医院" in part]
            if not hospital_parts:
                raise ValueError(f"Hospital name missing in row {row_number}: {parts}")
            name = hospital_parts[-1]

        rows.append(
            {
                "institution_id": f"SC-HOSP-{row_number:03d}",
                "institution_name": name,
                "region": REGION_BY_ROW[row_number],
                "institution_type": "综合医院",
                "institution_level": "三级",
                "approved_beds": UNKNOWN,
                "open_beds": UNKNOWN,
                "clinical_departments": UNKNOWN,
                "ct_available": UNKNOWN,
                "mri_available": UNKNOWN,
                "dsa_available": UNKNOWN,
                "source": SOURCE_URL,
                "update_date": SOURCE_DATE,
            }
        )
    return rows


def validate(rows: list[dict[str, str]]) -> dict[str, object]:
    ids = [row["institution_id"] for row in rows]
    names = [row["institution_name"] for row in rows]
    errors: list[str] = []
    if len(ids) != len(set(ids)):
        errors.append("duplicate institution_id")
    if len(names) != len(set(names)):
        errors.append("duplicate institution_name")
    for index, row in enumerate(rows, start=1):
        missing = [field for field in FIELDS if not row.get(field)]
        if missing:
            errors.append(f"row {index} missing fields: {','.join(missing)}")
        if row["institution_level"] not in {"一级", "二级", "三级", "其他"}:
            errors.append(f"row {index} invalid institution_level")
        for field in ("ct_available", "mri_available", "dsa_available"):
            if row[field] not in {"有", "无", UNKNOWN}:
                errors.append(f"row {index} invalid {field}")
    return {
        "row_count": len(rows),
        "unique_regions": sorted({row["region"] for row in rows}),
        "unknown_counts": {
            field: sum(row[field] == UNKNOWN for row in rows)
            for field in (
                "approved_beds",
                "open_beds",
                "clinical_departments",
                "ct_available",
                "mri_available",
                "dsa_available",
            )
        },
        "errors": errors,
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-text", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--raw-html", type=Path)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()

    acquisition = "python-http"
    network_error = None
    try:
        time.sleep(max(args.delay, 0.0))
        html = fetch_with_python(SOURCE_URL)
        if args.raw_html:
            args.raw_html.parent.mkdir(parents=True, exist_ok=True)
            args.raw_html.write_text(html, encoding="utf-8")
        # The official list is in an attached Word file, so the accessible
        # attachment text remains the authoritative parsing input.
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        acquisition = "browser-captured-official-attachment"
        network_error = f"{type(exc).__name__}: {exc}"

    source_text = args.input_text.read_text(encoding="utf-8")
    rows = parse_official_attachment(source_text)
    report = validate(rows)
    report.update(
        {
            "source_url": SOURCE_URL,
            "source_publication_date": SOURCE_DATE,
            "crawl_run_date": date.today().isoformat(),
            "acquisition": acquisition,
            "python_network_error": network_error,
        }
    )
    if report["errors"]:
        raise ValueError("Validation failed: " + "; ".join(report["errors"]))

    write_csv(args.output, rows)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
