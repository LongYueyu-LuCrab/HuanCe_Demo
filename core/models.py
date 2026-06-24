from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    create_time = models.DateTimeField('创建时间', auto_now_add=True)
    update_time = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        abstract = True


class LabOrder(TimeStampedModel):
    class Status(models.IntegerChoices):
        PENDING_REVIEW = 1, '待评审'
        REVIEW_REJECTED = 2, '评审驳回'
        SCHEDULING = 3, '排期中'
        TESTING = 4, '试验中'
        REPORT_REVIEW = 5, '报告审核中'
        INVOICED_CLOSED = 6, '已开票办结'
        CANCELLED = 7, '退单'

    class ExecutionMode(models.IntegerChoices):
        SUZHOU = 1, '苏州内部实验室'
        JIANGYIN = 2, '江阴内部实验室'
        OUTSOURCE = 3, '外部委外'
        MIXED = 4, '多路径并行'

    order_no = models.CharField('订单唯一业务编号', max_length=64, unique=True)
    customer_name = models.CharField('客户单位名称', max_length=100)
    customer_contact = models.CharField('客户对接人', max_length=50, blank=True)
    customer_phone = models.CharField('客户联系电话', max_length=20, blank=True)
    project_name = models.CharField('项目名称', max_length=160, blank=True)
    test_demand = models.TextField('详细试验需求、检测标准、检测项目清单')
    total_quote = models.DecimalField('订单总报价金额', max_digits=12, decimal_places=2, default=0)
    expect_sample_arrive = models.DateTimeField('预估样品送达时间', null=True, blank=True)
    expect_delivery_time = models.DateTimeField('预估交付时间', null=True, blank=True)
    order_status = models.PositiveSmallIntegerField('订单状态', choices=Status.choices, default=Status.PENDING_REVIEW)
    execution_mode = models.PositiveSmallIntegerField('试验执行路径', choices=ExecutionMode.choices, default=ExecutionMode.MIXED)
    sale_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='下单销售',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lims_sales_orders',
    )
    create_by = models.CharField('创建人账号', max_length=32, blank=True)
    update_by = models.CharField('更新人账号', max_length=32, blank=True)
    remark = models.CharField('订单备注', max_length=500, blank=True)

    class Meta:
        db_table = 'lims_sales_order'
        verbose_name = 'LIMS 销售订单'
        verbose_name_plural = 'LIMS 销售订单'
        ordering = ['-create_time']

    @property
    def status(self):
        return self.order_status

    @property
    def sales_owner(self):
        return self.sale_user

    @property
    def expected_delivery_date(self):
        return self.expect_delivery_time

    @property
    def is_urgent(self):
        return '加急' in (self.remark or '')

    def __str__(self):
        title = self.project_name or self.customer_name
        return f'{self.order_no} - {title}'

    def mark_status(self, status, actor=None, note=''):
        old_status = self.order_status
        self.order_status = status
        if actor:
            self.update_by = actor.username
        self.save(update_fields=['order_status', 'update_by', 'update_time'])
        WorkflowEvent.objects.create(
            order=self,
            actor=actor,
            event_type=WorkflowEvent.EventType.STATUS,
            from_status=str(old_status or ''),
            to_status=str(status or ''),
            note=note,
        )


class BusinessReview(TimeStampedModel):
    order = models.ForeignKey(LabOrder, verbose_name='销售订单', on_delete=models.CASCADE, related_name='reviews')
    biz_review_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='商务评审人',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lims_biz_reviews',
    )
    tech_review_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='技术评审人',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lims_tech_reviews',
    )
    biz_quote_detail = models.TextField('商务分项报价明细', blank=True)
    tech_feasible = models.BooleanField('技术可行性', default=True)
    review_result = models.BooleanField('评审结果', default=True)
    reject_reason = models.CharField('驳回原因', max_length=1000, blank=True)
    review_time = models.DateTimeField('评审完成时间', null=True, blank=True)

    class Meta:
        db_table = 'lims_biz_review'
        verbose_name = '商务技术评审'
        verbose_name_plural = '商务技术评审'
        ordering = ['-create_time']

    def __str__(self):
        return f'{self.order.order_no} 评审'


