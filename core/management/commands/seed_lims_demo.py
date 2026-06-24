from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
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


class Command(BaseCommand):
    help = '初始化苏州环测 LIMS 演示数据'

    def handle(self, *args, **options):
        user_model = get_user_model()
        admin_user = user_model.objects.filter(username='LuCrab').first()

        for group_name in [
            '销售',
            '商务',
            '技术',
            '质量部',
            '苏州实验室',
            '江阴实验室',
            '委外供应商',
            '总经理',
            '会计',
            '董事长',
        ]:
            group, _ = Group.objects.get_or_create(name=group_name)
            if admin_user and group_name == '董事长':
                admin_user.groups.add(group)

        now = timezone.now()
        order_specs = [
            {
                'order_no': 'LIMS-2026-0001',
                'project_name': '汽车零部件环境可靠性检测',
                'status': LabOrder.Status.TESTING,
                'mode': LabOrder.ExecutionMode.MIXED,
                'amount': '68000.00',
                'schedules': [
                    (SchedulePlan.TestType.SUZHOU, '', 0, 5, '高低温循环试验'),
                    (SchedulePlan.TestType.JIANGYIN, '', 1, 6, '振动耐久试验'),
                    (SchedulePlan.TestType.OUTSOURCE, '外协供应商A', 2, 8, '盐雾腐蚀试验'),
                ],
            },
            {
                'order_no': 'LIMS-2026-0002',
                'project_name': '电子控制器 EMC 预测试',
                'status': LabOrder.Status.REPORT_REVIEW,
                'mode': LabOrder.ExecutionMode.SUZHOU,
                'amount': '32000.00',
                'schedules': [
                    (SchedulePlan.TestType.SUZHOU, '', -3, 2, 'EMC 预测试'),
                ],
            },
            {
                'order_no': 'LIMS-2026-0003',
                'project_name': '材料老化委外检测',
                'status': LabOrder.Status.SCHEDULING,
                'mode': LabOrder.ExecutionMode.OUTSOURCE,
                'amount': '18800.00',
                'schedules': [
                    (SchedulePlan.TestType.OUTSOURCE, '外协供应商B', 3, 12, '材料老化试验'),
                ],
            },
        ]

        for spec in order_specs:
            order, _ = LabOrder.objects.update_or_create(
                order_no=spec['order_no'],
                defaults={
                    'customer_name': '苏州环测检测技术有限公司',
                    'customer_contact': '内部演示客户',
                    'customer_phone': '0512-00000000',
                    'project_name': spec['project_name'],
                    'test_demand': '依据客户需求完成检测、排期、报告审核和财务开票闭环。',
                    'sale_user': admin_user,
                    'order_status': spec['status'],
                    'execution_mode': spec['mode'],
                    'expect_sample_arrive': now + timedelta(days=2),
                    'expect_delivery_time': now + timedelta(days=14),
                    'total_quote': spec['amount'],
                    'create_by': admin_user.username if admin_user else 'system',
                    'update_by': admin_user.username if admin_user else 'system',
                    'remark': '系统初始化演示数据',
                },
            )

            BusinessReview.objects.update_or_create(
                order=order,
                defaults={
                    'biz_review_user': admin_user,
                    'tech_review_user': admin_user,
                    'biz_quote_detail': '商务报价已确认',
                    'tech_feasible': True,
                    'review_result': True,
                    'review_time': now,
                },
            )

            SchedulePlan.objects.filter(order=order).delete()
            Sample.objects.filter(order=order).delete()
            Experiment.objects.filter(order=order).delete()

            first_experiment = None
            for index, (test_type, factory, start_offset, end_offset, item_name) in enumerate(spec['schedules'], start=1):
                schedule = SchedulePlan.objects.create(
                    order=order,
                    test_type=test_type,
                    lab_manager=admin_user if test_type != SchedulePlan.TestType.OUTSOURCE else None,
                    outsource_factory=factory,
                    outsource_price=12000 if test_type == SchedulePlan.TestType.OUTSOURCE else 0,
                    outsource_cycle=end_offset - start_offset if test_type == SchedulePlan.TestType.OUTSOURCE else None,
                    plan_start_time=now + timedelta(days=start_offset),
                    plan_end_time=now + timedelta(days=end_offset),
                    schedule_status=SchedulePlan.Status.RUNNING
                    if order.order_status == LabOrder.Status.TESTING
                    else SchedulePlan.Status.NEW,
                    quality_user=admin_user,
                    remark=item_name,
                )
                sample = Sample.objects.create(
                    order=order,
                    schedule=schedule,
                    sample_no=f'SP-{order.order_no[-4:]}-{index}',
                    sample_name='送检样品',
                    sample_spec='演示规格',
                    sample_count=2,
                    storage_condition='常温',
                    actual_arrive_time=now,
                    sample_status=Sample.Status.TESTING
                    if order.order_status == LabOrder.Status.TESTING
                    else Sample.Status.REGISTERED,
                    quality_user=admin_user,
                )
                experiment = Experiment.objects.create(
                    order=order,
                    schedule=schedule,
                    sample=sample,
                    test_item_list=item_name,
                    test_standard='客户指定检测标准',
                    test_start_time=now + timedelta(days=start_offset),
                    test_operator=admin_user,
                    test_conclusion_temp='等待检测结果归档。',
                    test_status=Experiment.Status.RUNNING
                    if order.order_status == LabOrder.Status.TESTING
                    else Experiment.Status.WAITING,
                    test_type=test_type,
                )
                first_experiment = first_experiment or experiment

            if order.order_no == 'LIMS-2026-0001':
                ChangeRequest.objects.update_or_create(
                    order=order,
                    defaults={
                        'schedule': order.schedules.first(),
                        'change_scene': ChangeRequest.Scene.DURING_TEST,
                        'old_test_demand': order.test_demand,
                        'new_test_demand': f'{order.test_demand} 增加高温保持时长。',
                        'change_content': '客户追加试验条件确认，回流质量部重新确认周期。',
                        'change_user': admin_user,
                        'change_time': now,
                        'change_status': ChangeRequest.Status.PENDING,
                    },
                )

            if order.order_no == 'LIMS-2026-0002':
                report, _ = TestReport.objects.update_or_create(
                    order=order,
                    report_no='RPT-2026-0002',
                    defaults={
                        'test_record': first_experiment,
                        'report_status': TestReport.Status.SALES_REVIEW,
                        'create_quality_user': admin_user,
                        'final_conclusion': '检测项目已完成，待销售审核客户信息与基础数据。',
                    },
                )
                ReportAudit.objects.get_or_create(
                    report=report,
                    audit_level=ReportAudit.Level.SALES,
                    defaults={
                        'audit_user': admin_user,
                        'audit_result': ReportAudit.Result.APPROVED,
                        'audit_opinion': '演示审核记录',
                        'audit_time': now,
                    },
                )

            WorkflowEvent.objects.update_or_create(
                order=order,
                event_type=WorkflowEvent.EventType.STATUS,
                to_status=str(order.order_status),
                defaults={'actor': admin_user, 'note': '初始化演示流程状态'},
            )

        closed_order, _ = LabOrder.objects.update_or_create(
            order_no='LIMS-2026-0000',
            defaults={
                'customer_name': '苏州环测检测技术有限公司',
                'customer_contact': '内部演示客户',
                'customer_phone': '0512-00000000',
                'project_name': '历史订单开票归档',
                'test_demand': '历史流程闭环演示。',
                'sale_user': admin_user,
                'order_status': LabOrder.Status.INVOICED_CLOSED,
                'execution_mode': LabOrder.ExecutionMode.JIANGYIN,
                'expect_delivery_time': now - timedelta(days=3),
                'total_quote': '26000.00',
                'create_by': admin_user.username if admin_user else 'system',
                'update_by': admin_user.username if admin_user else 'system',
            },
        )
        report, _ = TestReport.objects.update_or_create(
            order=closed_order,
            report_no='RPT-2026-0000',
            defaults={'report_status': TestReport.Status.APPROVED, 'create_quality_user': admin_user},
        )
        Invoice.objects.update_or_create(
            order=closed_order,
            invoice_no='INV-2026-0000',
            defaults={
                'report': report,
                'invoice_amount': 26000,
                'invoice_type': '增值税普票',
                'invoice_date': datetime.combine(now.date(), datetime.min.time(), tzinfo=now.tzinfo),
                'pay_status': Invoice.PayStatus.PAID,
                'finance_user': admin_user,
                'order_finish_flag': Invoice.FinishFlag.FINISHED,
            },
        )

        self.stdout.write(self.style.SUCCESS(f'LIMS demo data ready: {LabOrder.objects.count()} orders'))
