"""Production-like LIMS V2 workflow regression through public HTTP APIs only.

The script never writes the database directly. It logs in as each configured role,
creates orders through the sales endpoint, and advances them through the same action
endpoint used by the Vue frontend.
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import uuid
from datetime import date, timedelta
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, HTTPSHandler, Request, build_opener


class ApiError(RuntimeError):
    def __init__(self, status: int, payload: dict):
        super().__init__(f"HTTP {status}: {payload.get('error') or payload}")
        self.status = status
        self.payload = payload


class Session:
    def __init__(self, base_url: str, username: str, password: str, insecure: bool = False):
        context = ssl._create_unverified_context() if insecure else ssl.create_default_context()
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()), HTTPSHandler(context=context))
        self.post_json("/api/auth/login/", {"username": username, "password": password})

    def request(self, path: str, method: str = "GET", body: bytes | None = None, headers: dict | None = None):
        for attempt in range(1, 4):
            request = Request(self.base_url + path, data=body, method=method, headers=headers or {})
            try:
                with self.opener.open(request, timeout=40) as response:
                    raw = response.read()
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        return json.loads(raw.decode("utf-8"))
                    return {"status": response.status, "content_type": content_type, "body": raw}
            except HTTPError as error:
                raw = error.read()
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    payload = {"error": raw.decode("utf-8", errors="replace")[:500]}
                raise ApiError(error.code, payload) from error
            except (URLError, TimeoutError):
                if attempt == 3:
                    raise
                time.sleep(attempt * 2)
        raise AssertionError("unreachable request retry state")

    def get(self, path: str):
        return self.request(path)

    def post_json(self, path: str, payload: dict):
        return self.request(
            path,
            method="POST",
            body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

    def post_multipart(self, path: str, fields: list[tuple[str, str]], files: list[tuple[str, str, str, bytes]]):
        boundary = "----HuanCeE2E" + uuid.uuid4().hex
        chunks: list[bytes] = []
        for name, value in fields:
            chunks.extend([
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                str(value).encode("utf-8"),
                b"\r\n",
            ])
        for name, filename, content_type, content in files:
            chunks.extend([
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode(),
                f"Content-Type: {content_type}\r\n\r\n".encode(),
                content,
                b"\r\n",
            ])
        chunks.append(f"--{boundary}--\r\n".encode())
        return self.request(
            path,
            method="POST",
            body=b"".join(chunks),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )

    def action(self, action: str, order_no: str | None = None, **payload):
        data = {"action": action, **payload}
        if order_no:
            data["order_no"] = order_no
        return self.post_json("/api/lims/action/", data)

    def action_with_photo(self, action: str, order_no: str, schedule_id: int):
        return self.post_multipart(
            "/api/lims/action/",
            [("action", action), ("order_no", order_no), ("schedule_id", str(schedule_id)), ("sample_arrived", "true")],
            [("sample_photos", f"{order_no}-sample.png", "image/png", b"\x89PNG\r\n\x1a\nE2E-SAMPLE")],
        )


def expect_error(call, status: int, label: str, checks: list[dict]):
    try:
        call()
    except ApiError as error:
        if error.status != status:
            raise AssertionError(f"{label}: expected HTTP {status}, got {error}") from error
        checks.append({"check": label, "status": error.status, "result": "passed"})
        return
    raise AssertionError(f"{label}: expected HTTP {status}, action unexpectedly succeeded")


def route_kind(index: int) -> str:
    if index in {40, 50, 60, 70, 80, 88, 90}:
        return "outsource"
    if index in {45, 55, 65, 75, 85, 95, 98, 100}:
        return "multi"
    return "suzhou" if index % 2 == 0 else "jiangyin"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://www.aroundtest.com")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--password", default=os.environ.get("LIMS_E2E_PASSWORD", ""))
    parser.add_argument("--chairman-password", default=os.environ.get("LIMS_CHAIRMAN_PASSWORD", ""))
    parser.add_argument("--insecure", action="store_true")
    parser.add_argument("--output", default="deliverables/e2e-100-result.json")
    args = parser.parse_args()
    if not args.password:
        parser.error("provide --password or LIMS_E2E_PASSWORD")

    account_names = {
        "sales": "sales01",
        "sales_manager": "sales_manager01",
        "business": "business01",
        "tech": "tech01",
        "quality": "quality01",
        "suzhou": "suzhou_lab01",
        "jiangyin": "jiangyin_lab01",
        "suzhou_operator": "suzhou_operator01",
        "jiangyin_operator": "jiangyin_operator01",
        "gm": "general_manager01",
        "accounting": "accountant01",
    }
    sessions = {
        key: Session(args.base_url, username, args.password, args.insecure)
        for key, username in account_names.items()
    }
    if args.chairman_password:
        sessions["chairman"] = Session(args.base_url, "zhihao", args.chairman_password, args.insecure)

    role_checks = {}
    for key, session in sessions.items():
        me = session.get("/api/auth/me/")
        dashboard = session.get("/api/lims/dashboard/?limit=10")
        if not me.get("authenticated") or not all(
            key in dashboard for key in ("metrics", "roles", "recent_orders")
        ):
            raise AssertionError(f"{key} login/dashboard failed")
        role_checks[key] = {"username": session.username, "roles": me.get("roles", []), "dashboard": "passed"}

    tech_dashboard = sessions["tech"].get("/api/lims/dashboard/?limit=5")
    routing = tech_dashboard["routing_options"]
    suzhou_manager = routing["suzhou_managers"][0]
    jiangyin_manager = routing["jiangyin_managers"][0]

    def normal_device(session_key: str, lab_type: int, code: str):
        devices = sessions[session_key].get("/api/labs/devices/")["devices"]
        matches = [item for item in devices if item["device_code"] == code]
        if matches:
            return matches[0]
        payload = {
            "device_code": code,
            "device_name": f"E2E {('苏州' if lab_type == 1 else '江阴')}专用测试台",
            "lab_type": lab_type,
            "model_spec": "E2E-20260912",
            "capability": "自动化全流程回归专用",
            "remark": "测试设备，请保留用于后续回归",
        }
        return sessions[session_key].post_json("/api/labs/devices/", payload)["device"]

    sz_device = normal_device("suzhou", 1, "E2E-SZ-20260912")
    jy_device = normal_device("jiangyin", 2, "E2E-JY-20260912")
    checks: list[dict] = []
    orders: list[dict] = []

    def create_order(index: int):
        kind = route_kind(index)
        attributes = ["autonomous"]
        if kind == "outsource":
            attributes = ["outsource"]
        elif kind == "multi":
            attributes = ["autonomous", "outsource"]
        fields = [
            ("customer_name", f"E2E-20260912-客户-{index:03d}"),
            ("contact_name", f"测试联系人{index:03d}"),
            ("phone", f"1390000{index:04d}"),
            ("project_name", f"E2E-20260912-流程覆盖-{kind}-{index:03d}"),
            ("test_requirements", f"第{index:03d}笔全流程回归：温湿度、振动与数据完整性验证"),
            ("test_method", "按客户技术协议执行，记录原始数据并进行结果复核"),
            ("test_standard", "GB/T 2423.10-2019"),
            ("expected_sample_arrival", "2027-01-05"),
            ("expected_delivery_date", "2028-12-31"),
            ("quoted_amount", "100000.00"),
            ("is_urgent", "true" if index % 9 == 0 else "false"),
            ("industry_category", ["automotive", "military", "other"][index % 3]),
        ]
        fields.extend(("execution_attributes", value) for value in attributes)
        files = []
        if "outsource" in attributes:
            fields.extend([
                ("outsource_company", f"E2E委外检测机构-{index:03d}"),
                ("outsource_amount", "28000.00"),
                ("entrust_order_no", f"E2E-ENTRUST-{index:03d}"),
                ("undertaking_amount", "60000.00"),
                ("outsource_experiment_start_time", "2028-01-01 09:00"),
                ("outsource_experiment_end_time", "2028-01-03 18:00"),
            ])
            files.append(("outsource_contract_files", f"E2E-{index:03d}-outsource-contract.pdf", "application/pdf", b"%PDF-1.4\nE2E OUTSOURCE CONTRACT\n%%EOF"))
        result = sessions["sales"].post_multipart("/api/orders/create/", fields, files)
        return result["order"]["order_no"], kind

    def tech_pass(order_no: str, kind: str):
        routes = [kind]
        if kind == "multi":
            routes = ["suzhou", "jiangyin", "outsource"]
        payload = {
            "execution_routes": routes,
            "suzhou_manager_id": suzhou_manager["id"],
            "jiangyin_manager_id": jiangyin_manager["id"],
            "outsource_owner_id": suzhou_manager["id"],
            "lead_lab_manager_id": suzhou_manager["id"] if kind != "jiangyin" else jiangyin_manager["id"],
            "suzhou_task": "苏州路径：温湿度与振动试验",
            "jiangyin_task": "江阴路径：机械性能与耐久试验",
            "outsource_task": "委外路径：专项环境可靠性试验",
        }
        return sessions["tech"].action("review_pass", order_no, **payload)

    def detail(order_no: str):
        return sessions["sales"].get(f"/api/orders/{order_no}/")["order"]

    def actor_for_schedule(schedule: dict, operator: bool = False):
        if schedule["lab_type"] == 2:
            return sessions["jiangyin_operator" if operator else "jiangyin"]
        return sessions["suzhou_operator" if operator else "suzhou"]

    for index in range(1, args.count + 1):
        order_no, kind = create_order(index)
        record = {"index": index, "order_no": order_no, "route": kind, "target": "pending_review"}
        orders.append(record)
        print(f"[{index:03d}/{args.count}] created {order_no} ({kind})", flush=True)

        if 11 <= index <= 15:
            sessions["business"].action("review_reject", order_no, reject_reason="E2E 商务资料驳回验证")
            record["target"] = "business_rejected"
            continue
        if 16 <= index <= 20:
            sessions["tech"].action("review_reject", order_no, reject_reason="E2E 技术可行性驳回验证")
            record["target"] = "technical_rejected"
            continue
        if 21 <= index <= 25:
            sessions["business"].action("review_reject", order_no, reject_reason="E2E 销售修改回流验证")
            if index == 25:
                sessions["sales"].action("order_cancel", order_no, reason="E2E 销售退单验证")
                record["target"] = "cancelled"
            else:
                sessions["sales"].action("order_update", order_no, project_name=f"E2E-20260912-驳回修改-{index:03d}")
                record["target"] = "resubmitted"
            continue
        if 26 <= index <= 35:
            sessions["business"].action("review_pass", order_no, biz_quote_detail="E2E 商务报价审核通过")
            record["target"] = "business_pass_waiting_technical"
            continue
        if 36 <= index <= 45:
            tech_pass(order_no, kind)
            record["target"] = "technical_pass_waiting_business"
            continue
        if index < 46:
            continue

        sessions["business"].action("review_pass", order_no, biz_quote_detail="E2E 商务报价审核通过")
        tech_pass(order_no, kind)
        record["target"] = "dual_review_passed"

        if index in {50, 98}:
            invoice = sessions["accounting"].action(
                "preinvoice_create", order_no, invoice_amount="10000.00", invoice_type="增值税专票", pay_status=0
            )["invoice"]
            record["preinvoice_no"] = invoice["invoice_no"]

        if index < 56:
            continue

        schedules = detail(order_no)["schedule_records"]
        base_day = date(2029, 1, 1) + timedelta(days=index * 5)
        for offset, schedule in enumerate(schedules):
            actor = actor_for_schedule(schedule)
            start = base_day + timedelta(days=offset)
            end = start + timedelta(days=1)
            payload = {
                "schedule_id": schedule["id"],
                "plan_start_time": start.isoformat(),
                "plan_end_time": end.isoformat(),
                "sample_arrived": False,
                "remark": f"E2E 排期任务 {index:03d}-{offset + 1}",
            }
            if schedule["test_type"] == "外部委外":
                payload.update({"outsource_factory": f"E2E委外检测机构-{index:03d}", "outsource_price": "28000", "outsource_cycle": 2})
            else:
                payload["device_id"] = sz_device["id"] if schedule["lab_type"] == 1 else jy_device["id"]
            actor.action("schedule_assign", order_no, **payload)
        record["target"] = "scheduled_waiting_sales"

        if index == 62:
            sessions["sales"].action(
                "create_change", order_no, change_scene=1,
                change_content="E2E 样品到货前增加测试条件", new_test_demand="增加低温保持试验",
            )
            for offset, schedule in enumerate(detail(order_no)["schedule_records"]):
                actor = actor_for_schedule(schedule)
                start = base_day + timedelta(days=2 + offset)
                payload = {
                    "schedule_id": schedule["id"], "plan_start_time": start.isoformat(),
                    "plan_end_time": (start + timedelta(days=1)).isoformat(), "sample_arrived": False,
                }
                if schedule["test_type"] != "外部委外":
                    payload["device_id"] = sz_device["id"] if schedule["lab_type"] == 1 else jy_device["id"]
                actor.action("process_change", order_no, **payload)
            record["target"] = "pre_sample_change_closed"

        if index < 66:
            continue
        sessions["sales"].action("sales_confirm", order_no, note="E2E 销售确认排期与需求")
        record["target"] = "sales_confirmed_waiting_sample"

        if index == 66:
            schedule = detail(order_no)["schedule_records"][0]
            expect_error(
                lambda: actor_for_schedule(schedule, operator=True).action("start_test", order_no, schedule_id=schedule["id"]),
                400,
                "sample gate blocks test start",
                checks,
            )
        if index < 71:
            continue
        for schedule in detail(order_no)["schedule_records"]:
            actor_for_schedule(schedule, operator=True).action_with_photo("sample_arrival", order_no, schedule["id"])
        record["target"] = "sample_arrived_waiting_test"

        if index < 76:
            continue
        for schedule in detail(order_no)["schedule_records"]:
            if schedule["test_type"] != "外部委外":
                actor_for_schedule(schedule, operator=True).action("start_test", order_no, schedule_id=schedule["id"])
        record["target"] = "testing"

        if index == 79:
            schedule = detail(order_no)["schedule_records"][0]
            actor = actor_for_schedule(schedule, operator=True)
            actor.action(
                "create_change", order_no, schedule_id=schedule["id"], change_scene=2,
                change_content="E2E 试验中追加振动条件", new_test_demand="追加随机振动测试",
            )
            changed_start = base_day + timedelta(days=3)
            actor.action(
                "process_change", order_no, schedule_id=schedule["id"],
                plan_start_time=changed_start.isoformat(), plan_end_time=(changed_start + timedelta(days=1)).isoformat(),
                device_id=sz_device["id"] if schedule["lab_type"] == 1 else jy_device["id"], sample_arrived=True,
            )
            sessions["sales"].action("sales_confirm", order_no, note="E2E 确认试验中变更后的排期")
            record["target"] = "in_test_change_closed"

        if index < 81:
            continue
        for schedule in detail(order_no)["schedule_records"]:
            actor = actor_for_schedule(schedule, operator=True)
            if schedule["test_type"] == "外部委外":
                actor.action(
                    "outsource_result", order_no, schedule_id=schedule["id"], result_status="pass",
                    test_raw_data=f"E2E 委外原始数据 {index:03d}", test_conclusion_temp="委外试验合格",
                )
            else:
                actor.action(
                    "end_test", order_no, schedule_id=schedule["id"], result_status="pass",
                    test_raw_data=f"E2E 原始数据 {index:03d}", test_conclusion_temp="各项指标满足要求",
                )
        record["target"] = "ended_waiting_submit"

        if index < 85:
            continue
        for schedule in detail(order_no)["schedule_records"]:
            actor_for_schedule(schedule, operator=True).action("submit_test", order_no, schedule_id=schedule["id"])
        record["target"] = "results_submitted_waiting_report"

        if index == 85:
            expect_error(
                lambda: sessions["suzhou_operator"].action("issue_report", order_no, final_conclusion="操作员越权"),
                403,
                "operator cannot issue final report",
                checks,
            )
        if index < 89:
            continue
        current = detail(order_no)
        lead = sessions["jiangyin"] if current["lead_lab_manager_username"] == "jiangyin_lab01" else sessions["suzhou"]
        issued = lead.action(
            "issue_report", order_no,
            report_type=["formal", "draft", "data_only"][index % 3],
            final_conclusion=f"E2E 第{index:03d}笔订单全部试验路径完成，综合结论合格",
        )
        report = issued["report"]
        if not report["has_file"]:
            raise AssertionError(f"{order_no}: report PDF was not generated")
        record.update({"target": "sales_report_review", "report_no": report["report_no"], "download_url": report["download_url"]})

        if index == 96:
            sessions["sales"].action("report_sales_reject", report_no=report["report_no"], audit_opinion="E2E 销售驳回重制")
            report = lead.action("issue_report", order_no, report_type="draft", final_conclusion="销售意见已修订")["report"]
            record.update({"target": "sales_reject_remade", "report_no": report["report_no"]})
            continue
        if index < 93:
            continue
        sessions["sales"].action("report_sales_pass", report_no=report["report_no"], audit_opinion="E2E 销售初审通过")
        record["target"] = "general_manager_review"

        if index == 97:
            sessions["gm"].action("report_gm_reject", report_no=report["report_no"], audit_opinion="E2E 总经理驳回重制")
            report = lead.action("issue_report", order_no, report_type="formal", final_conclusion="总经理意见已修订")["report"]
            sessions["sales"].action("report_sales_pass", report_no=report["report_no"], audit_opinion="重制后销售复审通过")
            record.update({"target": "gm_reject_remade", "report_no": report["report_no"]})
            continue
        if index < 98:
            continue
        sessions["gm"].action("report_gm_pass", report_no=report["report_no"], audit_opinion="E2E 总经理终审通过")
        final_invoice = sessions["accounting"].action(
            "invoice_create", report_no=report["report_no"], invoice_type="增值税专票", pay_status=0
        )["invoice"]
        sessions["accounting"].action("invoice_pay", invoice_no=final_invoice["invoice_no"], pay_status=1)
        record.update({"target": "closed", "final_invoice_no": final_invoice["invoice_no"]})
        if index == 100:
            sessions["accounting"].action(
                "invoice_void", invoice_no=final_invoice["invoice_no"], void_reason="E2E 最终总票作废回归验证"
            )
            record["target"] = "final_invoice_voided_reopened"

    # Cross-role access checks on one known V2 order.
    v2_order = orders[55]["order_no"]
    expect_error(
        lambda: sessions["quality"].action("schedule_assign", v2_order, plan_start_time="2035-01-01", plan_end_time="2035-01-02"),
        403,
        "legacy quality role cannot operate V2 order",
        checks,
    )
    expect_error(
        lambda: sessions["accounting"].action("preinvoice_create", orders[0]["order_no"], invoice_amount="1000"),
        400,
        "preinvoice requires dual review",
        checks,
    )

    # Verify report downloads and endpoint payloads with the authorized lead manager.
    report_order = next(item for item in orders if item.get("download_url"))
    report_detail = detail(report_order["order_no"])
    report_record = next(item for item in report_detail["report_records"] if item["report_no"] == report_order["report_no"])
    lead = sessions["jiangyin"] if report_detail["lead_lab_manager_username"] == "jiangyin_lab01" else sessions["suzhou"]
    downloaded = lead.get(report_record["download_url"])
    if downloaded["status"] != 200 or not downloaded["body"].startswith(b"%PDF"):
        raise AssertionError("protected report download did not return a valid PDF")
    checks.append({"check": "protected report PDF download", "status": 200, "result": "passed"})

    state_counts = {}
    for item in orders:
        state_counts[item["target"]] = state_counts.get(item["target"], 0) + 1
    result = {
        "base_url": args.base_url,
        "marker": "E2E-20260912",
        "created_count": len(orders),
        "role_checks": role_checks,
        "negative_and_security_checks": checks,
        "state_counts": state_counts,
        "orders": orders,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("created_count", "state_counts", "negative_and_security_checks")}, ensure_ascii=False, indent=2))
    print(f"Result written to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
