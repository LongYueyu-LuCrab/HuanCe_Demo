"""Verify the 100-order E2E batch through authorized order detail APIs."""

from __future__ import annotations

import json
import os
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from production_e2e_100 import Session


BASE_URL = "https://www.aroundtest.com"
PASSWORD = os.environ.get("LIMS_E2E_PASSWORD", "")
FIRST_NUMBER = 43
COUNT = 100
local = threading.local()


def client() -> Session:
    if not hasattr(local, "client"):
        local.client = Session(BASE_URL, "sales01", PASSWORD)
    return local.client


def fetch(index: int) -> dict:
    order_no = f"LIMS-2026-{FIRST_NUMBER + index - 1:04d}"
    return client().get(f"/api/orders/{order_no}/")["order"]


def main() -> int:
    if not PASSWORD:
        raise RuntimeError("LIMS_E2E_PASSWORD is required")
    with ThreadPoolExecutor(max_workers=10) as pool:
        orders = list(pool.map(fetch, range(1, COUNT + 1)))

    expected_numbers = {f"LIMS-2026-{number:04d}" for number in range(FIRST_NUMBER, FIRST_NUMBER + COUNT)}
    actual_numbers = {order["order_no"] for order in orders}
    if actual_numbers != expected_numbers:
        raise AssertionError(f"batch mismatch: missing={expected_numbers - actual_numbers}, extra={actual_numbers - expected_numbers}")
    if not all(order["customer"].startswith("E2E-20260912") for order in orders):
        raise AssertionError("one or more orders do not belong to the E2E batch")

    schedules = [item for order in orders for item in order.get("schedule_records", [])]
    sample_slots = [item for order in orders for item in order.get("sample_records", [])]
    samples = [item for item in sample_slots if item["sample_no"]]
    experiments = [item for order in orders for item in order.get("experiment_records", [])]
    reports = [item for order in orders for item in order.get("report_records", [])]

    route_types = sorted({item["test_type"] for item in schedules})
    experiment_statuses = sorted({item["status"] for item in experiments})
    report_types = sorted({item["report_type"] for item in reports})
    if len(route_types) != 3:
        raise AssertionError(f"expected 3 execution routes, got {route_types}")
    if not {"formal", "draft", "data_only"}.issubset(report_types):
        raise AssertionError(f"report type coverage incomplete: {report_types}")
    if len(experiment_statuses) < 3:
        raise AssertionError(f"experiment stage coverage incomplete: {experiment_statuses}")
    incomplete_samples = [
        item for item in samples if not item["actual_arrive_time"] or not item["photos"]
    ]
    if incomplete_samples:
        raise AssertionError(f"sample arrival/photo evidence is incomplete: {incomplete_samples}")
    if any(not item["has_file"] or not item["download_url"] for item in reports):
        raise AssertionError("generated report download evidence is incomplete")

    result = {
        "base_url": BASE_URL,
        "marker": "E2E-20260912",
        "created_count": len(orders),
        "first_order": min(actual_numbers),
        "last_order": max(actual_numbers),
        "order_status_counts": dict(Counter(order["status"] for order in orders)),
        "execution_route_counts": dict(Counter(item["test_type"] for item in schedules)),
        "schedule_status_counts": dict(Counter(item["schedule_status"] for item in schedules)),
        "sample_count": len(samples),
        "sample_not_arrived_slot_count": sum(not item["sample_no"] for item in sample_slots),
        "sample_photo_count": sum(len(item["photos"]) for item in samples),
        "sample_outbound_count": sum(bool(item["outbound_time"]) for item in samples),
        "experiment_status_counts": dict(Counter(item["status"] for item in experiments)),
        "experiment_result_counts": dict(Counter(item["result"] for item in experiments)),
        "report_type_counts": dict(Counter(item["report_type"] for item in reports)),
        "report_status_counts": dict(Counter(item["status"] for item in reports)),
        "generated_report_file_count": sum(bool(item["has_file"]) for item in reports),
        "all_routes_scheduled_orders": sum(order["all_routes_scheduled"] for order in orders),
        "sales_confirmed_orders": sum(order["sales_confirmed"] for order in orders),
        "verification": "passed",
    }
    output = Path("deliverables/e2e-100-result.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
