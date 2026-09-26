from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import LabDevice, LabOrder, LabStaffProfile, SamplePhoto, SchedulePlan, WorkflowEvent


class AdvanceScheduleTests(TestCase):
    def setUp(self):
        self.manager = get_user_model().objects.create_user('advance_manager')
        self.manager.groups.add(Group.objects.get_or_create(name='苏州实验室')[0])
        self.operator = get_user_model().objects.create_user('advance_operator')
        self.operator.groups.add(Group.objects.get_or_create(name='实验操作员')[0])
        LabStaffProfile.objects.create(user=self.operator, lab_type=1, position=LabStaffProfile.Position.OPERATOR)
        self.today = timezone.localdate()
        self.tomorrow = self.today + timedelta(days=1)
        self.device = LabDevice.objects.create(device_code='ADVANCE-DEVICE', device_name='提前排期测试台', lab_type=1)
        self.order = LabOrder.objects.create(
            order_no='ADVANCE-ORDER', workflow_version=2, order_status=3,
            lead_lab_manager=self.manager, sales_confirmed_at=timezone.now(),
        )
        self.schedule = SchedulePlan.objects.create(
            order=self.order, test_type=1, lab_manager=self.manager, device=self.device,
            plan_start_time=timezone.make_aware(datetime.combine(self.tomorrow, time.min)),
            plan_end_time=timezone.make_aware(datetime.combine(self.tomorrow, time.max)),
            scheduled_at=timezone.now(), scheduled_by=self.manager,
            sample_arrived=True, sample_arrived_at=timezone.now(),
        )
        SamplePhoto.objects.create(order=self.order, schedule=self.schedule, file='existing.png', original_name='existing.png', file_size=1)

    def availability(self, user):
        self.client.force_login(user)
        return self.client.get(reverse('lab_device_availability'), {
            'schedule_id': self.schedule.id, 'start_date': str(self.today), 'end_date': str(self.tomorrow),
        })

    def advance(self, user):
        self.client.force_login(user)
        return self.client.post(reverse('lims_action'), {
            'action': 'schedule_assign', 'order_no': self.order.order_no,
            'schedule_id': self.schedule.id, 'device_id': self.device.id,
            'plan_start_time': str(self.today), 'plan_end_time': str(self.tomorrow),
            'sample_arrived': True,
        }, content_type='application/json')

    def check_advance(self, user):
        arrived_at = self.schedule.sample_arrived_at
        response = self.availability(user)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(next(d for d in response.json()['devices'] if d['id'] == self.device.id)['available'])
        response = self.advance(user)
        self.assertEqual(response.status_code, 200, response.content)
        self.schedule.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(timezone.localdate(self.schedule.plan_start_time), self.today)
        self.assertEqual(self.schedule.sample_arrived_at, arrived_at)
        self.assertEqual(self.schedule.sample_photos.count(), 1)
        self.assertIsNotNone(self.order.sales_confirmed_at)
        self.assertEqual(self.schedule.scheduled_by_id, user.id)
        self.assertTrue(WorkflowEvent.objects.filter(order=self.order, action_code='lab_schedule_assign').exists())

    def test_manager_can_advance_arrived_order_and_excludes_own_booking(self):
        self.check_advance(self.manager)

    def test_operator_can_advance_arrived_order_and_excludes_own_booking(self):
        self.check_advance(self.operator)

    def test_other_booking_still_blocks_and_preserves_original_plan(self):
        other = LabOrder.objects.create(order_no='ADVANCE-CONFLICT', workflow_version=2, order_status=3)
        SchedulePlan.objects.create(
            order=other, test_type=1, device=self.device, lab_manager=self.manager,
            plan_start_time=timezone.make_aware(datetime.combine(self.today, time.min)),
            plan_end_time=timezone.make_aware(datetime.combine(self.today, time.max)),
        )
        original_start, confirmed = self.schedule.plan_start_time, self.order.sales_confirmed_at
        response = self.availability(self.operator)
        self.assertFalse(next(d for d in response.json()['devices'] if d['id'] == self.device.id)['available'])
        response = self.advance(self.operator)
        self.assertEqual(response.status_code, 400)
        self.assertIn('排期冲突', response.json()['error'])
        self.schedule.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.schedule.plan_start_time, original_start)
        self.assertEqual(self.order.sales_confirmed_at, confirmed)

    def test_other_lab_operator_cannot_advance_order(self):
        LabStaffProfile.objects.filter(user=self.operator).update(lab_type=2)
        self.assertEqual(self.availability(self.operator).status_code, 403)
        self.assertEqual(self.advance(self.operator).status_code, 403)
