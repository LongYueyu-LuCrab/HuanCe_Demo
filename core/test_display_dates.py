from datetime import datetime, timezone as datetime_timezone
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from .models import Invoice, LabOrder, SchedulePlan, TestReport
from .views import _display_date, _display_datetime, _invoice_payload, _order_payload, _report_payload, _schedule_payload


class DisplayDateTests(SimpleTestCase):
    """Pure serialization checks; no HTTP requests or database writes."""

    def test_local_midnight_preserves_selected_calendar_date(self):
        stored = datetime(2032, 12, 31, 16, tzinfo=datetime_timezone.utc)
        with timezone.override('Asia/Shanghai'):
            self.assertEqual(_display_date(stored), '2033-01-01')
            self.assertEqual(_display_datetime(stored), '2033-01-01 00:00')
            self.assertEqual(_display_date(None), '')

    def test_schedule_payload_converts_utc_to_business_dates(self):
        order = LabOrder(order_no='UI-DATE-TEST')
        schedule = SchedulePlan(
            order=order,
            plan_start_time=datetime(2032, 12, 31, 16, tzinfo=datetime_timezone.utc),
            plan_end_time=datetime(2033, 1, 2, 15, 59, tzinfo=datetime_timezone.utc),
        )
        with (
            timezone.override('Asia/Shanghai'),
            patch('core.views._schedule_samples', return_value=[]),
            patch('core.views._schedule_experiment', return_value=None),
            patch('core.views._sample_photo_payloads', return_value=[]),
        ):
            payload = _schedule_payload(schedule)
        self.assertEqual(payload['start_time'], '2033-01-01')
        self.assertEqual(payload['end_time'], '2033-01-02')

    def test_order_creation_time_matches_workflow_local_time(self):
        order = LabOrder(
            id=1,
            order_no='UI-DATE-TEST',
            create_time=datetime(2026, 9, 12, 15, 51, tzinfo=datetime_timezone.utc),
        )
        order.payload_schedules = []
        order._prefetched_objects_cache = {'documents': []}
        with timezone.override('Asia/Shanghai'):
            payload = _order_payload(order)
        self.assertEqual(payload['created_at'], '2026-09-12 23:51')

    def test_report_generation_time_uses_local_date_after_midnight(self):
        report = TestReport(
            order=LabOrder(order_no='UI-DATE-TEST'),
            generated_at=datetime(2026, 9, 12, 16, 47, tzinfo=datetime_timezone.utc),
        )
        with timezone.override('Asia/Shanghai'):
            payload = _report_payload(report)
        self.assertEqual(payload['generated_at'], '2026-09-13 00:47')

    def test_invoice_date_and_void_time_use_business_timezone(self):
        order = LabOrder(order_no='UI-DATE-TEST', order_status=LabOrder.Status.INVOICED_CLOSED)
        order._prefetched_objects_cache = {'invoices': []}
        invoice = Invoice(
            order=order,
            invoice_date=datetime(2026, 9, 12, 16, tzinfo=datetime_timezone.utc),
            voided_at=datetime(2026, 9, 12, 16, 30, tzinfo=datetime_timezone.utc),
        )
        with timezone.override('Asia/Shanghai'):
            payload = _invoice_payload(invoice)
        self.assertEqual(payload['invoice_date'], '2026-09-13')
        self.assertEqual(payload['voided_at'], '2026-09-13 00:30')