class SchedulePlan(TimeStampedModel):
    class TestType(models.IntegerChoices):
        SUZHOU = 1, '苏州内部实验室'
        JIANGYIN = 2, '江阴内部实验室'
        OUTSOURCE = 3, '外部委外'

    class Status(models.IntegerChoices):
        NEW = 1, '新建'
        CHANGE_PENDING = 2, '变更待调整'
        RUNNING = 3, '执行中'
        FINISHED = 4, '试验完成'

    order = models.ForeignKey(LabOrder, verbose_name='销售订单', on_delete=models.CASCADE, related_name='schedules')
    test_type = models.PositiveSmallIntegerField('试验执行类型', choices=TestType.choices, default=TestType.SUZHOU)
    lab_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='实验室负责人',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lims_lab_schedules',
    )
    outsource_factory = models.CharField('委外厂家名称', max_length=100, blank=True)
    outsource_price = models.DecimalField('委外试验单价', max_digits=12, decimal_places=2, default=0)
    outsource_cycle = models.PositiveIntegerField('委外交付周期（天）', null=True, blank=True)
    plan_start_time = models.DateTimeField('试验计划开始时间', null=True, blank=True)
    plan_end_time = models.DateTimeField('试验计划完成时间', null=True, blank=True)
    schedule_status = models.PositiveSmallIntegerField('排期状态', choices=Status.choices, default=Status.NEW)
    quality_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='质量部操作人员',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lims_quality_schedules',
    )
    remark = models.CharField('排期备注', max_length=500, blank=True)

    class Meta:
        db_table = 'lims_project_schedule'
        verbose_name = '项目周期排期'
        verbose_name_plural = '项目周期排期'
        ordering = ['plan_start_time', 'id']

    def __str__(self):
        return f'{self.order.order_no} {self.get_test_type_display()}排期'


class ChangeRequest(TimeStampedModel):
    class Scene(models.IntegerChoices):
        BEFORE_SAMPLE = 1, '样品到货前变更'
        DURING_TEST = 2, '试验过程中变更'

    class Status(models.IntegerChoices):
        PENDING = 1, '待调整排期'
        APPLIED = 2, '排期已更新完成'

    order = models.ForeignKey(LabOrder, verbose_name='销售订单', on_delete=models.CASCADE, related_name='change_requests')
    schedule = models.ForeignKey(SchedulePlan, verbose_name='项目排期', on_delete=models.SET_NULL, null=True, blank=True, related_name='change_requests')
    change_scene = models.PositiveSmallIntegerField('变更场景', choices=Scene.choices, default=Scene.BEFORE_SAMPLE)
    old_test_demand = models.TextField('变更前原始试验需求', blank=True)
    new_test_demand = models.TextField('变更后调整试验需求', blank=True)
    change_content = models.CharField('变更详细描述', max_length=1000)
    change_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='变更发起人',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lims_order_changes',
    )
    change_time = models.DateTimeField('变更提交时间', default=timezone.now)
    change_status = models.PositiveSmallIntegerField('变更状态', choices=Status.choices, default=Status.PENDING)

    class Meta:
        db_table = 'lims_order_change'
        verbose_name = '订单变更单'
        verbose_name_plural = '订单变更单'
        ordering = ['-create_time']

    def __str__(self):
        return f'{self.order.order_no} {self.get_change_scene_display()}'


