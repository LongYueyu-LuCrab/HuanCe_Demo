from unittest.mock import Mock

from django.test import SimpleTestCase

from .models import ChangeRequest, LabOrder
from .views import PENDING_CHANGE_BLOCKED_ACTIONS, _pending_change_error


class PendingChangeGuardTests(SimpleTestCase):
    def order(self, pending):
        order = Mock(workflow_version=LabOrder.WorkflowVersion.LAB_DIRECT)
        order.change_requests.exclude.return_value.exists.return_value = pending
        return order

    def test_unresolved_change_blocks_advancement(self):
        for action in PENDING_CHANGE_BLOCKED_ACTIONS:
            with self.subTest(action=action):
                order = self.order(True)
                response = _pending_change_error(order, action)
                self.assertEqual(response.status_code, 400)
                order.change_requests.exclude.assert_called_once_with(
                    change_status=ChangeRequest.Status.APPLIED,
                )

    def test_applied_changes_allow_advancement(self):
        for action in PENDING_CHANGE_BLOCKED_ACTIONS:
            with self.subTest(action=action):
                self.assertIsNone(_pending_change_error(self.order(False), action))

    def test_processing_and_sample_arrival_remain_available(self):
        for action in ('process_change', 'sample_arrival', 'end_test', 'invoice_pay'):
            self.assertIsNone(_pending_change_error(self.order(True), action))

    def test_results_require_sales_reconfirmation_after_change(self):
        order = self.order(False)
        order.sales_confirmed_at = None
        for action in ('submit_test', 'issue_report'):
            self.assertEqual(_pending_change_error(order, action).status_code, 400)
