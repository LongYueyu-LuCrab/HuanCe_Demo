from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import Invoice, LabOrder
from .views import _invoice_payload


class InvoiceVoidVisibilityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='invoice-owner')
        self.other = get_user_model().objects.create_user(username='other-accountant')
        self.order = LabOrder.objects.create(
            order_no='VOID-VISIBILITY', customer_name='Synthetic customer',
            total_quote=Decimal('20000'), sale_user=self.user,
            order_status=LabOrder.Status.INVOICED_CLOSED,
        )
        self.pre = self.invoice('PRE', Invoice.Stage.PRE_REVIEW, '5000')
        self.final = self.invoice('FINAL', Invoice.Stage.FINAL, '15000')

    def invoice(self, number, stage, amount):
        return Invoice.objects.create(
            order=self.order, invoice_no=number, invoice_stage=stage,
            invoice_amount=Decimal(amount), invoice_date=timezone.now(),
            finance_user=self.user,
        )

    def test_valid_final_hides_preliminary_void_only(self):
        self.assertFalse(_invoice_payload(self.pre, self.user)['can_void'])
        self.assertTrue(_invoice_payload(self.final, self.user)['can_void'])

    def test_voided_final_restores_preliminary_void(self):
        self.final.record_status = Invoice.RecordStatus.VOIDED
        self.final.save()
        self.assertTrue(_invoice_payload(self.pre, self.user)['can_void'])
        self.assertFalse(_invoice_payload(self.final, self.user)['can_void'])

    def test_other_accountant_cannot_void(self):
        self.assertFalse(_invoice_payload(self.final, self.other)['can_void'])

    def test_prefetched_history_uses_same_rule_without_queries(self):
        order = LabOrder.objects.prefetch_related('invoices', 'experiments').get(pk=self.order.pk)
        self.pre.order = order
        with self.assertNumQueries(0):
            self.assertFalse(_invoice_payload(self.pre, self.user)['can_void'])