class Sample(TimeStampedModel):
    class Status(models.IntegerChoices):
        REGISTERED = 1, '已登记待试验'
        TESTING = 2, '试验中'
        FINISHED = 3, '试验完成'
        RETURNED = 4, '已归还客户'

    order = models.ForeignKey(LabOrder, verbose_name='销售订单', on_delete=models.CASCADE, related_name='samples')
    schedule = models.ForeignKey(SchedulePlan, verbose_name='项目排期', on_delete=models.SET_NULL, null=True, blank=True, related_name='samples')
    sample_no = models.CharField('全局唯一样品编号', max_length=64, unique=True)
    sample_name = models.CharField('样品名称', max_length=100)
    sample_spec = models.CharField('样品规格型号', max_length=200, blank=True)
    sample_count = models.PositiveIntegerField('样品数量', default=1)
    storage_condition = models.CharField('样品存储条件', max_length=200, blank=True)
    actual_arrive_time = models.DateTimeField('样品实际送达入库时间', null=True, blank=True)
    sample_status = models.PositiveSmallIntegerField('样品状态', choices=Status.choices, default=Status.REGISTERED)
    quality_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='登记质量人员',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lims_registered_samples',
    )

    class Meta:
        db_table = 'lims_sample_info'
        verbose_name = '样品信息登记'
        verbose_name_plural = '样品信息登记'
        ordering = ['sample_no']

    def __str__(self):
        return self.sample_no


class Experiment(TimeStampedModel):
    class Status(models.IntegerChoices):
        WAITING = 1, '待开展'
        RUNNING = 2, '试验中'
        FINISHED = 3, '试验完成待出报告'

    order = models.ForeignKey(LabOrder, verbose_name='销售订单', on_delete=models.CASCADE, related_name='experiments')
    schedule = models.ForeignKey(SchedulePlan, verbose_name='项目排期', on_delete=models.SET_NULL, null=True, blank=True, related_name='experiments')
    sample = models.ForeignKey(Sample, verbose_name='样品', on_delete=models.SET_NULL, null=True, blank=True, related_name='experiments')
    test_item_list = models.TextField('实际开展检测项目清单')
    test_standard = models.CharField('执行检测标准号', max_length=500, blank=True)
    test_start_time = models.DateTimeField('试验实际开始时间', null=True, blank=True)
    test_end_time = models.DateTimeField('试验实际结束时间', null=True, blank=True)
    test_operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='试验操作人员',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lims_test_records',
    )
    test_raw_data = models.TextField('原始检测数据、数值记录', blank=True)
    test_conclusion_temp = models.CharField('试验临时初步结论', max_length=1000, blank=True)
    test_status = models.PositiveSmallIntegerField('试验状态', choices=Status.choices, default=Status.WAITING)
    test_type = models.PositiveSmallIntegerField('试验执行类型', choices=SchedulePlan.TestType.choices, default=SchedulePlan.TestType.SUZHOU)

    class Meta:
        db_table = 'lims_test_record'
        verbose_name = '试验执行记录'
        verbose_name_plural = '试验执行记录'
        ordering = ['-create_time']

    def __str__(self):
        return f'{self.order.order_no} - {self.test_item_list[:20]}'


class TestReport(TimeStampedModel):
    class Status(models.IntegerChoices):
        DRAFT = 1, '草稿'
        SALES_REVIEW = 2, '待销售初审'
        GM_REVIEW = 3, '待总经理终审'
        REJECTED = 4, '审核驳回重制'
        APPROVED = 5, '审核通过待开票'

    order = models.ForeignKey(LabOrder, verbose_name='销售订单', on_delete=models.CASCADE, related_name='reports')
    test_record = models.ForeignKey(Experiment, verbose_name='试验记录', on_delete=models.SET_NULL, null=True, blank=True, related_name='reports')
    report_no = models.CharField('全局唯一报告编号', max_length=64, unique=True)
    report_file_url = models.CharField('报告 PDF 文件存储地址', max_length=500, blank=True)
    final_conclusion = models.TextField('检测最终正式结论', blank=True)
    report_status = models.PositiveSmallIntegerField('报告状态', choices=Status.choices, default=Status.DRAFT)
    remake_count = models.PositiveIntegerField('驳回重制次数统计', default=0)
    create_quality_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='出具报告质量人员',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lims_created_reports',
    )

    class Meta:
        db_table = 'lims_test_report'
        verbose_name = '检测报告'
        verbose_name_plural = '检测报告'
        ordering = ['-create_time']

    def __str__(self):
        return self.report_no


