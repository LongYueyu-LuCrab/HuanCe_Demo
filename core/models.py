from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        abstract = True


class Customer(TimeStampedModel):
    name = models.CharField('客户名称', max_length=120)
    contact_name = models.CharField('联系人', max_length=60, blank=True)
    phone = models.CharField('联系电话', max_length=40, blank=True)
    email = models.EmailField('邮箱', blank=True)
    address = models.CharField('地址', max_length=240, blank=True)

    class Meta:
        verbose_name = '客户'
        verbose_name_plural = '客户'
        ordering = ['name']

    def __str__(self):
        return self.name


class LabOrder(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', '销售下单'
        REVIEWING = 'reviewing', '商务技术评审'
        SALES_REVISION = 'sales_revision', '销售修改/退单'
        BUSINESS_ASSIGN = 'business_assign', '商务任务分配'
        QUALITY_SCHEDULING = 'quality_scheduling', '质量部排期'
        CUSTOMER_CONFIRM = 'customer_confirm', '销售确认需求'
        SAMPLE_REGISTER = 'sample_register', '样品编号登记'
        TESTING = 'testing', '试验执行'
        REPORT_DRAFT = 'report_draft', '质量部出具报告'
        SALES_REPORT_REVIEW = 'sales_report_review', '销售审核报告'
        GM_REPORT_REVIEW = 'gm_report_review', '总经理审核报告'
        ACCOUNTING_INVOICE = 'accounting_invoice', '会计开票'
        CLOSED = 'closed', '办结'
        CANCELLED = 'cancelled', '退单'

    class ExecutionMode(models.TextChoices):
        SUZHOU = 'suzhou', '苏州实验室'
        JIANGYIN = 'jiangyin', '江阴实验室'
        OUTSOURCE = 'outsource', '外部委外'
        MIXED = 'mixed', '多路径并行'

    order_no = models.CharField('订单编号', max_length=40, unique=True)
    customer = models.ForeignKey(Customer, verbose_name='客户', on_delete=models.PROTECT)
    project_name = models.CharField('项目名称', max_length=160)
    test_requirements = models.TextField('试验需求')
    sales_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='销售负责人',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_orders',
    )
    status = models.CharField('当前状态', max_length=40, choices=Status.choices, default=Status.DRAFT)
    execution_mode = models.CharField(
        '执行路径',
        max_length=20,
        choices=ExecutionMode.choices,
        default=ExecutionMode.MIXED,
    )
    expected_sample_arrival = models.DateField('预计样品到达日期', null=True, blank=True)
    expected_delivery_date = models.DateField('预计交付日期', null=True, blank=True)
    quoted_amount = models.DecimalField('报价金额', max_digits=12, decimal_places=2, default=0)
    is_urgent = models.BooleanField('加急订单', default=False)
    chairman_visible = models.BooleanField('董事长可查看/审批', default=True)
    closed_at = models.DateTimeField('办结时间', null=True, blank=True)
    remark = models.TextField('备注', blank=True)

    class Meta:
        verbose_name = 'LIMS订单'
        verbose_name_plural = 'LIMS订单'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.order_no} - {self.project_name}'

    def mark_status(self, status, actor=None, note=''):
        old_status = self.status
        self.status = status
        if status == self.Status.CLOSED and self.closed_at is None:
            self.closed_at = timezone.now()
        self.save(update_fields=['status', 'closed_at', 'updated_at'])
        WorkflowEvent.objects.create(
            order=self,
            actor=actor,
            event_type=WorkflowEvent.EventType.STATUS,
            from_status=old_status,
            to_status=status,
            note=note,
        )


