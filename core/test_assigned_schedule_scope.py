from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase

from core import views


class AssignedScheduleScopeTests(SimpleTestCase):
    def query(self, params, *, operator=False, chairman=False, lab_type=1):
        request = RequestFactory().get('/api/labs/orders/', params)
        request.user = get_user_model()(pk=701, username='scope-test')
        with (
            patch.object(views, '_user_lab_type', return_value=lab_type),
            patch.object(views, '_roles', return_value=[]),
            patch.object(views, '_has_any_role', return_value=True),
            patch.object(views, '_is_chairman', return_value=chairman),
            patch.object(views, '_is_lab_operator', return_value=operator),
        ):
            return views._laboratory_schedule_queryset(request)

    def test_manager_assigned_scope_filters_by_owner_not_dashboard_limit(self):
        rows, _, error = self.query({'scope': 'assigned', 'keyword': 'BRANCH'})
        self.assertIsNone(error)
        self.assertIn('"lab_manager_id" = 701', str(rows.query))
        self.assertIn('BRANCH', str(rows.query))
        self.assertFalse(rows.query.is_sliced)

    def test_operator_scope_includes_lab_and_owned_outsource(self):
        rows, _, error = self.query({'scope': 'assigned'}, operator=True)
        self.assertIsNone(error)
        sql = str(rows.query)
        self.assertIn('"test_type" = 1', sql)
        self.assertIn('"test_type" = 3', sql)

    def test_other_laboratory_is_still_denied(self):
        _, _, error = self.query({'scope': 'assigned', 'lab_type': '2'})
        self.assertEqual(error.status_code, 403)

    def test_outsource_filter_keeps_owner_scope(self):
        rows, _, error = self.query({'scope': 'assigned', 'test_type': '3'})
        self.assertIsNone(error)
        self.assertIn('"test_type" = 3', str(rows.query))
        self.assertIn('"lab_manager_id" = 701', str(rows.query))

    def test_chairman_can_query_assigned_tasks_without_lab_selector(self):
        rows, _, error = self.query({'scope': 'assigned'}, chairman=True, lab_type=None)
        self.assertIsNone(error)
        self.assertNotIn('"lab_manager_id" = 701', str(rows.query))
