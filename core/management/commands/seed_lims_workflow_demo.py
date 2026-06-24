from decimal import Decimal
from random import Random

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
    help = '创建 10 个角色账号和 60 笔覆盖全流程的 LIMS 模拟订单'

    demo_password = 'HuanCe@2026'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-existing',
            action='store_true',
            help='保留已有 DEMO-2026 订单，不先清理重建。',
        )

    def handle(self, *args, **options):
        rnd = Random(20260625)
        now = timezone.now()

        users = self.ensure_users()

        if not options['keep_existing']:
            LabOrder.objects.filter(order_no__startswith='DEMO-2026-').delete()

        customers = [
            ('苏州智驱汽车科技有限公司', '周工', '13812660001'),
            ('无锡蓝芯电子有限公司', '陈经理', '13912660002'),
            ('常州启衡新能源有限公司', '沈工', '13712660003'),
            ('南京卓维材料研究院', '赵主任', '13612660004'),
            ('上海越科智能装备有限公司', '林经理', '13512660005'),
            ('杭州星环传感技术有限公司', '钱工', '15812660006'),
            ('宁波海川电驱系统有限公司', '孙经理', '15912660007'),
            ('合肥清越半导体有限公司', '吴工', '15712660008'),
        ]
        projects = [
            ('车载控制器环境可靠性验证', '高低温循环、温湿度偏置、振动耐久、外观复核'),
            ('新能源电池包结构件试验', '盐雾腐蚀、冷热冲击、机械冲击、密封性能验证'),
            ('传感器三综合应力筛选', '温度、湿度、振动三综合试验并记录漂移数据'),
            ('电子模块 EMC 预测试', '静电放电、浪涌、传导抗扰度、辐射发射预测试'),
            ('材料老化与阻燃性能验证', '紫外老化、热老化、阻燃等级、拉伸强度复测'),
            ('工业连接器耐久性测试', '插拔寿命、振动、温升、接触电阻稳定性验证'),
            ('智能座舱屏幕可靠性测试', '高温高湿、冷热冲击、跌落、亮度衰减观察'),
            ('电机控制器壳体防护测试', 'IP 防护、盐雾、温升、机械振动验证'),
        ]
        standards = ['GB/T 2423', 'GB/T 4208', 'IEC 60068', 'ISO 16750', 'GB/T 10125']
        modes = [
            LabOrder.ExecutionMode.SUZHOU,
            LabOrder.ExecutionMode.JIANGYIN,
            LabOrder.ExecutionMode.OUTSOURCE,
            LabOrder.ExecutionMode.MIXED,
        ]

        created = []
        for index in range(1, 61):
            scenario = self.scenario_for(index)
            customer_name, contact, phone = customers[(index - 1) % len(customers)]
            project_name, demand = projects[(index - 1) % len(projects)]
            sales_user = users[f'sales{((index - 1) % 3) + 1:02d}']
            mode = modes[(index - 1) % len(modes)]
            quote = Decimal(12000 + (index * 1730) % 88000).quantize(Decimal('0.01'))
            order_no = f'DEMO-2026-{index:04d}'
            created_at = now - timezone.timedelta(days=70 - index)

            order = LabOrder.objects.create(
                order_no=order_no,
                customer_name=customer_name,
                customer_contact=contact,
                customer_phone=phone,
                project_name=f'{project_name}-{index:02d}',
                test_demand=f'{demand}。执行标准：{standards[index % len(standards)]}。',
                total_quote=quote,
                expect_sample_arrive=created_at + timezone.timedelta(days=2),
                expect_delivery_time=created_at + timezone.timedelta(days=12 + index % 8),
                order_status=scenario['order_status'],
                execution_mode=mode,
                sale_user=sales_user,
                create_by=sales_user.username,
                update_by=sales_user.username,
                remark='加急；批量全流程演示订单' if index % 9 == 0 else '批量全流程演示订单',
            )
            created.append(order)
            self.event(order, sales_user, '', order.order_status, '销售创建订单')

            if scenario['review'] == 'rejected':
                BusinessReview.objects.create(
                    order=order,
                    biz_review_user=users['business01'],
                    tech_review_user=users['tech01'],
                    biz_quote_detail='商务报价与客户预算差异较大，建议销售重新确认范围。',
                    tech_feasible=index % 2 == 0,
                    review_result=False,
                    reject_reason='检测标准不完整或样品信息不足，需销售补充后重新提交。',
                    review_time=created_at + timezone.timedelta(days=1),
                )
                self.event(order, users['business01'], LabOrder.Status.PENDING_REVIEW, order.order_status, '商务技术评审驳回')
                continue

            BusinessReview.objects.create(
                order=order,
                biz_review_user=users['business01'],
                tech_review_user=users['tech01'],
                biz_quote_detail=f'报价包含试验费、样品管理费、报告编制费，合计 {quote} 元。',
                tech_feasible=True,
                review_result=True,
                review_time=created_at + timezone.timedelta(days=1),
            )
            self.event(order, users['tech01'], LabOrder.Status.PENDING_REVIEW, LabOrder.Status.SCHEDULING, '商务技术评审通过')

            schedules = self.create_schedules(order, mode, users, created_at, rnd)

            if index % 7 == 0:
                schedule = schedules[0]
                ChangeRequest.objects.create(
                    order=order,
                    schedule=schedule,
                    change_scene=ChangeRequest.Scene.BEFORE_SAMPLE if index % 14 else ChangeRequest.Scene.DURING_TEST,
                    old_test_demand=order.test_demand,
                    new_test_demand=f'{order.test_demand} 客户追加一组复测样品。',
                    change_content='客户调整检测项目数量，质量部已同步更新排期。',
                    change_user=sales_user if index % 14 else users['quality01'],
                    change_time=created_at + timezone.timedelta(days=3),
                    change_status=ChangeRequest.Status.APPLIED if scenario['order_status'] != LabOrder.Status.TESTING else ChangeRequest.Status.PENDING,
                )
                self.event(order, sales_user, order.order_status, order.order_status, '创建订单变更单')

            if scenario['stage_rank'] < 3:
                continue

            experiments = self.create_samples_and_experiments(order, schedules, users, created_at, scenario)

            if scenario['stage_rank'] < 5:
                continue

            report = self.create_report(order, experiments[0], users, created_at, scenario)

            if scenario['report'] in ['sales_rejected', 'gm_rejected']:
                level = ReportAudit.Level.SALES if scenario['report'] == 'sales_rejected' else ReportAudit.Level.GENERAL_MANAGER
                auditor = users['sales01'] if level == ReportAudit.Level.SALES else users['general_manager01']
                ReportAudit.objects.create(
                    report=report,
                    audit_level=level,
                    audit_user=auditor,
                    audit_result=ReportAudit.Result.REJECTED,
                    audit_opinion='报告数据、客户信息或结论表述需要质量部重新核对。',
                    audit_time=created_at + timezone.timedelta(days=10),
                )
                self.event(order, auditor, order.order_status, order.order_status, '报告审核不通过，退回质量部重制')
            elif scenario['report'] == 'gm_pending':
                ReportAudit.objects.create(
                    report=report,
                    audit_level=ReportAudit.Level.SALES,
                    audit_user=users['sales02'],
                    audit_result=ReportAudit.Result.APPROVED,
                    audit_opinion='销售初审通过，提交总经理终审。',
                    audit_time=created_at + timezone.timedelta(days=10),
                )
            elif scenario['report'] == 'approved':
                ReportAudit.objects.create(
                    report=report,
                    audit_level=ReportAudit.Level.SALES,
                    audit_user=users['sales03'],
                    audit_result=ReportAudit.Result.APPROVED,
                    audit_opinion='销售初审通过。',
                    audit_time=created_at + timezone.timedelta(days=10),
                )
                ReportAudit.objects.create(
                    report=report,
                    audit_level=ReportAudit.Level.GENERAL_MANAGER,
                    audit_user=users['general_manager01'],
                    audit_result=ReportAudit.Result.APPROVED,
                    audit_opinion='总经理终审通过，同意开票。',
                    audit_time=created_at + timezone.timedelta(days=11),
                )

            if scenario['invoice']:
                Invoice.objects.create(
                    order=order,
                    report=report,
                    invoice_no=f'INV-DEMO-2026-{index:04d}',
                    invoice_amount=quote,
                    invoice_type='增值税专票' if index % 3 else '增值税普票',
                    invoice_date=created_at + timezone.timedelta(days=13),
                    pay_status=Invoice.PayStatus.PAID if index % 4 else Invoice.PayStatus.UNPAID,
                    finance_user=users['accountant01'],
                    order_finish_flag=Invoice.FinishFlag.FINISHED,
                )
                self.event(order, users['accountant01'], LabOrder.Status.REPORT_REVIEW, LabOrder.Status.INVOICED_CLOSED, '会计开票并办结')

        self.stdout.write(self.style.SUCCESS('已创建/更新角色账号：10 个'))
        self.stdout.write(self.style.SUCCESS(f'统一初始密码：{self.demo_password}'))
        self.stdout.write(self.style.SUCCESS(f'已创建模拟订单：{len(created)} 笔'))
        demo_count = LabOrder.objects.filter(order_no__startswith='DEMO-2026-').count()
        self.stdout.write(self.style.SUCCESS(f'当前 DEMO-2026 订单总数：{demo_count}'))

    def ensure_users(self):
        user_model = get_user_model()
        role_specs = {
            'sales01': ('销售一号', '销售'),
            'sales02': ('销售二号', '销售'),
            'sales03': ('销售三号', '销售'),
            'business01': ('商务评审一号', '商务'),
            'tech01': ('技术评审一号', '技术'),
            'quality01': ('质量专员一号', '质量部'),
            'suzhou_lab01': ('苏州实验室负责人', '苏州实验室'),
            'jiangyin_lab01': ('江阴实验室负责人', '江阴实验室'),
            'general_manager01': ('总经理一号', '总经理'),
            'accountant01': ('会计一号', '会计'),
        }
        users = {}
        for username, (display_name, role_name) in role_specs.items():
            group, _ = Group.objects.get_or_create(name=role_name)
            user, _ = user_model.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': display_name,
                    'email': f'{username}@aroundtest.com',
                    'is_staff': True,
                    'is_active': True,
                },
            )
            user.first_name = display_name
            user.email = f'{username}@aroundtest.com'
            user.is_staff = True
            user.is_active = True
            user.set_password(self.demo_password)
            user.save()
            user.groups.add(group)
            users[username] = user
        return users

    def scenario_for(self, index):
        if index <= 18:
            return {
                'order_status': LabOrder.Status.INVOICED_CLOSED,
                'review': 'passed',
                'stage_rank': 6,
                'report': 'approved',
                'invoice': True,
            }
        if index <= 24:
            return {
                'order_status': LabOrder.Status.REPORT_REVIEW,
                'review': 'passed',
                'stage_rank': 6,
                'report': 'approved',
                'invoice': False,
            }
        if index <= 32:
            return {
                'order_status': LabOrder.Status.REPORT_REVIEW,
                'review': 'passed',
                'stage_rank': 5,
                'report': 'sales_pending',
                'invoice': False,
            }
        if index <= 39:
            return {
                'order_status': LabOrder.Status.REPORT_REVIEW,
                'review': 'passed',
                'stage_rank': 5,
                'report': 'gm_pending',
                'invoice': False,
            }
        if index <= 45:
            return {
                'order_status': LabOrder.Status.REPORT_REVIEW,
                'review': 'passed',
                'stage_rank': 5,
                'report': 'sales_rejected' if index % 2 else 'gm_rejected',
                'invoice': False,
            }
        if index <= 52:
            return {
                'order_status': LabOrder.Status.TESTING,
                'review': 'passed',
                'stage_rank': 3,
                'report': None,
                'invoice': False,
            }
        if index <= 56:
            return {
                'order_status': LabOrder.Status.SCHEDULING,
                'review': 'passed',
                'stage_rank': 2,
                'report': None,
                'invoice': False,
            }
        if index <= 58:
            return {
                'order_status': LabOrder.Status.REVIEW_REJECTED,
                'review': 'rejected',
                'stage_rank': 1,
                'report': None,
                'invoice': False,
            }
        return {
            'order_status': LabOrder.Status.CANCELLED,
            'review': 'rejected',
            'stage_rank': 1,
            'report': None,
            'invoice': False,
        }

    def create_schedules(self, order, mode, users, created_at, rnd):
        if mode == LabOrder.ExecutionMode.SUZHOU:
            types = [SchedulePlan.TestType.SUZHOU]
        elif mode == LabOrder.ExecutionMode.JIANGYIN:
            types = [SchedulePlan.TestType.JIANGYIN]
        elif mode == LabOrder.ExecutionMode.OUTSOURCE:
            types = [SchedulePlan.TestType.OUTSOURCE]
        else:
            types = [SchedulePlan.TestType.SUZHOU, SchedulePlan.TestType.JIANGYIN, SchedulePlan.TestType.OUTSOURCE]

        names = {
            SchedulePlan.TestType.SUZHOU: '苏州实验室内部可靠性试验',
            SchedulePlan.TestType.JIANGYIN: '江阴实验室机械环境试验',
            SchedulePlan.TestType.OUTSOURCE: '外部委托专项试验',
        }
        schedules = []
        for offset, test_type in enumerate(types):
            schedule = SchedulePlan.objects.create(
                order=order,
                test_type=test_type,
                lab_manager=users['suzhou_lab01'] if test_type == SchedulePlan.TestType.SUZHOU else users['jiangyin_lab01'] if test_type == SchedulePlan.TestType.JIANGYIN else None,
                outsource_factory=f'华东外协实验室{rnd.randint(1, 5)}号' if test_type == SchedulePlan.TestType.OUTSOURCE else '',
                outsource_price=Decimal(8000 + rnd.randint(0, 12000)) if test_type == SchedulePlan.TestType.OUTSOURCE else Decimal('0.00'),
                outsource_cycle=7 + rnd.randint(0, 8) if test_type == SchedulePlan.TestType.OUTSOURCE else None,
                plan_start_time=created_at + timezone.timedelta(days=3 + offset),
                plan_end_time=created_at + timezone.timedelta(days=9 + offset + rnd.randint(0, 4)),
                schedule_status=SchedulePlan.Status.FINISHED if order.order_status in [LabOrder.Status.REPORT_REVIEW, LabOrder.Status.INVOICED_CLOSED] else SchedulePlan.Status.RUNNING if order.order_status == LabOrder.Status.TESTING else SchedulePlan.Status.NEW,
                quality_user=users['quality01'],
                remark=names[test_type],
            )
            schedules.append(schedule)
        return schedules

    def create_samples_and_experiments(self, order, schedules, users, created_at, scenario):
        experiments = []
        for index, schedule in enumerate(schedules, start=1):
            sample = Sample.objects.create(
                order=order,
                schedule=schedule,
                sample_no=f'SMP-{order.order_no[-4:]}-{index}',
                sample_name=f'{order.project_name} 样品{index}',
                sample_spec='量产前验证样件' if index % 2 else '客户送检样件',
                sample_count=2 + index,
                storage_condition='常温' if index % 3 else '冷藏/避光',
                actual_arrive_time=created_at + timezone.timedelta(days=4),
                sample_status=Sample.Status.FINISHED if scenario['stage_rank'] >= 5 else Sample.Status.TESTING,
                quality_user=users['quality01'],
            )
            operator = users['suzhou_lab01'] if schedule.test_type == SchedulePlan.TestType.SUZHOU else users['jiangyin_lab01'] if schedule.test_type == SchedulePlan.TestType.JIANGYIN else users['quality01']
            experiments.append(
                Experiment.objects.create(
                    order=order,
                    schedule=schedule,
                    sample=sample,
                    test_item_list=schedule.remark,
                    test_standard='GB/T 2423; ISO 16750',
                    test_start_time=created_at + timezone.timedelta(days=5),
                    test_end_time=created_at + timezone.timedelta(days=10) if scenario['stage_rank'] >= 5 else None,
                    test_operator=operator,
                    test_raw_data='温度、湿度、振动、外观及功能检查数据均已记录。',
                    test_conclusion_temp='检测过程正常，样品满足当前阶段判定要求。',
                    test_status=Experiment.Status.FINISHED if scenario['stage_rank'] >= 5 else Experiment.Status.RUNNING,
                    test_type=schedule.test_type,
                )
            )
        self.event(order, users['quality01'], LabOrder.Status.SCHEDULING, order.order_status, '样品登记并进入试验执行')
        return experiments

    def create_report(self, order, experiment, users, created_at, scenario):
        report_status = TestReport.Status.SALES_REVIEW
        remake_count = 0
        if scenario['report'] == 'gm_pending':
            report_status = TestReport.Status.GM_REVIEW
        elif scenario['report'] == 'approved':
            report_status = TestReport.Status.APPROVED
        elif scenario['report'] in ['sales_rejected', 'gm_rejected']:
            report_status = TestReport.Status.REJECTED
            remake_count = 1
        report = TestReport.objects.create(
            order=order,
            test_record=experiment,
            report_no=f'RPT-{order.order_no}',
            report_file_url=f'/media/reports/RPT-{order.order_no}.pdf',
            final_conclusion='依据送检样品、检测标准与原始数据，本次检测结论已形成正式报告。',
            report_status=report_status,
            remake_count=remake_count,
            create_quality_user=users['quality01'],
        )
        self.event(order, users['quality01'], LabOrder.Status.TESTING, LabOrder.Status.REPORT_REVIEW, '质量部出具检测报告')
        return report

    def event(self, order, actor, from_status, to_status, note):
        WorkflowEvent.objects.create(
            order=order,
            actor=actor,
            event_type=WorkflowEvent.EventType.STATUS,
            from_status=str(from_status or ''),
            to_status=str(to_status or ''),
            note=note,
        )