class ReportAudit(TimeStampedModel):
    class Level(models.IntegerChoices):
        SALES = 1, '销售初审'
        GENERAL_MANAGER = 2, '总经理终审'

    class Result(models.IntegerChoices):
        REJECTED = 0, '驳回'
        APPROVED = 1, '通过'

    report = models.ForeignKey(TestReport, verbose_name='检测报告', on_delete=models.CASCADE, related_name='audits')
    audit_level = models.PositiveSmallIntegerField('审核层级', choices=Level.choices)
    audit_user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='审核操作人', on_delete=models.SET_NULL, null=True, blank=True)
    audit_result = models.PositiveSmallIntegerField('审核结果', choices=Result.choices)
    audit_opinion = models.CharField('审核意见、修改要求', max_length=1000, blank=True)
    audit_time = models.DateTimeField('审核操作时间', default=timezone.now)

    class Meta:
        db_table = 'lims_report_audit'
        verbose_name = '报告多级审核记录'
        verbose_name_plural = '报告多级审核记录'
        ordering = ['-audit_time']

    def __str__(self):
        return f'{self.report.report_no} {self.get_audit_level_display()}'


class Invoice(TimeStampedModel):
    class PayStatus(models.IntegerChoices):
        UNPAID = 0, '未收款'
        PAID = 1, '已回款'

    class FinishFlag(models.IntegerChoices):
        UNFINISHED = 0, '未办结'
        FINISHED = 1, '全部流程完成'

    order = models.ForeignKey(LabOrder, verbose_name='销售订单', on_delete=models.CASCADE, related_name='invoices')
    report = models.ForeignKey(TestReport, verbose_name='检测报告', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    invoice_no = models.CharField('发票号码', max_length=64, unique=True)
    invoice_amount = models.DecimalField('开票金额', max_digits=12, decimal_places=2)
    invoice_type = models.CharField('发票类型', max_length=32, blank=True)
    invoice_date = models.DateTimeField('发票开具日期', null=True, blank=True)
    pay_status = models.PositiveSmallIntegerField('回款状态', choices=PayStatus.choices, default=PayStatus.UNPAID)
    finance_user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='操作开票会计', on_delete=models.SET_NULL, null=True, blank=True)
    order_finish_flag = models.PositiveSmallIntegerField('订单办结标记', choices=FinishFlag.choices, default=FinishFlag.UNFINISHED)

    class Meta:
        db_table = 'lims_finance_invoice'
        verbose_name = '财务开票结算'
        verbose_name_plural = '财务开票结算'

    def __str__(self):
        return self.invoice_no


class WorkflowEvent(TimeStampedModel):
    class EventType(models.TextChoices):
        STATUS = 'status', '状态流转'
        REVIEW = 'review', '审核'
        CHANGE = 'change', '变更'
        COMMENT = 'comment', '备注'
        CHAIRMAN = 'chairman', '董事长操作'

    order = models.ForeignKey(LabOrder, verbose_name='销售订单', on_delete=models.CASCADE, related_name='events')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='操作人', on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField('事件类型', max_length=20, choices=EventType.choices, default=EventType.COMMENT)
    from_status = models.CharField('原状态', max_length=40, blank=True)
    to_status = models.CharField('新状态', max_length=40, blank=True)
    note = models.TextField('说明', blank=True)

    class Meta:
        db_table = 'lims_workflow_event'
        verbose_name = '流程操作日志'
        verbose_name_plural = '流程操作日志'
        ordering = ['-create_time']

    def __str__(self):
        return f'{self.order.order_no} {self.get_event_type_display()}'
