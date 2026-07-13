from __future__ import annotations

import csv
import hashlib
import json
import math
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
JSON_DIR = RAW_DIR / "api_json"
CLEAN_DIR = ROOT / "data" / "clean"
OUTPUT_CSV = ROOT / "weather_environment.csv"

START_DATE = "2025-07-01"
END_DATE = "2026-06-30"
SOURCE = "Open-Meteo Historical Weather API (ERA5)"
API_URL = "https://archive-api.open-meteo.com/v1/archive"

# Coordinates use each prefecture-level region's representative urban point.
REGIONS = [
    {"region": "成都市", "station": "成都", "latitude": 30.5728, "longitude": 104.0668},
    {"region": "绵阳市", "station": "绵阳", "latitude": 31.4675, "longitude": 104.6796},
    {"region": "广元市", "station": "广元", "latitude": 32.4355, "longitude": 105.8436},
    {"region": "达州市", "station": "达州", "latitude": 31.2093, "longitude": 107.4678},
    {"region": "宜宾市", "station": "宜宾", "latitude": 28.7518, "longitude": 104.6432},
    {"region": "泸州市", "station": "泸州", "latitude": 28.8717, "longitude": 105.4426},
    {"region": "攀枝花市", "station": "攀枝花", "latitude": 26.5823, "longitude": 101.7186},
    {"region": "凉山彝族自治州", "station": "西昌", "latitude": 27.8945, "longitude": 102.2644},
    {"region": "甘孜藏族自治州", "station": "康定", "latitude": 30.0507, "longitude": 101.9638},
    {"region": "雅安市", "station": "雅安", "latitude": 29.9805, "longitude": 103.0133},
]


def build_url(item: dict) -> str:
    params = urlencode(
        {
            "latitude": item["latitude"],
            "longitude": item["longitude"],
            "start_date": START_DATE,
            "end_date": END_DATE,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
            "timezone": "Asia/Shanghai",
            "wind_speed_unit": "ms",
        }
    )
    return f"{API_URL}?{params}"


def fetch_json(url: str, attempts: int = 3) -> dict:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": "HealthPortalTeachingProject/1.0 (low-frequency academic use)"
                },
            )
            with urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as error:
            last_error = error
            if attempt < attempts:
                time.sleep(2 ** (attempt - 1))
    assert last_error is not None
    raise last_error


def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def valid_values(values: list) -> list[float]:
    return [float(value) for value in values if is_number(value)]


def mean(values: list) -> float | None:
    valid = valid_values(values)
    return sum(valid) / len(valid) if valid else None


def total(values: list) -> float | None:
    valid = valid_values(values)
    return sum(valid) if valid else None


def rounded(value: float | None, digits: int) -> float | str:
    return "" if value is None else round(value, digits)


def validate_response(data: dict, region: str) -> None:
    hourly = data.get("hourly", {})
    required = [
        "time",
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "wind_speed_10m",
    ]
    for field in required:
        if not isinstance(hourly.get(field), list):
            raise ValueError(f"{region}: missing hourly.{field}")
    row_count = len(hourly["time"])
    for field in required[1:]:
        if len(hourly[field]) != row_count:
            raise ValueError(f"{region}: {field} length mismatch")
    if data.get("timezone") != "Asia/Shanghai":
        raise ValueError(f"{region}: unexpected timezone {data.get('timezone')}")


