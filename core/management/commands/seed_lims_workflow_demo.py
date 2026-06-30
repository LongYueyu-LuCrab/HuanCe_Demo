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
    help = '创建演示账号和 100 笔覆盖 LIMS 全流程节点的模拟订单'

    demo_password = 'HuanCe@2026'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-existing',
            action='store_true',
            help='保留已有 DEMO-2026 订单，不先清理重建',
        )

    def handle(self, *args, **options):
        rnd = Random(20260628)
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

        scenarios = self.build_scenarios()
        created = []

        for index, scenario in enumerate(scenarios, start=1):
            customer_name, contact, phone = customers[(index - 1) % len(customers)]
            project_name, demand = projects[(index - 1) % len(projects)]
            sales_user = users[f'sales{((index - 1) % 3) + 1:02d}']
            created_at = now - timezone.timedelta(days=105 - index)
            quote = Decimal(12800 + (index * 1730) % 92000).quantize(Decimal('0.01'))
            order = LabOrder.objects.create(
                order_no=f'DEMO-2026-{index:04d}',
                customer_name=customer_name,
                customer_contact=contact,
                customer_phone=phone,
                project_name=f'{project_name}-{index:03d}',
                test_demand=f'{demand}。执行标准：{standards[index % len(standards)]}。',
                total_quote=quote,
                expect_sample_arrive=created_at + timezone.timedelta(days=2),
                expect_delivery_time=created_at + timezone.timedelta(days=12 + index % 10),
                order_status=scenario['order_status'],
                execution_mode=scenario['mode'],
                sale_user=sales_user,
                create_by=sales_user.username,
                update_by=sales_user.username,
                remark='加急；全流程演示订单' if index % 9 == 0 else '全流程演示订单',
            )
            created.append(order)
            self.event(order, sales_user, '', LabOrder.Status.PENDING_REVIEW, '销售下单，进入商务技术评审')

            if scenario['review'] == 'none':
                continue

            self.create_review(order, users, created_at, scenario['review'], quote)
            if scenario['review'] == 'rejected':
                self.event(order, users['business01'], LabOrder.Status.PENDING_REVIEW, order.order_status, scenario['label'])
                continue

            self.event(order, users['tech01'], LabOrder.Status.PENDING_REVIEW, LabOrder.Status.SCHEDULING, '商务技术评审通过，商务完成任务书与订单分配')
            schedules = self.create_schedules(order, users, created_at, scenario, rnd)

            if scenario.get('change_scene'):
                self.create_change(order, schedules[0], users, sales_user, created_at, scenario)

            if scenario['stage'] < 3:
                continue

            experiments = self.create_samples_and_experiments(order, schedules, users, created_at, scenario)
            self.event(order, users['quality01'], LabOrder.Status.SCHEDULING, LabOrder.Status.TESTING, scenario['sample_event'])

            if scenario['stage'] < 5:
                continue

            report = self.create_report(order, experiments[0], users, created_at, scenario)
            self.event(order, users['quality01'], LabOrder.Status.TESTING, LabOrder.Status.REPORT_REVIEW, '质量部出具检测报告')
            self.create_audits(report, users, created_at, scenario)

            if scenario.get('invoice'):
                Invoice.objects.create(
                    order=order,
                    report=report,
                    invoice_no=f'INV-DEMO-2026-{index:04d}',
                    invoice_amount=quote,
                    invoice_type='增值税专票' if index % 3 else '增值税普票',
                    invoice_date=created_at + timezone.timedelta(days=14),
                    pay_status=Invoice.PayStatus.PAID if index % 4 else Invoice.PayStatus.UNPAID,
                    finance_user=users['accountant01'],
                    order_finish_flag=Invoice.FinishFlag.FINISHED,
                )
                self.event(order, users['accountant01'], LabOrder.Status.REPORT_REVIEW, LabOrder.Status.INVOICED_CLOSED, '会计开票并办结，流程退出')

        self.stdout.write(self.style.SUCCESS('已创建/更新演示账号。'))
        self.stdout.write(self.style.SUCCESS(f'统一演示密码：{self.demo_password}，董事长 zhihao 密码：123456'))
        self.stdout.write(self.style.SUCCESS(f'已创建模拟订单：{len(created)} 笔'))
        self.stdout.write(self.style.SUCCESS(f'DEMO-2026 订单总数：{LabOrder.objects.filter(order_no__startswith="DEMO-2026-").count()}'))

    def ensure_users(self):
        user_model = get_user_model()
        role_specs = {
            'zhihao': ('董事长', '董事长', '123456', True),
            'sales01': ('销售一号', '销售', self.demo_password, False),
            'sales02': ('销售二号', '销售', self.demo_password, False),
            'sales03': ('销售三号', '销售', self.demo_password, False),
            'business01': ('商务评审一号', '商务', self.demo_password, False),
            'tech01': ('技术评审一号', '技术', self.demo_password, False),
            'quality01': ('质量专员一号', '质量部', self.demo_password, False),
            'suzhou_lab01': ('苏州实验室负责人', '苏州实验室', self.demo_password, False),
            'jiangyin_lab01': ('江阴实验室负责人', '江阴实验室', self.demo_password, False),
            'general_manager01': ('总经理一号', '总经理', self.demo_password, False),
            'accountant01': ('会计一号', '会计', self.demo_password, False),
        }
        users = {}
        for username, (display_name, role_name, password, is_superuser) in role_specs.items():
            group, _ = Group.objects.get_or_create(name=role_name)
            user, _ = user_model.objects.get_or_create(username=username)
            user.first_name = display_name
            user.email = f'{username}@aroundtest.com'
            user.is_staff = True
            user.is_active = True
            user.is_superuser = is_superuser
            user.set_password(password)
            user.save()
            user.groups.clear()
            user.groups.add(group)
            users[username] = user
        legacy_chairman = user_model.objects.filter(username='LuCrab').first()
        if legacy_chairman:
            chairman_group, _ = Group.objects.get_or_create(name='董事长')
            legacy_chairman.first_name = '龙老大'
            legacy_chairman.is_staff = True
            legacy_chairman.is_superuser = True
            legacy_chairman.is_active = True
            legacy_chairman.save()
            legacy_chairman.groups.clear()
            legacy_chairman.groups.add(chairman_group)
        return users

    def build_scenarios(self):
        specs = [
            ('待商务技术评审', 6, LabOrder.Status.PENDING_REVIEW, LabOrder.ExecutionMode.MIXED, 'none', 1),
            ('评审驳回待销售修改', 6, LabOrder.Status.REVIEW_REJECTED, LabOrder.ExecutionMode.MIXED, 'rejected', 1),
            ('评审驳回后退单', 4, LabOrder.Status.CANCELLED, LabOrder.ExecutionMode.MIXED, 'rejected', 1),
            ('苏州实验室排期中', 8, LabOrder.Status.SCHEDULING, LabOrder.ExecutionMode.SUZHOU, 'passed', 2),
            ('江阴实验室排期中', 8, LabOrder.Status.SCHEDULING, LabOrder.ExecutionMode.JIANGYIN, 'passed', 2),
            ('委外厂家确认价格周期', 7, LabOrder.Status.SCHEDULING, LabOrder.ExecutionMode.OUTSOURCE, 'passed', 2),
            ('样品到货前变更待闭环', 7, LabOrder.Status.SCHEDULING, LabOrder.ExecutionMode.MIXED, 'passed', 2),
            ('质量部样品编号登记完成', 7, LabOrder.Status.TESTING, LabOrder.ExecutionMode.MIXED, 'passed', 3),
            ('苏州实验室开始试验', 7, LabOrder.Status.TESTING, LabOrder.ExecutionMode.SUZHOU, 'passed', 4),
            ('江阴实验室开始试验', 7, LabOrder.Status.TESTING, LabOrder.ExecutionMode.JIANGYIN, 'passed', 4),
            ('试验过程中变更待闭环', 5, LabOrder.Status.TESTING, LabOrder.ExecutionMode.MIXED, 'passed', 4),
            ('质量部出报告待销售初审', 6, LabOrder.Status.REPORT_REVIEW, LabOrder.ExecutionMode.MIXED, 'passed', 5),
            ('销售审核报告驳回重制', 4, LabOrder.Status.REPORT_REVIEW, LabOrder.ExecutionMode.SUZHOU, 'passed', 5),
            ('销售通过待总经理终审', 4, LabOrder.Status.REPORT_REVIEW, LabOrder.ExecutionMode.JIANGYIN, 'passed', 5),
            ('总经理终审驳回重制', 3, LabOrder.Status.REPORT_REVIEW, LabOrder.ExecutionMode.OUTSOURCE, 'passed', 5),
            ('总经理终审通过待会计开票', 3, LabOrder.Status.REPORT_REVIEW, LabOrder.ExecutionMode.MIXED, 'passed', 6),
            ('会计开票办结退出系统', 8, LabOrder.Status.INVOICED_CLOSED, LabOrder.ExecutionMode.MIXED, 'passed', 6),
        ]
        scenarios = []
        for label, count, status, mode, review, stage in specs:
            for _ in range(count):
                scenario = {
                    'label': label,
                    'order_status': status,
                    'mode': mode,
                    'review': review,
                    'stage': stage,
                    'schedule_status': SchedulePlan.Status.NEW,
                    'sample_status': Sample.Status.REGISTERED,
                    'experiment_status': Experiment.Status.WAITING,
                    'report_status': None,
                    'audit_path': None,
                    'invoice': False,
                    'sample_event': '质量部填写样品编号，等待开始试验',
                }
                if '变更待闭环' in label:
                    scenario['schedule_status'] = SchedulePlan.Status.CHANGE_PENDING
                    scenario['change_scene'] = (
                        ChangeRequest.Scene.DURING_TEST if '试验过程' in label else ChangeRequest.Scene.BEFORE_SAMPLE
                    )
                    scenario['change_status'] = ChangeRequest.Status.PENDING
                if stage >= 4:
                    scenario['schedule_status'] = SchedulePlan.Status.RUNNING
                    scenario['sample_status'] = Sample.Status.TESTING
                    scenario['experiment_status'] = Experiment.Status.RUNNING
                    scenario['sample_event'] = '样品登记完成，实验室开始试验'
                if '试验过程中变更' in label:
                    scenario['schedule_status'] = SchedulePlan.Status.CHANGE_PENDING
                    scenario['change_scene'] = ChangeRequest.Scene.DURING_TEST
                    scenario['change_status'] = ChangeRequest.Status.PENDING
                if stage >= 5:
                    scenario['schedule_status'] = SchedulePlan.Status.FINISHED
                    scenario['sample_status'] = Sample.Status.FINISHED
                    scenario['experiment_status'] = Experiment.Status.FINISHED
                    scenario['sample_event'] = '样品登记完成，试验执行完成'
                    scenario['report_status'] = TestReport.Status.SALES_REVIEW
                if '销售审核报告驳回' in label:
                    scenario['report_status'] = TestReport.Status.REJECTED
                    scenario['audit_path'] = 'sales_rejected'
                elif '销售通过待总经理终审' in label:
                    scenario['report_status'] = TestReport.Status.GM_REVIEW
                    scenario['audit_path'] = 'sales_approved'
                elif '总经理终审驳回' in label:
                    scenario['report_status'] = TestReport.Status.REJECTED
                    scenario['audit_path'] = 'gm_rejected'
                elif '待会计开票' in label:
                    scenario['report_status'] = TestReport.Status.APPROVED
                    scenario['audit_path'] = 'approved'
                elif '开票办结' in label:
                    scenario['report_status'] = TestReport.Status.APPROVED
                    scenario['audit_path'] = 'approved'
                    scenario['invoice'] = True
                scenarios.append(scenario)
        return scenarios

    def create_review(self, order, users, created_at, result, quote):
        approved = result == 'passed'
        BusinessReview.objects.create(
            order=order,
            biz_review_user=users['business01'],
            tech_review_user=users['tech01'],
            biz_quote_detail=f'商务报价包含试验费、样品管理费、报告编制费，合计 {quote} 元。',
            tech_feasible=approved,
            review_result=approved,
            reject_reason='' if approved else '检测标准或样品信息不完整，需销售补充后重新提交或退单。',
            review_time=created_at + timezone.timedelta(days=1),
        )

    def create_schedules(self, order, users, created_at, scenario, rnd):
        if scenario['mode'] == LabOrder.ExecutionMode.SUZHOU:
            types = [SchedulePlan.TestType.SUZHOU]
        elif scenario['mode'] == LabOrder.ExecutionMode.JIANGYIN:
            types = [SchedulePlan.TestType.JIANGYIN]
        elif scenario['mode'] == LabOrder.ExecutionMode.OUTSOURCE:
            types = [SchedulePlan.TestType.OUTSOURCE]
        else:
            types = [SchedulePlan.TestType.SUZHOU, SchedulePlan.TestType.JIANGYIN, SchedulePlan.TestType.OUTSOURCE]

        remarks = {
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
                outsource_price=Decimal(9000 + rnd.randint(0, 15000)) if test_type == SchedulePlan.TestType.OUTSOURCE else Decimal('0.00'),
                outsource_cycle=7 + rnd.randint(0, 10) if test_type == SchedulePlan.TestType.OUTSOURCE else None,
                plan_start_time=created_at + timezone.timedelta(days=3 + offset),
                plan_end_time=created_at + timezone.timedelta(days=9 + offset + rnd.randint(0, 5)),
                schedule_status=scenario['schedule_status'],
                quality_user=users['quality01'],
                remark=remarks[test_type],
            )
            schedules.append(schedule)
        return schedules

    def create_change(self, order, schedule, users, sales_user, created_at, scenario):
        actor = users['quality01'] if scenario['change_scene'] == ChangeRequest.Scene.DURING_TEST else sales_user
        ChangeRequest.objects.create(
            order=order,
            schedule=schedule,
            change_scene=scenario['change_scene'],
            old_test_demand=order.test_demand,
            new_test_demand=f'{order.test_demand} 客户追加一组复测样品。',
            change_content='客户需求或试验方案调整，质量部需重新确认项目周期表。',
            change_user=actor,
            change_time=created_at + timezone.timedelta(days=4),
            change_status=scenario['change_status'],
        )
        self.event(order, actor, order.order_status, order.order_status, scenario['label'])

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
                sample_status=scenario['sample_status'],
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
                    test_start_time=created_at + timezone.timedelta(days=5) if scenario['experiment_status'] != Experiment.Status.WAITING else None,
                    test_end_time=created_at + timezone.timedelta(days=10) if scenario['experiment_status'] == Experiment.Status.FINISHED else None,
                    test_operator=operator,
                    test_raw_data='温度、湿度、振动、外观及功能检查数据均已记录。',
                    test_conclusion_temp='检测过程正常，样品满足当前阶段判定要求。',
                    test_status=scenario['experiment_status'],
                    test_type=schedule.test_type,
                )
            )
        return experiments

    def create_report(self, order, experiment, users, created_at, scenario):
        remake_count = 1 if scenario['report_status'] == TestReport.Status.REJECTED else 0
        return TestReport.objects.create(
            order=order,
            test_record=experiment,
            report_no=f'RPT-{order.order_no}',
            report_file_url=f'/media/reports/RPT-{order.order_no}.pdf',
            final_conclusion='依据送检样品、检测标准与原始数据，本次检测结论已形成正式报告。',
            report_status=scenario['report_status'],
            remake_count=remake_count,
            create_quality_user=users['quality01'],
        )

    def create_audits(self, report, users, created_at, scenario):
        if scenario['audit_path'] == 'sales_rejected':
            ReportAudit.objects.create(
                report=report,
                audit_level=ReportAudit.Level.SALES,
                audit_user=users['sales01'],
                audit_result=ReportAudit.Result.REJECTED,
                audit_opinion='客户信息或检测项目需质量部重新核对。',
                audit_time=created_at + timezone.timedelta(days=11),
            )
            self.event(report.order, users['sales01'], LabOrder.Status.REPORT_REVIEW, LabOrder.Status.REPORT_REVIEW, '销售初审驳回，退回质量部重制报告')
        elif scenario['audit_path'] in ['sales_approved', 'gm_rejected', 'approved']:
            ReportAudit.objects.create(
                report=report,
                audit_level=ReportAudit.Level.SALES,
                audit_user=users['sales01'],
                audit_result=ReportAudit.Result.APPROVED,
                audit_opinion='销售初审通过，提交总经理终审。',
                audit_time=created_at + timezone.timedelta(days=11),
            )
            if scenario['audit_path'] == 'gm_rejected':
                ReportAudit.objects.create(
                    report=report,
                    audit_level=ReportAudit.Level.GENERAL_MANAGER,
                    audit_user=users['general_manager01'],
                    audit_result=ReportAudit.Result.REJECTED,
                    audit_opinion='重大结论表述需复核，退回质量部重制。',
                    audit_time=created_at + timezone.timedelta(days=12),
                )
                self.event(report.order, users['general_manager01'], LabOrder.Status.REPORT_REVIEW, LabOrder.Status.REPORT_REVIEW, '总经理终审驳回，退回质量部重制报告')
            elif scenario['audit_path'] == 'approved':
                ReportAudit.objects.create(
                    report=report,
                    audit_level=ReportAudit.Level.GENERAL_MANAGER,
                    audit_user=users['general_manager01'],
                    audit_result=ReportAudit.Result.APPROVED,
                    audit_opinion='总经理终审通过，同意进入财务开票。',
                    audit_time=created_at + timezone.timedelta(days=12),
                )
                self.event(report.order, users['general_manager01'], LabOrder.Status.REPORT_REVIEW, LabOrder.Status.REPORT_REVIEW, '总经理终审通过，推送会计开票')

    def event(self, order, actor, from_status, to_status, note):
        WorkflowEvent.objects.create(
            order=order,
            actor=actor,
            event_type=WorkflowEvent.EventType.STATUS,
            from_status=str(from_status or ''),
            to_status=str(to_status or ''),
            note=note,
        )
