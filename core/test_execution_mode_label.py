from types import SimpleNamespace

from django.test import SimpleTestCase

from .views import _execution_mode_label


class ExecutionModeLabelTests(SimpleTestCase):
    def order(self, version, label):
        return SimpleNamespace(
            workflow_version=version,
            get_execution_mode_display=lambda: label,
        )

    def test_unassigned_v2_does_not_appear_as_mixed(self):
        self.assertEqual(
            _execution_mode_label(self.order(2, 'mixed'), []),
            '\u5f85\u5206\u914d',
        )

    def test_assigned_v2_keeps_execution_mode(self):
        for label in ('suzhou', 'jiangyin', 'outsource', 'mixed'):
            with self.subTest(label=label):
                self.assertEqual(
                    _execution_mode_label(self.order(2, label), [object()]),
                    label,
                )

    def test_legacy_order_keeps_explicit_execution_mode(self):
        self.assertEqual(
            _execution_mode_label(self.order(1, 'suzhou'), []),
            'suzhou',
        )
