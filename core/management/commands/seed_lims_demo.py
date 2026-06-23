from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from core.models import (
    BusinessReview,
    ChangeRequest,
    Customer,
    Experiment,
    Invoice,
    LabOrder,
    Sample,
    ScheduleItem,
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

        customer, _ = Customer.objects.update_or_create(
            name='苏州环测检测技术有限公司',
            defaults={
                'contact_name': '内部演示客户',
                'phone': '0512-00000000',
                'email': 'loveudoc@163.com',
                'address': '苏州',
            },
        )

        today = date.today()
        order_specs = [
            {
                'order_no': 'LIMS-2026-0001',
                'project_name': '汽车零部件环境可靠性检测',
                'status': LabOrder.Status.TESTING,
                'mode': LabOrder.ExecutionMode.MIXED,
                'urgent': True,
                'amount': '68000.00',
                'items': [
                    ('suzhou', '苏州实验室项目负责人', '高低温循环试验', 0, 5, '内部设备已锁定'),
                    ('jiangyin', '江阴实验室项目负责人', '振动耐久试验', 1, 6, '江阴场地排期中'),
                    ('outsource', '外协供应商A', '盐雾腐蚀试验', 2, 8, '外协报价已确认'),
                ],
            },
            {
                'order_no': 'LIMS-2026-0002',
                'project_name': '电子控制器 EMC 预测试',
                'status': LabOrder.Status.SALES_REPORT_REVIEW,
                'mode': LabOrder.ExecutionMode.SUZHOU,
                'urgent': False,
                'amount': '32000.00',
                'items': [
                    ('suzhou', '苏州实验室项目负责人', 'EMC 预测试', -3, 2, '报告待销售初审'),
                ],
            },
            {
                'order_no': 'LIMS-2026-0003',
                'project_name': '材料老化委外检测',
                'status': LabOrder.Status.QUALITY_SCHEDULING,
                'mode': LabOrder.ExecutionMode.OUTSOURCE,
                'urgent': False,
                'amount': '18800.00',
                'items': [
                    ('outsource', '外协供应商B', '材料老化试验', 3, 12, '等待供应商最终周期'),
                ],
            },
        ]

        for spec in order_specs:
            order, _ = LabOrder.objects.update_or_create(
                order_no=spec['order_no'],
                defaults={
                    'customer': customer,
                    'project_name': spec['project_name'],
                    'test_requirements': '依据客户需求完成检测、排期、报告审核和财务开票闭环。',
                    'sales_owner': admin_user,
                    'status': spec['status'],
                    'execution_mode': spec['mode'],
                    'expected_sample_arrival': today + timedelta(days=2),
                    'expected_delivery_date': today + timedelta(days=14),
                    'quoted_amount': spec['amount'],
                    'is_urgent': spec['urgent'],
                    'chairman_visible': True,
                    'remark': '系统初始化演示数据',
                },
            )

            BusinessReview.objects.update_or_create(
                order=order,
                defaults={
                    'reviewer': admin_user,
                    'business_passed': True,
                    'technical_passed': True,
                    'quotation_note': '商务报价已确认',
                    'feasibility_note': '技术可行',
                    'delivery_note': '交付周期可控',
                },
            )

            plan, _ = SchedulePlan.objects.update_or_create(
                order=order,
                defaults={
                    'owner': admin_user,
                    'version': 1,
                    'start_date': today,
                    'end_date': today + timedelta(days=14),
                    'summary': '整合苏州、江阴与委外资源形成统一项目周期表。',
                    'approved': order.status != LabOrder.Status.QUALITY_SCHEDULING,
                },
            )
            ScheduleItem.objects.filter(plan=plan).delete()
            Sample.objects.filter(order=order).delete()
            Experiment.objects.filter(order=order).delete()

            for index, (resource_type, owner_name, task_name, start_offset, end_offset, note) in enumerate(spec['items'], start=1):
                item = ScheduleItem.objects.create(
                    plan=plan,
                    resource_type=resource_type,
                    owner_name=owner_name,
                    task_name=task_name,
                    start_date=today + timedelta(days=start_offset),
                    end_date=today + timedelta(days=end_offset),
                    cost=12000,
                    note=note,
                )
                sample = Sample.objects.create(
                    order=order,
                    sample_no=f'SP-{order.order_no[-4:]}-{index}',
                    name='送检样品',
                    quantity=2,
                    storage_location='样品室 A 区',
                )
                Experiment.objects.create(
                    order=order,
                    schedule_item=item,
                    sample=sample,
                    name=task_name,
                    executor=owner_name,
                    status=Experiment.Status.RUNNING
                    if order.status == LabOrder.Status.TESTING
                    else Experiment.Status.WAITING,
                    result_summary='等待检测结果归档。',
                )

            if order.order_no == 'LIMS-2026-0001':
                ChangeRequest.objects.update_or_create(
                    order=order,
                    stage=ChangeRequest.ChangeStage.DURING_TEST,
                    defaults={
                        'requester': admin_user,
                        'reason': '客户追加试验条件确认',
                        'requested_changes': '增加高温保持时长，回流质量部重新确认周期。',
                        'status': ChangeRequest.Status.SUBMITTED,
                    },
                )

            if order.order_no == 'LIMS-2026-0002':
                TestReport.objects.update_or_create(
                    order=order,
                    report_no='RPT-2026-0002',
                    defaults={
                        'version': 1,
                        'status': TestReport.Status.SALES_REVIEW,
                        'prepared_by': admin_user,
                        'conclusion': '检测项目已完成，待销售审核客户信息与基础数据。',
                    },
                )

            WorkflowEvent.objects.update_or_create(
                order=order,
                event_type=WorkflowEvent.EventType.STATUS,
                to_status=order.status,
                defaults={'actor': admin_user, 'note': '初始化演示流程状态'},
            )

        closed_order, _ = LabOrder.objects.update_or_create(
            order_no='LIMS-2026-0000',
            defaults={
                'customer': customer,
                'project_name': '历史订单开票归档',
                'test_requirements': '历史流程闭环演示。',
                'sales_owner': admin_user,
                'status': LabOrder.Status.CLOSED,
                'execution_mode': LabOrder.ExecutionMode.JIANGYIN,
                'expected_delivery_date': today - timedelta(days=3),
                'quoted_amount': '26000.00',
                'chairman_visible': True,
            },
        )
        Invoice.objects.update_or_create(
            order=closed_order,
            defaults={
                'invoice_no': 'INV-2026-0000',
                'accountant': admin_user,
                'amount': 26000,
                'issued_at': today,
            },
        )

        self.stdout.write(self.style.SUCCESS(f'LIMS demo data ready: {LabOrder.objects.count()} orders'))