class BusinessReview(TimeStampedModel):
    order = models.ForeignKey(LabOrder, verbose_name='订单', on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='评审人', on_delete=models.SET_NULL, null=True, blank=True)
    business_passed = models.BooleanField('商务评审通过', default=False)
    technical_passed = models.BooleanField('技术评审通过', default=False)
    quotation_note = models.TextField('报价说明', blank=True)
    feasibility_note = models.TextField('可行性说明', blank=True)
    delivery_note = models.TextField('交付周期说明', blank=True)
    reviewed_at = models.DateTimeField('评审时间', null=True, blank=True)

    class Meta:
        verbose_name = '商务技术评审'
        verbose_name_plural = '商务技术评审'
        ordering = ['-created_at']

    @property
    def passed(self):
        return self.business_passed and self.technical_passed

    def __str__(self):
        return f'{self.order.order_no} 评审'


class SchedulePlan(TimeStampedModel):
    order = models.OneToOneField(LabOrder, verbose_name='订单', on_delete=models.CASCADE, related_name='schedule_plan')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='质量部负责人', on_delete=models.SET_NULL, null=True, blank=True)
    version = models.PositiveIntegerField('版本号', default=1)
    start_date = models.DateField('计划开始日期', null=True, blank=True)
    end_date = models.DateField('计划完成日期', null=True, blank=True)
    summary = models.TextField('项目总周期说明', blank=True)
    approved = models.BooleanField('周期表已确认', default=False)

    class Meta:
        verbose_name = '项目周期表'
        verbose_name_plural = '项目周期表'

    def __str__(self):
        return f'{self.order.order_no} 周期表 V{self.version}'


class ScheduleItem(TimeStampedModel):
    class ResourceType(models.TextChoices):
        SUZHOU = 'suzhou', '苏州实验室'
        JIANGYIN = 'jiangyin', '江阴实验室'
        OUTSOURCE = 'outsource', '委外供应商'

    plan = models.ForeignKey(SchedulePlan, verbose_name='周期表', on_delete=models.CASCADE, related_name='items')
    resource_type = models.CharField('执行主体', max_length=20, choices=ResourceType.choices)
    owner_name = models.CharField('项目负责人/供应商', max_length=100)
    task_name = models.CharField('试验任务', max_length=160)
    start_date = models.DateField('开始日期', null=True, blank=True)
    end_date = models.DateField('结束日期', null=True, blank=True)
    cost = models.DecimalField('成本/报价', max_digits=12, decimal_places=2, default=0)
    note = models.TextField('排期说明', blank=True)

    class Meta:
        verbose_name = '排期明细'
        verbose_name_plural = '排期明细'
        ordering = ['start_date', 'id']

    def __str__(self):
        return f'{self.get_resource_type_display()} - {self.task_name}'


class ChangeRequest(TimeStampedModel):
    class ChangeStage(models.TextChoices):
        BEFORE_SAMPLE = 'before_sample', '样品到货前'
        DURING_TEST = 'during_test', '试验进行中'

    class Status(models.TextChoices):
        SUBMITTED = 'submitted', '已提交'
        ACCEPTED = 'accepted', '已接收'
        APPLIED = 'applied', '已应用并回流排期'
        REJECTED = 'rejected', '已驳回'

    order = models.ForeignKey(LabOrder, verbose_name='订单', on_delete=models.CASCADE, related_name='change_requests')
    stage = models.CharField('变更阶段', max_length=20, choices=ChangeStage.choices)
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='发起人', on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField('变更原因')
    requested_changes = models.TextField('变更内容')
    status = models.CharField('处理状态', max_length=20, choices=Status.choices, default=Status.SUBMITTED)

    class Meta:
        verbose_name = '订单更改单'
        verbose_name_plural = '订单更改单'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.order.order_no} {self.get_stage_display()}变更'


class Sample(TimeStampedModel):
    order = models.ForeignKey(LabOrder, verbose_name='订单', on_delete=models.CASCADE, related_name='samples')
    sample_no = models.CharField('样品编号', max_length=60, unique=True)
    name = models.CharField('样品名称', max_length=120)
    quantity = models.PositiveIntegerField('数量', default=1)
    received_at = models.DateTimeField('收样时间', null=True, blank=True)
    storage_location = models.CharField('存放位置', max_length=120, blank=True)
    note = models.TextField('样品备注', blank=True)

    class Meta:
        verbose_name = '样品台账'
        verbose_name_plural = '样品台账'
        ordering = ['sample_no']

    def __str__(self):
        return self.sample_no


