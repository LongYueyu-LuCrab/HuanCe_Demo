import json

from django.contrib.auth import get_user_model
from django.test import TestCase


class PasswordChangeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='password-change-user',
            password='hc123456',
            first_name='密码测试员',
        )
        self.client.post(
            '/api/auth/login/',
            data=json.dumps({'username': 'password-change-user', 'password': 'hc123456'}),
            content_type='application/json',
        )

    def change(self, new_password, confirm_password=None):
        return self.client.post(
            '/api/auth/change-password/',
            data=json.dumps({
                'current_password': 'hc123456',
                'new_password': new_password,
                'confirm_password': confirm_password if confirm_password is not None else new_password,
            }),
            content_type='application/json',
        )

    def test_requires_complex_password_and_matching_confirmation(self):
        self.assertEqual(self.change('hc123456').status_code, 400)
        self.assertEqual(self.change('Hc123456!', 'Hc123456?').status_code, 400)

    def test_changes_password_and_invalidates_session(self):
        response = self.change('Hc123456!')
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(self.client.login(username='password-change-user', password='Hc123456!'))
        self.assertFalse(self.client.login(username='password-change-user', password='hc123456'))
