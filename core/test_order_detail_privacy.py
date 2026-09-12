import json

from django.test import SimpleTestCase

from .views import (
    ROLE_ACCOUNTING, ROLE_BUSINESS, ROLE_CHAIRMAN, ROLE_GENERAL_MANAGER,
    ROLE_JIANGYIN_LAB, ROLE_LAB_OPERATOR, ROLE_QUALITY, ROLE_SALES,
    ROLE_SALES_MANAGER, ROLE_SUZHOU_LAB, ROLE_TECH,
    _redact_order_experiment_data,
)


class OrderDetailPrivacyTests(SimpleTestCase):
    def setUp(self):
        self.payload = {
            'order_no': 'UI-PRIVACY-TEST',
            'experiment_records': [{'raw_data': 'PRIVATE-RAW', 'conclusion': 'PRIVATE-CONCLUSION'}],
            'schedule_records': [{
                'id': 1, 'experiment_result_key': 'pass',
                'experiment_raw_data': 'PRIVATE-RAW',
                'experiment_conclusion': 'PRIVATE-CONCLUSION',
            }],
            'report_records': [{'report_no': 'TEST-REPORT'}],
            'workflow_progress': {'current_node': 'invoice'},
        }

    def test_non_lab_business_roles_cannot_receive_raw_experiments(self):
        for role in [ROLE_ACCOUNTING, ROLE_SALES, ROLE_SALES_MANAGER, ROLE_BUSINESS, ROLE_TECH]:
            with self.subTest(role=role):
                result = _redact_order_experiment_data(self.payload, [role])
                self.assertNotIn('experiment_records', result)
                self.assertNotIn('PRIVATE-', json.dumps(result))
                self.assertEqual(result['schedule_records'][0]['experiment_result_key'], 'pass')
                self.assertEqual(result['report_records'], self.payload['report_records'])
                self.assertEqual(result['workflow_progress'], self.payload['workflow_progress'])
        self.assertIn('experiment_raw_data', self.payload['schedule_records'][0])

    def test_authorized_roles_keep_experiment_data(self):
        for role in [ROLE_CHAIRMAN, ROLE_GENERAL_MANAGER, ROLE_QUALITY,
                     ROLE_SUZHOU_LAB, ROLE_JIANGYIN_LAB, ROLE_LAB_OPERATOR]:
            with self.subTest(role=role):
                self.assertEqual(_redact_order_experiment_data(self.payload, [role]), self.payload)

    def test_unknown_role_does_not_receive_raw_data(self):
        self.assertNotIn('PRIVATE-', json.dumps(_redact_order_experiment_data(self.payload, [])))
