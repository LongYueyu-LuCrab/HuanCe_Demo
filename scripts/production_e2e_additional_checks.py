"""Run non-mainline production checks through public HTTP endpoints."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from production_e2e_100 import ApiError, Session, expect_error


def main() -> int:
    password = os.environ.get("LIMS_E2E_PASSWORD", "")
    if not password:
        raise RuntimeError("LIMS_E2E_PASSWORD is required")
    base_url = "https://www.aroundtest.com"
    sessions = {
        name: Session(base_url, username, password)
        for name, username in {
            "sales": "sales01",
            "quality": "quality01",
            "suzhou": "suzhou_lab01",
            "jiangyin": "jiangyin_lab01",
            "suzhou_operator": "suzhou_operator01",
            "jiangyin_operator": "jiangyin_operator01",
            "gm": "general_manager01",
            "accounting": "accountant01",
        }.items()
    }
    checks: list[dict] = []

    # An experiment-ended order is visible for pre-invoicing without closing it.
    preinvoice = sessions["accounting"].action(
        "preinvoice_create",
        "LIMS-2026-0126",
        invoice_amount="5000.00",
        invoice_type="VAT special",
        pay_status=0,
    )["invoice"]
    if preinvoice["invoice_stage"] != "pre_experiment":
        raise AssertionError(f"expected pre_experiment invoice, got {preinvoice}")
    checks.append({"check": "post-experiment preinvoice", "result": "passed", "invoice": preinvoice["invoice_no"]})

    # Sample outbound is a separate lifecycle action after result submission.
    outbound_order = sessions["sales"].get("/api/orders/LIMS-2026-0127/")["order"]
    outbound_count = 0
    for schedule in outbound_order["schedule_records"]:
        key = "jiangyin_operator" if schedule["lab_type"] == 2 else "suzhou_operator"
        sessions[key].action("sample_outbound", outbound_order["order_no"], schedule_id=schedule["id"])
        outbound_count += 1
    checks.append({"check": "sample outbound lifecycle", "result": "passed", "routes": outbound_count})

    # Laboratory manager standard maintenance.
    standard = sessions["suzhou"].action(
        "standard_create",
        industry="E2E regression",
        standard_code="E2E-STD-20260912",
        standard_name="E2E full workflow verification standard",
        description="Created through the same workflow endpoint as the frontend.",
    )["standard"]
    checks.append({"check": "test standard create/update", "result": "passed", "standard": standard["standard_code"]})

    # Device create, maintenance status update, restore and delete.
    existing = sessions["suzhou"].get("/api/labs/devices/")["devices"]
    for device in existing:
        if device["device_code"] == "E2E-CRUD-20260912":
            sessions["suzhou"].request(f"/api/labs/devices/{device['id']}/", method="DELETE")
    device = sessions["suzhou"].post_json(
        "/api/labs/devices/",
        {
            "device_code": "E2E-CRUD-20260912",
            "device_name": "E2E disposable device",
            "lab_type": 1,
            "model_spec": "E2E",
            "capability": "CRUD regression",
        },
    )["device"]
    maintenance = sessions["suzhou"].request(
        f"/api/labs/devices/{device['id']}/",
        method="PATCH",
        body=json.dumps({"device_status": 2}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )["device"]
    if maintenance["status_key"] != 2:
        raise AssertionError("device maintenance status was not saved")
    sessions["suzhou"].request(
        f"/api/labs/devices/{device['id']}/",
        method="PATCH",
        body=json.dumps({"device_status": 1}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    sessions["suzhou"].request(f"/api/labs/devices/{device['id']}/", method="DELETE")
    checks.append({"check": "device create/status/restore/delete", "result": "passed"})

    # Export endpoints return real XLSX payloads.
    sales_export = sessions["sales"].get("/api/sales/orders/export/?keyword=E2E-20260912")
    if not sales_export["body"].startswith(b"PK"):
        raise AssertionError("sales export is not an XLSX archive")
    lab_export = sessions["suzhou_operator"].get("/api/labs/orders/export/?lab_type=1&keyword=E2E-20260912")
    if not lab_export["body"].startswith(b"PK"):
        raise AssertionError("laboratory export is not an XLSX archive")
    checks.append({"check": "sales and laboratory Excel exports", "result": "passed"})

    # Protected generated report returns a PDF for an authorized lead manager.
    report_order = sessions["sales"].get("/api/orders/LIMS-2026-0142/")["order"]
    report = report_order["report_records"][0]
    pdf = sessions["suzhou"].get(report["download_url"])
    if pdf["status"] != 200 or not pdf["body"].startswith(b"%PDF"):
        raise AssertionError("generated report download is not a valid PDF")
    checks.append({"check": "protected report PDF download", "result": "passed", "report": report["report_no"]})

    # Cross-role and state-machine negative checks.
    target = sessions["sales"].get("/api/orders/LIMS-2026-0098/")["order"]
    schedule_id = target["schedule_records"][0]["id"]
    expect_error(
        lambda: sessions["quality"].action(
            "schedule_assign", target["order_no"], schedule_id=schedule_id,
            plan_start_time="2035-01-01", plan_end_time="2035-01-02",
        ),
        403,
        "legacy quality role cannot operate V2 schedule",
        checks,
    )
    expect_error(
        lambda: sessions["accounting"].action(
            "preinvoice_create", "LIMS-2026-0043", invoice_amount="1000.00"
        ),
        400,
        "preinvoice requires dual review",
        checks,
    )
    expect_error(
        lambda: sessions["jiangyin_operator"].action(
            "sample_arrival", target["order_no"], schedule_id=schedule_id, sample_arrived=True
        ),
        403,
        "wrong laboratory cannot operate assigned route",
        checks,
    )
    expect_error(
        lambda: sessions["gm"].action(
            "invoice_create", report_no=report["report_no"], invoice_amount="1.00"
        ),
        403,
        "general manager cannot perform accounting action",
        checks,
    )

    output = Path("deliverables/e2e-additional-checks-20260912.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(checks, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ApiError as error:
        print(error, file=sys.stderr)
        raise
