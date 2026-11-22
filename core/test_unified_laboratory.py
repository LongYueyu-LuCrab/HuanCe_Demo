import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from .models import LabDevice, LabStaffProfile


class UnifiedLaboratoryRegressionTests(TestCase):
    def setUp(self):
        manager_group, _ = Group.objects.get_or_create(name='实验室负责人')
        self.manager = get_user_model().objects.create_user(
            username='unified-lab-manager',
            password='password123',
        )
        self.manager.groups.add(manager_group)
        # Simulate a legacy profile that has not yet been normalized.
        LabStaffProfile.objects.create(
            user=self.manager,
            lab_type=2,
            position=LabStaffProfile.Position.MANAGER,
        )

    def test_device_creation_and_queries_always_use_lab_one(self):
        self.client.force_login(self.manager)
        created = self.client.post(
            reverse('lab_devices'),
            data=json.dumps({
                'device_code': 'UNIFIED-001',
                'device_name': '统一实验室测试设备',
                'lab_type': 2,
            }),
            content_type='application/json',
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()['device']['lab_type'], 1)
        self.assertEqual(LabDevice.objects.get(device_code='UNIFIED-001').lab_type, 1)

        for legacy_query_value in ('0', '1', '2'):
            response = self.client.get(reverse('laboratory_orders'), {'lab_type': legacy_query_value})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['lab_type'], 1)
