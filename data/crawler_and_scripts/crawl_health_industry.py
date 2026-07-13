#!/usr/bin/env python3
"""Collect and clean a mixed, 500-row health-industry dataset.

Official sources:
* openFDA 510(k): medical devices
* FDA Drugs@FDA: approved drugs
* FDA NDC Directory: pharmaceutical manufacturing / marketed products
* ClinicalTrials.gov: drug research

Both CSV files use exactly the Project 13 nine-column contract.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import logging
import random
import re
import sys
import time
import unicodedata
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


DEVICE_API = "https://api.fda.gov/device/510k.json"
DRUG_API = "https://api.fda.gov/drug/drugsfda.json"
NDC_API = "https://api.fda.gov/drug/ndc.json"
TRIAL_API = "https://clinicaltrials.gov/api/v2/studies"
USER_AGENT = (
    "Project13-HealthPortal-Teaching/2.0 "
    "(educational public-data collection; contact: project13@example.invalid)"
)
CSV_HEADERS = [
    "industry_id",
    "industry_type",
    "product_name",
    "category",
    "registrant_region",
    "approval_date",
    "status",
    "source",
    "source_url",
]
REQUIRED_FIELDS = {
    "industry_id",
    "industry_type",
    "product_name",
    "category",
    "approval_date",
    "status",
    "source",
    "source_url",
}
RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}

DEVICE_CATEGORY_GROUPS = {
    "General, Plastic Surgery": "外科与综合医疗",
    "General Hospital": "外科与综合医疗",
    "Anesthesiology": "外科与综合医疗",
    "Clinical Chemistry": "医学检验与诊断",
    "Microbiology": "医学检验与诊断",
    "Hematology": "医学检验与诊断",
    "Immunology": "医学检验与诊断",
    "Clinical Toxicology": "医学检验与诊断",
    "Orthopedic": "骨科与康复",
    "Physical Medicine": "骨科与康复",
    "Cardiovascular": "心脑血管",
    "Neurology": "心脑血管",
    "Radiology": "医学影像",
    "Dental": "口腔医疗",
    "Gastroenterology, Urology": "消化与泌尿",
    "Ophthalmic": "眼耳鼻喉",
    "Ear, Nose, Throat": "眼耳鼻喉",
    "Unknown": "其他或未知",
    "Obstetrics/Gynecology": "妇产科",
}

TRIAL_STATUS = {
    "NOT_YET_RECRUITING": "尚未招募",
    "RECRUITING": "招募中",
    "ENROLLING_BY_INVITATION": "邀请招募",
    "ACTIVE_NOT_RECRUITING": "进行中（不再招募）",
    "SUSPENDED": "已暂停",
    "TERMINATED": "已终止",
    "COMPLETED": "已完成",
    "WITHDRAWN": "已撤回",
    "UNKNOWN": "状态未知",
}


def parse_args() -> argparse.Namespace:
    base_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="采集四类共 500 条健康产业数据。")
    parser.add_argument("--max-records", type=int, default=500)
    parser.add_argument("--device-records", type=int, default=150)
    parser.add_argument("--drug-records", type=int, default=150)
    parser.add_argument("--manufacturing-records", type=int, default=100)
    parser.add_argument("--research-records", type=int, default=100)
    parser.add_argument("--page-size", type=int, default=200)
    parser.add_argument("--delay", type=float, default=0.6)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--refresh", action="store_true", help="忽略四个本地源缓存。")
    parser.add_argument("--output-dir", type=Path, default=base_dir)
    args = parser.parse_args()

    quotas = (
        args.device_records,
        args.drug_records,
        args.manufacturing_records,
        args.research_records,
    )
    if not 1 <= args.max_records <= 500:
        parser.error("--max-records 必须在 1 到 500 之间。")
    if any(value < 0 for value in quotas):
        parser.error("各产业类型数量不能为负数。")
    if sum(quotas) != args.max_records:
        parser.error("四类数量之和必须等于 --max-records。")
    if not 1 <= args.page_size <= 500:
        parser.error("--page-size 必须在 1 到 500 之间。")
    if args.delay < 0.2:
        parser.error("--delay 不得小于 0.2 秒。")
    return args


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", "" if value is None else str(value))
    return re.sub(r"\s+", " ", text).strip()


def request_json(url: str, timeout: float, max_retries: int) -> dict[str, Any]:
    """Request public JSON with bounded, access-rule-respecting retries."""
    for attempt in range(max_retries + 1):
        request = Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read()
                if response.headers.get("Content-Encoding", "").lower() == "gzip":
                    body = gzip.decompress(body)
                return json.loads(body.decode("utf-8"))
        except HTTPError as exc:
            if exc.code in {401, 403}:
                raise RuntimeError(
                    f"官方接口拒绝访问（HTTP {exc.code}）；程序不会绕过访问限制。"
                ) from exc
            if exc.code not in RETRYABLE_HTTP_CODES or attempt >= max_retries:
                raise RuntimeError(f"请求失败：HTTP {exc.code}，URL={url}") from exc
            retry_after = exc.headers.get("Retry-After")
            wait = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt >= max_retries:
                raise RuntimeError(f"请求或 JSON 解析失败：{exc}") from exc
            wait = 2**attempt

        wait += random.uniform(0.1, 0.8)
        logging.warning("请求暂时失败，%.1f 秒后进行第 %d 次重试。", wait, attempt + 1)
        time.sleep(wait)
    raise AssertionError("unreachable")


def first_value(values: Any, key: str = "") -> str:
    if not isinstance(values, list) or not values:
        return ""
    value = values[0]
    if key and isinstance(value, dict):
        value = value.get(key, "")
    return normalize_text(value)


def normalize_date(value: Any) -> str:
    text = normalize_text(value)
    patterns = (
        ("%Y-%m-%d", text),
        ("%Y%m%d", text),
        ("%Y-%m", f"{text}-01"),
        ("%Y", f"{text}-01-01"),
    )
    for pattern, candidate in patterns:
        try:
            parsed = datetime.strptime(candidate, pattern).date()
            if 1900 <= parsed.year <= date.today().year + 5:
                return parsed.isoformat()
        except ValueError:
            continue
    return ""


def record_is_complete(row: dict[str, str]) -> bool:
    return all(normalize_text(row.get(field)) for field in REQUIRED_FIELDS)


def map_device(record: dict[str, Any]) -> list[dict[str, str]]:
    k_number = normalize_text(record.get("k_number"))
    specialty = normalize_text(record.get("advisory_committee_description")) or "Unknown"
    product_code = normalize_text(record.get("product_code"))
    category = f"{specialty} ({product_code})" if product_code else specialty
    region = " / ".join(
        value
        for value in (
            normalize_text(record.get("country_code")),
            normalize_text(record.get("state")),
            normalize_text(record.get("city")),
        )
        if value
    ) or "未公开"
    return [{
        "industry_id": f"DEV-{k_number}",
        "industry_type": "医疗器械",
        "product_name": normalize_text(record.get("device_name")),
        "category": category,
        "registrant_region": region,
        "approval_date": normalize_date(record.get("decision_date")),
        "status": normalize_text(record.get("decision_description")) or "Unknown",
        "source": "美国食品药品监督管理局 openFDA 510(k)",
        "source_url": (
            "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/"
            f"pmn.cfm?ID={quote(k_number)}"
        ),
    }]


def drug_approval_date(record: dict[str, Any]) -> str:
    submissions = record.get("submissions") or []
    approved = [
        normalize_date(item.get("submission_status_date"))
        for item in submissions
        if normalize_text(item.get("submission_status")).upper() == "AP"
    ]
    approved = [value for value in approved if value]
    return min(approved) if approved else ""


def map_drug(record: dict[str, Any]) -> list[dict[str, str]]:
    application = normalize_text(record.get("application_number")).upper()
    approval_date = drug_approval_date(record)
    if not application or not approval_date:
        return []
    application_digits = "".join(re.findall(r"\d+", application))
    rows: list[dict[str, str]] = []
    for product in record.get("products") or []:
        product_number = normalize_text(product.get("product_number")) or "001"
        brand = normalize_text(product.get("brand_name"))
        ingredient = first_value(product.get("active_ingredients"), "name")
        product_name = brand or ingredient
        dosage = normalize_text(product.get("dosage_form"))
        route = normalize_text(product.get("route"))
        category = " / ".join(value for value in (application, dosage, route) if value)
        rows.append({
            "industry_id": f"DRUG-{application}-{product_number}",
        "industry_type": "药品制造",
            "product_name": product_name,
            "category": category,
            "registrant_region": "未公开",
            "approval_date": approval_date,
            "status": normalize_text(product.get("marketing_status")) or "Unknown",
            "source": "美国食品药品监督管理局 Drugs@FDA",
            "source_url": (
                "https://www.accessdata.fda.gov/scripts/cder/daf/"
                f"index.cfm?event=overview.process&ApplNo={quote(application_digits)}"
            ),
        })
    return rows


def map_manufacturing(record: dict[str, Any]) -> list[dict[str, str]]:
    product_ndc = normalize_text(record.get("product_ndc"))
    product_type = normalize_text(record.get("product_type")) or "Unknown"
    marketing_category = normalize_text(record.get("marketing_category"))
    expiry = normalize_date(record.get("listing_expiration_date"))
    status = f"有效至 {expiry}" if expiry and expiry >= date.today().isoformat() else "目录已过期"
    api_link = f'{NDC_API}?{urlencode({"search": f"product_ndc:\"{product_ndc}\"", "limit": 1})}'
    return [{
        "industry_id": f"MFG-{product_ndc}",
        "industry_type": "药品制造",
        "product_name": normalize_text(record.get("brand_name")) or normalize_text(record.get("generic_name")),
        "category": " / ".join(value for value in (product_type, marketing_category) if value),
        "registrant_region": "未公开",
        "approval_date": normalize_date(record.get("marketing_start_date")),
        "status": status,
        "source": "美国食品药品监督管理局 NDC Directory",
        "source_url": api_link,
    }]


def map_trial(study: dict[str, Any]) -> list[dict[str, str]]:
    protocol = study.get("protocolSection") or {}
    identification = protocol.get("identificationModule") or {}
    status_module = protocol.get("statusModule") or {}
    design = protocol.get("designModule") or {}
    interventions = (protocol.get("armsInterventionsModule") or {}).get("interventions") or []
    drug_interventions = [
        normalize_text(item.get("name"))
        for item in interventions
        if normalize_text(item.get("type")).upper() in {"DRUG", "BIOLOGICAL"}
        and normalize_text(item.get("name"))
    ]
    nct_id = normalize_text(identification.get("nctId")).upper()
    product_name = "；".join(dict.fromkeys(drug_interventions[:3]))
    phases = [normalize_text(value).upper() for value in design.get("phases") or []]
    locations = (protocol.get("contactsLocationsModule") or {}).get("locations") or []
    countries = list(dict.fromkeys(
        normalize_text(item.get("country")) for item in locations if normalize_text(item.get("country"))
    ))
    region = " / ".join(countries[:3]) or "未公开"
    start_date = normalize_date((status_module.get("startDateStruct") or {}).get("date"))
    return [{
        "industry_id": f"RND-{nct_id}",
        "industry_type": "药品研发",
        "product_name": product_name,
        "category": " / ".join(phases) if phases else "NA",
        "registrant_region": region,
        "approval_date": start_date,
        "status": normalize_text(status_module.get("overallStatus")) or "UNKNOWN",
        "source": "美国 ClinicalTrials.gov",
        "source_url": f"https://clinicaltrials.gov/study/{quote(nct_id)}",
    }]


Mapper = Callable[[dict[str, Any]], list[dict[str, str]]]


def collect_openfda(
    endpoint: str,
    quota: int,
    mapper: Mapper,
    args: argparse.Namespace,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    skip = 0
    while len(rows) < quota:
        limit = min(args.page_size, 500)
        url = f"{endpoint}?{urlencode({'limit': limit, 'skip': skip})}"
        payload = request_json(url, args.timeout, args.max_retries)
        results = payload.get("results") or []
        if not results:
            break
        for record in results:
            for row in mapper(record):
                identity = row.get("industry_id", "")
                if identity and identity not in seen and record_is_complete(row):
                    seen.add(identity)
                    rows.append(row)
                    if len(rows) >= quota:
                        break
            if len(rows) >= quota:
                break
        skip += len(results)
        if len(results) < limit:
            break
        if len(rows) < quota:
            time.sleep(args.delay + random.uniform(0.0, 0.3))
    if len(rows) < quota:
        raise RuntimeError(f"{endpoint} 仅获得 {len(rows)}/{quota} 条完整记录。")
    return rows[:quota]


def collect_trials(quota: int, args: argparse.Namespace) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    next_page_token = ""
    while len(rows) < quota:
        params = {
            "query.term": "AREA[InterventionType]DRUG OR AREA[InterventionType]BIOLOGICAL",
            "pageSize": min(args.page_size, 500),
            "format": "json",
        }
        if next_page_token:
            params["pageToken"] = next_page_token
        payload = request_json(f"{TRIAL_API}?{urlencode(params)}", args.timeout, args.max_retries)
        studies = payload.get("studies") or []
        for study in studies:
            for row in map_trial(study):
                identity = row.get("industry_id", "")
                if identity and identity not in seen and record_is_complete(row):
                    seen.add(identity)
                    rows.append(row)
                    if len(rows) >= quota:
                        break
            if len(rows) >= quota:
                break
        next_page_token = normalize_text(payload.get("nextPageToken"))
        if len(rows) >= quota or not next_page_token:
            break
        time.sleep(args.delay + random.uniform(0.0, 0.3))
    if len(rows) < quota:
        raise RuntimeError(f"ClinicalTrials.gov 仅获得 {len(rows)}/{quota} 条完整记录。")
    return rows[:quota]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def load_or_collect(
    cache_path: Path,
    quota: int,
    collector: Callable[[], list[dict[str, str]]],
    refresh: bool,
) -> tuple[list[dict[str, str]], bool]:
    if cache_path.exists() and not refresh:
        with cache_path.open("r", encoding="utf-8") as handle:
            cache = json.load(handle)
        cached_rows = cache.get("records") or []
        if len(cached_rows) >= quota:
            logging.info("使用缓存：%s", cache_path.name)
            return cached_rows[:quota], True
    rows = collector()
    write_json(cache_path, {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(rows),
        "records": rows,
    })
    return rows, False


def clean_device_category(value: str) -> str:
    specialty = re.sub(r"\s*\([^()]+\)\s*$", "", normalize_text(value)).strip()
    return DEVICE_CATEGORY_GROUPS.get(specialty, "其他或未知")


def clean_drug_category(value: str) -> str:
    application = normalize_text(value).split(" / ", 1)[0].upper()
    if application.startswith("ANDA"):
        return "获批仿制药"
    if application.startswith("NDA"):
        return "获批新药"
    if application.startswith("BLA"):
        return "获批生物制品"
    return "获批其他药品"


def clean_manufacturing_category(value: str) -> str:
    upper = normalize_text(value).upper()
    if "BULK" in upper or "INGREDIENT" in upper:
        return "原料药制造"
    if "BIOLOG" in upper or "VACCINE" in upper or "PLASMA" in upper:
        return "生物制品制造"
    if "OTC" in upper:
        return "非处方药制造"
    if "PRESCRIPTION" in upper:
        return "处方药制造"
    return "其他药品制造"


def clean_research_category(value: str) -> str:
    phases = set(normalize_text(value).upper().split(" / "))
    if "PHASE4" in phases:
        return "四期临床"
    if "PHASE3" in phases:
        return "三期临床"
    if "PHASE2" in phases:
        return "二期临床"
    if phases & {"PHASE1", "EARLY_PHASE1"}:
        return "一期临床"
    return "未分期研发"


def clean_status(industry_type: str, value: str, source: str) -> str:
    original = normalize_text(value)
    lowered = original.lower()
    if industry_type == "医疗器械":
        if "not substantially equivalent" in lowered:
            return "未通过"
        if "substantially equivalent" in lowered:
            return "有效"
        if "withdraw" in lowered:
            return "已撤回"
        if "delete" in lowered or "rescind" in lowered:
            return "已撤销"
    elif industry_type == "药品制造":
        if "Drugs@FDA" in source:
            if "discontinued" in lowered:
                return "已停产"
            if "tentative" in lowered:
                return "暂定批准"
            if "prescription" in lowered or "over-the-counter" in lowered:
                return "有效"
        if "NDC Directory" in source:
            return "已过期" if "过期" in original else "有效"
    elif industry_type == "药品研发":
        return TRIAL_STATUS.get(original.upper(), "状态未知")
    return "其他"


def clean_rows(raw_rows: Iterable[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, int]]:
    cleaned: list[dict[str, str]] = []
    seen: set[str] = set()
    duplicates = 0
    invalid_dates = 0
    dropped = 0
    for raw in raw_rows:
        row = {header: normalize_text(raw.get(header)) for header in CSV_HEADERS}
        row["industry_id"] = row["industry_id"].upper()
        normalized_date = normalize_date(row["approval_date"])
        if row["approval_date"] and not normalized_date:
            invalid_dates += 1
        row["approval_date"] = normalized_date
        industry_type = row["industry_type"]
        if industry_type == "医疗器械":
            row["category"] = clean_device_category(row["category"])
        elif industry_type == "药品制造":
            if "Drugs@FDA" in row["source"]:
                row["category"] = clean_drug_category(row["category"])
            else:
                row["category"] = clean_manufacturing_category(row["category"])
        elif industry_type == "药品研发":
            row["category"] = clean_research_category(row["category"])
        row["status"] = clean_status(industry_type, row["status"], row["source"])

        if row["industry_id"] in seen:
            duplicates += 1
            continue
        if not record_is_complete(row):
            dropped += 1
            continue
        seen.add(row["industry_id"])
        cleaned.append(row)
    cleaned.sort(key=lambda row: (row["industry_type"], row["approval_date"], row["industry_id"]))
    return cleaned, {
        "duplicates_removed": duplicates,
        "invalid_dates": invalid_dates,
        "rows_dropped_missing_required": dropped,
    }


def write_csv(path: Path, rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_HEADERS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def missing_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    return {
        header: sum(1 for row in rows if not normalize_text(row.get(header)))
        for header in CSV_HEADERS
    }


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    output_dir = args.output_dir.resolve()
    raw_dir = output_dir / "data" / "raw"
    clean_dir = output_dir / "data" / "clean"
    cache_dir = raw_dir / "source_cache"
    report_dir = output_dir / "reports"

    devices, device_cache = load_or_collect(
        cache_dir / "openfda_510k.json",
        args.device_records,
        lambda: collect_openfda(DEVICE_API, args.device_records, map_device, args),
        args.refresh,
    )
    drugs, drug_cache = load_or_collect(
        cache_dir / "openfda_drugsfda.json",
        args.drug_records,
        lambda: collect_openfda(DRUG_API, args.drug_records, map_drug, args),
        args.refresh,
    )
    manufacturing, manufacturing_cache = load_or_collect(
        cache_dir / "openfda_ndc.json",
        args.manufacturing_records,
        lambda: collect_openfda(NDC_API, args.manufacturing_records, map_manufacturing, args),
        args.refresh,
    )
    research, research_cache = load_or_collect(
        cache_dir / "clinicaltrials_drug_research.json",
        args.research_records,
        lambda: collect_trials(args.research_records, args),
        args.refresh,
    )

    raw_rows = [
        {header: normalize_text(row.get(header)) for header in CSV_HEADERS}
        for row in (devices + drugs + manufacturing + research)
    ]
    for row in raw_rows:
        if row["industry_type"] in {"药品", "医药制造"}:
            row["industry_type"] = "药品制造"
    clean_records, clean_metrics = clean_rows(raw_rows)
    raw_csv = raw_dir / "health_industry.csv"
    clean_csv = clean_dir / "health_industry.csv"
    report_path = report_dir / "health_industry_quality_report.json"
    write_csv(raw_csv, raw_rows)
    write_csv(clean_csv, clean_records)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requested_max_records": args.max_records,
        "raw_row_count": len(raw_rows),
        "clean_row_count": len(clean_records),
        "csv_headers": CSV_HEADERS,
        "source_cache_used": {
            "医疗器械": device_cache,
            "药品制造（获批记录）": drug_cache,
            "药品制造（生产上市目录）": manufacturing_cache,
            "药品研发": research_cache,
        },
        "raw_industry_type_distribution": dict(Counter(row["industry_type"] for row in raw_rows)),
        "clean_industry_type_distribution": dict(Counter(row["industry_type"] for row in clean_records)),
        "clean_category_distribution": dict(Counter(row["category"] for row in clean_records)),
        "clean_status_distribution": dict(Counter(row["status"] for row in clean_records)),
        "raw_missing_by_column": missing_counts(raw_rows),
        "clean_missing_by_column": missing_counts(clean_records),
        "cleaning_metrics": clean_metrics,
        "region_not_public_count": sum(
            1 for row in clean_records if row["registrant_region"] == "未公开"
        ),
        "date_semantics": {
            "医疗器械": "FDA decision_date（批准决定日期）",
            "药品制造（获批记录）": "Drugs@FDA 首次 AP submission_status_date（批准日期）",
            "药品制造（生产上市目录）": "NDC marketing_start_date（上市/统计起始日期）",
            "药品研发": "ClinicalTrials.gov startDate（研究开始日期，不是药品批准日期）",
        },
        "privacy_note": "仅保留项目约定公开字段，不保存联系人、电话或详细地址。",
        "raw_csv": str(raw_csv),
        "clean_csv": str(clean_csv),
    }
    write_json(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if len(raw_rows) != args.max_records or len(clean_records) != args.max_records:
        logging.error("输出行数未达到要求：raw=%d, clean=%d", len(raw_rows), len(clean_records))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
