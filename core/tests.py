from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    BusinessReview,
    ChangeRequest,
    Experiment,
    Invoice,
    LabOrder,
    ReportAudit,
    Sample,
    SchedulePlan,
    TestReport,
    WorkflowEvent,
)


class LimsDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='tester',
            password='password123',
        )
        sales_group = Group.objects.create(name='销售')
        self.user.groups.add(sales_group)
        self.order = LabOrder.objects.create(
            order_no='TEST-001',
            customer_name='苏州环测检测技术有限公司',
            customer_contact='王五',
            customer_phone='13800000000',
            project_name='测试订单',
            test_demand='测试需求',
            sale_user=self.user,
            order_status=LabOrder.Status.TESTING,
        )

    def test_dashboard_api_returns_lims_summary(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('lims_dashboard'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['company'], '苏州环测检测技术有限公司')
        self.assertEqual(data['metrics']['orders'], 1)
        self.assertEqual(data['metrics']['active_orders'], 1)
        self.assertEqual(len(data['recent_orders']), 1)
        self.assertEqual(data['recent_orders'][0]['order_no'], 'TEST-001')

    def test_mark_status_writes_workflow_event(self):
        self.order.mark_status(LabOrder.Status.REPORT_REVIEW, note='测试流转')

        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, LabOrder.Status.REPORT_REVIEW)
        self.assertTrue(
            WorkflowEvent.objects.filter(
                order=self.order,
                from_status=str(LabOrder.Status.TESTING),
                to_status=str(LabOrder.Status.REPORT_REVIEW),
            ).exists()
        )

    def test_sales_can_create_order(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('create_order'),
            data={
                'customer_name': '新客户',
                'contact_name': '王五',
                'phone': '13800000000',
                'project_name': '新项目',
                'test_requirements': '完成可靠性检测。',
                'expected_sample_arrival': '2026-07-01',
                'expected_delivery_date': '2026-07-15',
                'quoted_amount': '12000.50',
                'is_urgent': True,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['ok'])
        created = LabOrder.objects.get(order_no=payload['order']['order_no'])
        self.assertEqual(created.sale_user, self.user)
        self.assertEqual(created.order_status, LabOrder.Status.PENDING_REVIEW)
        self.assertEqual(created.customer_name, '新客户')


class LimsFullRoleWorkflowTests(TestCase):
    roles = {
        'sales': '销售',
        'business': '商务',
        'tech': '技术',
        'quality': '质量部',
        'suzhou_lab': '苏州实验室',
        'jiangyin_lab': '江阴实验室',
        'general_manager': '总经理',
        'accountant': '会计',
    }

    def setUp(self):
        user_model = get_user_model()
        self.users = {}
        for username, role_name in self.roles.items():
            group = Group.objects.create(name=role_name)
            user = user_model.objects.create_user(
                username=username,
                password='password123',
                first_name=role_name,
            )
            user.groups.add(group)
            self.users[username] = user

    def test_all_roles_can_complete_one_lims_order_flow(self):
        now = timezone.now()

        order = LabOrder.objects.create(
            order_no='FLOW-001',
            customer_name='流程测试客户',
            customer_contact='赵六',
            customer_phone='13900000000',
            project_name='全角色流程测试',
            test_demand='覆盖销售、商务、技术、质量、双实验室、总经理、会计的完整流程。',
            total_quote='50000.00',
            expect_sample_arrive=now + timezone.timedelta(days=1),
            sale_user=self.users['sales'],
            create_by=self.users['sales'].username,
            update_by=self.users['sales'].username,
            order_status=LabOrder.Status.PENDING_REVIEW,
        )
        WorkflowEvent.objects.create(
            order=order,
            actor=self.users['sales'],
            event_type=WorkflowEvent.EventType.STATUS,
            to_status=str(LabOrder.Status.PENDING_REVIEW),
            note='销售下单',
        )

        review = BusinessReview.objects.create(
            order=order,
            biz_review_user=self.users['business'],
            tech_review_user=self.users['tech'],
            biz_quote_detail='商务报价通过',
            tech_feasible=True,
            review_result=True,
            review_time=now,
        )
        order.mark_status(LabOrder.Status.SCHEDULING, self.users['business'], '商务技术评审通过')

        suzhou_schedule = SchedulePlan.objects.create(
            order=order,
            test_type=SchedulePlan.TestType.SUZHOU,
            lab_manager=self.users['suzhou_lab'],
            plan_start_time=now + timezone.timedelta(days=2),
            plan_end_time=now + timezone.timedelta(days=5),
            schedule_status=SchedulePlan.Status.RUNNING,
            quality_user=self.users['quality'],
            remark='苏州实验室排期',
        )
        jiangyin_schedule = SchedulePlan.objects.create(
            order=order,
            test_type=SchedulePlan.TestType.JIANGYIN,
            lab_manager=self.users['jiangyin_lab'],
            plan_start_time=now + timezone.timedelta(days=3),
            plan_end_time=now + timezone.timedelta(days=6),
            schedule_status=SchedulePlan.Status.RUNNING,
            quality_user=self.users['quality'],
            remark='江阴实验室排期',
        )

        change = ChangeRequest.objects.create(
            order=order,
            schedule=suzhou_schedule,
            change_scene=ChangeRequest.Scene.BEFORE_SAMPLE,
            old_test_demand=order.test_demand,
            new_test_demand=f'{order.test_demand} 增加温湿度循环。',
            change_content='样品到货前客户调整检测条件',
            change_user=self.users['sales'],
            change_status=ChangeRequest.Status.APPLIED,
        )
        suzhou_schedule.plan_end_time = suzhou_schedule.plan_end_time + timezone.timedelta(days=1)
        suzhou_schedule.save(update_fields=['plan_end_time', 'update_time'])

        suzhou_sample = Sample.objects.create(
            order=order,
            schedule=suzhou_schedule,
            sample_no='SAMPLE-SZ-001',
            sample_name='苏州试验样品',
            sample_spec='A 型',
            sample_count=2,
            storage_condition='常温',
            actual_arrive_time=now,
            sample_status=Sample.Status.TESTING,
            quality_user=self.users['quality'],
        )
        jiangyin_sample = Sample.objects.create(
            order=order,
            schedule=jiangyin_schedule,
            sample_no='SAMPLE-JY-001',
            sample_name='江阴试验样品',
            sample_spec='B 型',
            sample_count=1,
            storage_condition='避光',
            actual_arrive_time=now,
            sample_status=Sample.Status.TESTING,
            quality_user=self.users['quality'],
        )
        order.mark_status(LabOrder.Status.TESTING, self.users['quality'], '样品登记完成，开始试验')

        suzhou_test = Experiment.objects.create(
            order=order,
            schedule=suzhou_schedule,
            sample=suzhou_sample,
            test_item_list='高低温循环试验',
            test_standard='GB/T 2423',
            test_start_time=now + timezone.timedelta(days=2),
            test_end_time=now + timezone.timedelta(days=5),
            test_operator=self.users['suzhou_lab'],
            test_raw_data='苏州实验室原始数据',
            test_conclusion_temp='苏州项目合格',
            test_status=Experiment.Status.FINISHED,
            test_type=SchedulePlan.TestType.SUZHOU,
        )
        jiangyin_test = Experiment.objects.create(
            order=order,
            schedule=jiangyin_schedule,
            sample=jiangyin_sample,
            test_item_list='振动耐久试验',
            test_standard='GB/T 2423',
            test_start_time=now + timezone.timedelta(days=3),
            test_end_time=now + timezone.timedelta(days=6),
            test_operator=self.users['jiangyin_lab'],
            test_raw_data='江阴实验室原始数据',
            test_conclusion_temp='江阴项目合格',
            test_status=Experiment.Status.FINISHED,
            test_type=SchedulePlan.TestType.JIANGYIN,
        )
        self.assertNotEqual(suzhou_test.test_operator, jiangyin_test.test_operator)

        report = TestReport.objects.create(
            order=order,
            test_record=suzhou_test,
            report_no='RPT-FLOW-001',
            report_file_url='/media/reports/RPT-FLOW-001.pdf',
            final_conclusion='全部检测项目符合要求。',
            report_status=TestReport.Status.SALES_REVIEW,
            create_quality_user=self.users['quality'],
        )
        order.mark_status(LabOrder.Status.REPORT_REVIEW, self.users['quality'], '质量部出具报告')

        sales_audit = ReportAudit.objects.create(
            report=report,
            audit_level=ReportAudit.Level.SALES,
            audit_user=self.users['sales'],
            audit_result=ReportAudit.Result.APPROVED,
            audit_opinion='销售初审通过',
            audit_time=now,
        )
        report.report_status = TestReport.Status.GM_REVIEW
        report.save(update_fields=['report_status', 'update_time'])

        gm_audit = ReportAudit.objects.create(
            report=report,
            audit_level=ReportAudit.Level.GENERAL_MANAGER,
            audit_user=self.users['general_manager'],
            audit_result=ReportAudit.Result.APPROVED,
            audit_opinion='总经理终审通过',
            audit_time=now,
        )
        report.report_status = TestReport.Status.APPROVED
        report.save(update_fields=['report_status', 'update_time'])

        invoice = Invoice.objects.create(
            order=order,
            report=report,
            invoice_no='INV-FLOW-001',
            invoice_amount=order.total_quote,
            invoice_type='增值税专票',
            invoice_date=now,
            pay_status=Invoice.PayStatus.PAID,
            finance_user=self.users['accountant'],
            order_finish_flag=Invoice.FinishFlag.FINISHED,
        )
        order.mark_status(LabOrder.Status.INVOICED_CLOSED, self.users['accountant'], '会计开票办结')

        order.refresh_from_db()
        report.refresh_from_db()

        self.assertTrue(review.review_result)
        self.assertEqual(change.change_status, ChangeRequest.Status.APPLIED)
        self.assertEqual(order.schedules.count(), 2)
        self.assertEqual(order.samples.count(), 2)
        self.assertEqual(order.experiments.count(), 2)
        self.assertEqual(report.audits.count(), 2)
        self.assertEqual(sales_audit.audit_user, self.users['sales'])
        self.assertEqual(gm_audit.audit_user, self.users['general_manager'])
        self.assertEqual(invoice.finance_user, self.users['accountant'])
        self.assertEqual(invoice.order_finish_flag, Invoice.FinishFlag.FINISHED)
        self.assertEqual(report.report_status, TestReport.Status.APPROVED)
        self.assertEqual(order.order_status, LabOrder.Status.INVOICED_CLOSED)
        self.assertEqual(
            set(Group.objects.values_list('name', flat=True)),
            set(self.roles.values()),
        )