def write_csv(file_path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    # utf-8-sig lets Excel recognize Chinese text without manual encoding selection.
    with file_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    manifest: list[dict] = []
    raw_rows: list[dict] = []
    monthly_rows: list[dict] = []
    region_reports: list[dict] = []

    for index, item in enumerate(REGIONS, start=1):
        url = build_url(item)
        print(f"[{index}/{len(REGIONS)}] Fetching {item['region']} ({item['station']})", flush=True)
        data = fetch_json(url)
        validate_response(data, item["region"])

        raw_text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        filename = f"{index:02d}_{item['station']}.json"
        (JSON_DIR / filename).write_text(raw_text, encoding="utf-8")
        manifest.append(
            {
                "region": item["region"],
                "representative_station": item["station"],
                "latitude": item["latitude"],
                "longitude": item["longitude"],
                "query_url": url,
                "retrieved_at_utc": retrieved_at,
                "raw_file": f"api_json/{filename}",
                "sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
            }
        )

        groups = defaultdict(
            lambda: {"temperature": [], "humidity": [], "precipitation": [], "wind_speed": []}
        )
        missing = {"temperature": 0, "humidity": 0, "precipitation": 0, "wind_speed": 0}
        hourly = data["hourly"]

        for row_index, record_time in enumerate(hourly["time"]):
            temperature = hourly["temperature_2m"][row_index]
            humidity = hourly["relative_humidity_2m"][row_index]
            precipitation = hourly["precipitation"][row_index]
            wind_speed = hourly["wind_speed_10m"][row_index]

            for field, value in (
                ("temperature", temperature),
                ("humidity", humidity),
                ("precipitation", precipitation),
                ("wind_speed", wind_speed),
            ):
                if not is_number(value):
                    missing[field] += 1

            raw_rows.append(
                {
                    "record_time": record_time,
                    "region": item["region"],
                    "representative_station": item["station"],
                    "latitude": item["latitude"],
                    "longitude": item["longitude"],
                    "temperature": temperature,
                    "humidity": humidity,
                    "precipitation": precipitation,
                    "wind_speed": wind_speed,
                    "source": SOURCE,
                }
            )

            month = record_time[:7]
            groups[month]["temperature"].append(temperature)
            groups[month]["humidity"].append(humidity)
            groups[month]["precipitation"].append(precipitation)
            groups[month]["wind_speed"].append(wind_speed)

        for month in sorted(groups):
            group = groups[month]
            monthly_rows.append(
                {
                    "record_date": month,
                    "region": item["region"],
                    "temperature": rounded(mean(group["temperature"]), 1),
                    "humidity": rounded(mean(group["humidity"]), 1),
                    "precipitation": rounded(total(group["precipitation"]), 1),
                    "wind_speed": rounded(mean(group["wind_speed"]), 2),
                    "source": SOURCE,
                }
            )

        region_reports.append(
            {
                "region": item["region"],
                "representative_station": item["station"],
                "raw_hourly_rows": len(hourly["time"]),
                "clean_monthly_rows": len(groups),
                "missing_hourly_values": missing,
            }
        )
        if index < len(REGIONS):
            time.sleep(1)

    monthly_rows.sort(key=lambda row: (row["record_date"], row["region"]))
    raw_headers = [
        "record_time",
        "region",
        "representative_station",
        "latitude",
        "longitude",
        "temperature",
        "humidity",
        "precipitation",
        "wind_speed",
        "source",
    ]
    clean_headers = [
        "record_date",
        "region",
        "temperature",
        "humidity",
        "precipitation",
        "wind_speed",
        "source",
    ]
    write_csv(RAW_DIR / "weather_environment_hourly_raw.csv", raw_headers, raw_rows)
    # The primary deliverable is overwritten beside this script on every run.
    write_csv(OUTPUT_CSV, clean_headers, monthly_rows)
    # Keep a synchronized project-layout copy for downstream HDFS/Hive handoff.
    write_csv(CLEAN_DIR / "weather_environment.csv", clean_headers, monthly_rows)
    (RAW_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    unique_keys = {(row["record_date"], row["region"]) for row in monthly_rows}
    invalid_rows = [
        row
        for row in monthly_rows
        if not row["record_date"]
        or not row["region"]
        or not is_number(row["temperature"])
        or not -50 <= row["temperature"] <= 50
        or not is_number(row["humidity"])
        or not 0 <= row["humidity"] <= 100
        or not is_number(row["precipitation"])
        or row["precipitation"] < 0
        or not is_number(row["wind_speed"])
        or row["wind_speed"] < 0
    ]
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "period": {"start": START_DATE, "end": END_DATE},
        "source": SOURCE,
        "aggregation": {
            "temperature": "monthly mean of hourly temperature_2m (degC)",
            "humidity": "monthly mean of hourly relative_humidity_2m (%)",
            "precipitation": "monthly sum of hourly precipitation (mm)",
            "wind_speed": "monthly mean of hourly wind_speed_10m (m/s)",
        },
        "totals": {
            "regions": len(REGIONS),
            "raw_hourly_rows": len(raw_rows),
            "clean_monthly_rows": len(monthly_rows),
            "unique_region_month_keys": len(unique_keys),
            "duplicate_region_month_keys": len(monthly_rows) - len(unique_keys),
            "invalid_clean_rows": len(invalid_rows),
        },
        "regions": region_reports,
    }
    (ROOT / "quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    missing_total = {
        field: sum(item["missing_hourly_values"][field] for item in region_reports)
        for field in ("temperature", "humidity", "precipitation", "wind_speed")
    }
    report_md = f"""# 气象环境数据质量报告

- 数据范围：{START_DATE} 至 {END_DATE}
- 地区数量：{len(REGIONS)}
- 原始逐小时记录：{len(raw_rows)}
- 清洗后月度记录：{len(monthly_rows)}
- 地区-月份唯一键：{len(unique_keys)}
- 重复键：{len(monthly_rows) - len(unique_keys)}
- 无效月度记录：{len(invalid_rows)}
- 原始缺失值：temperature={missing_total['temperature']}, humidity={missing_total['humidity']}, precipitation={missing_total['precipitation']}, wind_speed={missing_total['wind_speed']}
- 数据来源：{SOURCE}

## 清洗与聚合规则

1. 按 Asia/Shanghai 时区，将逐小时记录归入 YYYY-MM 月份。
2. temperature、humidity、wind_speed 计算月平均值。
3. precipitation 计算月累计值。
4. 使用 record_date + region 检查重复，并执行数值范围检查。

## 使用限制

本数据来自 ERA5 再分析产品接口，代表给定坐标网格的估计值，不等同于中国气象站官方观测值。仅用于课程教学、统计展示和系统联调，不用于医疗因果推断。
"""
    (ROOT / "quality_report.md").write_text(report_md, encoding="utf-8")

    print(f"Done: {len(raw_rows)} hourly rows, {len(monthly_rows)} monthly rows.")
    print(f"CSV overwritten: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
