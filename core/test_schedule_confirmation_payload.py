from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from .models import LabOrder, SchedulePlan
from .views import _schedule_payload


class ScheduleConfirmationPayloadTests(SimpleTestCase):
    def test_confirmation_flag_tracks_the_order(self):
        for confirmed_at in (None, timezone.now()):
            with self.subTest(confirmed=bool(confirmed_at)):
                order = LabOrder(workflow_version=2, sales_confirmed_at=confirmed_at)
                schedule = SchedulePlan(order=order, test_type=1)
                with (
                    patch('core.views._schedule_samples', return_value=[]),
                    patch('core.views._schedule_experiment', return_value=None),
                    patch('core.views._sample_photo_payloads', return_value=[]),
                ):
                    payload = _schedule_payload(schedule)
                self.assertEqual(payload['sales_confirmed'], bool(confirmed_at))