class Experiment(TimeStampedModel):
    class Status(models.TextChoices):
        WAITING = 'waiting', '待开始'
        RUNNING = 'running', '试验中'
        CHANGING = 'changing', '变更回流'
        FINISHED = 'finished', '已完成'

    order = models.ForeignKey(LabOrder, verbose_name='订单', on_delete=models.CASCADE, related_name='experiments')
    sample = models.ForeignKey(Sample, verbose_name='样品', on_delete=models.SET_NULL, null=True, blank=True, related_name='experiments')
    schedule_item = models.ForeignKey(ScheduleItem, verbose_name='排期明细', on_delete=models.SET_NULL, null=True, blank=True, related_name='experiments')
    name = models.CharField('试验项目', max_length=160)
    executor = models.CharField('执行人/供应商', max_length=100, blank=True)
    status = models.CharField('试验状态', max_length=20, choices=Status.choices, default=Status.WAITING)
    started_at = models.DateTimeField('开始时间', null=True, blank=True)
    finished_at = models.DateTimeField('完成时间', null=True, blank=True)
    result_summary = models.TextField('结果摘要', blank=True)

    class Meta:
        verbose_name = '试验记录'
        verbose_name_plural = '试验记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.order.order_no} - {self.name}'


class TestReport(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', '质量部出具'
        SALES_REVIEW = 'sales_review', '销售审核'
        GM_REVIEW = 'gm_review', '总经理审核'
        APPROVED = 'approved', '审核通过'
        REJECTED = 'rejected', '驳回重制'

    order = models.ForeignKey(LabOrder, verbose_name='订单', on_delete=models.CASCADE, related_name='reports')
    report_no = models.CharField('报告编号', max_length=60, unique=True)
    version = models.PositiveIntegerField('版本号', default=1)
    status = models.CharField('报告状态', max_length=20, choices=Status.choices, default=Status.DRAFT)
    prepared_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='编制人', on_delete=models.SET_NULL, null=True, blank=True, related_name='prepared_reports')
    sales_reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='销售审核人', on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_reviewed_reports')
    gm_reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='总经理审核人', on_delete=models.SET_NULL, null=True, blank=True, related_name='gm_reviewed_reports')
    conclusion = models.TextField('报告结论', blank=True)
    reject_reason = models.TextField('驳回原因', blank=True)

    class Meta:
        verbose_name = '检测报告'
        verbose_name_plural = '检测报告'
        ordering = ['-created_at']

    def __str__(self):
        return self.report_no


class Invoice(TimeStampedModel):
    order = models.OneToOneField(LabOrder, verbose_name='订单', on_delete=models.CASCADE, related_name='invoice')
    invoice_no = models.CharField('发票编号', max_length=80, unique=True)
    accountant = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='会计', on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField('开票金额', max_digits=12, decimal_places=2)
    issued_at = models.DateField('开票日期', null=True, blank=True)
    note = models.TextField('财务备注', blank=True)

    class Meta:
        verbose_name = '财务开票'
        verbose_name_plural = '财务开票'

    def __str__(self):
        return self.invoice_no


class WorkflowEvent(TimeStampedModel):
    class EventType(models.TextChoices):
        STATUS = 'status', '状态流转'
        REVIEW = 'review', '审核'
        CHANGE = 'change', '变更'
        COMMENT = 'comment', '备注'
        CHAIRMAN = 'chairman', '董事长操作'

    order = models.ForeignKey(LabOrder, verbose_name='订单', on_delete=models.CASCADE, related_name='events')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='操作人', on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField('事件类型', max_length=20, choices=EventType.choices, default=EventType.COMMENT)
    from_status = models.CharField('原状态', max_length=40, blank=True)
    to_status = models.CharField('新状态', max_length=40, blank=True)
    note = models.TextField('说明', blank=True)

    class Meta:
        verbose_name = '流程日志'
        verbose_name_plural = '流程日志'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.order.order_no} {self.get_event_type_display()}'
