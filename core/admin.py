from django.contrib import admin

from .models import (
    BusinessReview,
    ChangeRequest,
    Experiment,
    Invoice,
    LabDevice,
    LabStaffProfile,
    LabOrder,
    OrderDocument,
    ReportAudit,
    Sample,
    SamplePhoto,
    SchedulePlan,
    TestStandard,
    TestReport,
    WorkflowEvent,
)


class BusinessReviewInline(admin.StackedInline):
    model = BusinessReview
    extra = 0
    fields = (
        ('biz_review_user', 'tech_review_user'),
        'biz_quote_detail',
        'tech_feasible',
        'review_result',
        'reject_reason',
        'review_time',
    )


class SchedulePlanInline(admin.TabularInline):
    model = SchedulePlan
    extra = 0
    fields = (
        'test_type',
        'lab_manager',
        'device',
        'assigned_by',
        'outsource_factory',
        'outsource_price',
        'outsource_cycle',
        'plan_start_time',
        'plan_end_time',
        'sample_arrived',
        'sample_arrived_at',
        'sample_confirmed_by',
        'schedule_status',
        'quality_user',
    )


class ChangeRequestInline(admin.TabularInline):
    model = ChangeRequest
    extra = 0
    fields = ('change_scene', 'change_user', 'change_status', 'change_content', 'change_time')


class SampleInline(admin.TabularInline):
    model = Sample
    extra = 0
    fields = ('sample_no', 'sample_name', 'sample_spec', 'sample_count', 'sample_status', 'actual_arrive_time')


class SamplePhotoInline(admin.TabularInline):
    model = SamplePhoto
    extra = 0
    fields = ('schedule', 'original_name', 'file', 'file_size', 'uploaded_by', 'create_time')
    readonly_fields = ('original_name', 'file_size', 'uploaded_by', 'create_time')


class ExperimentInline(admin.TabularInline):
    model = Experiment
    extra = 0
    fields = ('test_item_list', 'sample', 'test_type', 'test_status', 'test_start_time', 'test_end_time')


class TestReportInline(admin.TabularInline):
    model = TestReport
    extra = 0
    fields = ('report_no', 'test_record', 'report_status', 'remake_count', 'create_quality_user')


class WorkflowEventInline(admin.TabularInline):
    model = WorkflowEvent
    extra = 0
    fields = ('event_type', 'actor', 'from_status', 'to_status', 'note', 'create_time')
    readonly_fields = ('create_time',)


class OrderDocumentInline(admin.TabularInline):
    model = OrderDocument
    extra = 0
    fields = ('document_type', 'original_name', 'file', 'file_size', 'uploaded_by', 'create_time')
    readonly_fields = ('original_name', 'file_size', 'uploaded_by', 'create_time')


@admin.register(LabOrder)
class LabOrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_no',
        'customer_name',
        'project_name',
        'industry_category',
        'order_status',
        'execution_mode',
        'workflow_version',
        'lead_lab_manager',
        'expect_sample_arrive',
        'total_quote',
        'sale_user',
    )
    list_filter = ('order_status', 'workflow_version', 'execution_mode', 'industry_category', 'autonomous_execution', 'outsourced_execution')
    search_fields = (
        'order_no', 'customer_name', 'customer_contact', 'customer_phone', 'project_name',
        'test_demand', 'test_method', 'test_standard',
    )
    date_hierarchy = 'create_time'
    readonly_fields = ('create_time', 'update_time')
    fieldsets = (
        ('订单基础信息', {
            'fields': (
                'order_no',
                ('customer_name', 'customer_contact', 'customer_phone'),
                'project_name',
                'industry_category',
                'test_demand',
                'test_method',
                'test_standard',
                'total_quote',
                'sale_user',
            )
        }),
        ('流程状态', {
            'fields': (
                'order_status',
                'workflow_version',
                'execution_mode',
                ('autonomous_execution', 'outsourced_execution'),
                'lead_lab_manager',
                'sales_confirmed_at',
                'expect_sample_arrive',
                'expect_delivery_time',
            )
        }),
        ('操作留痕', {
            'fields': ('create_by', 'update_by', 'remark', 'create_time', 'update_time')
        }),
    )
    inlines = [
        BusinessReviewInline,
        SchedulePlanInline,
        ChangeRequestInline,
        SampleInline,
        ExperimentInline,
        TestReportInline,
        WorkflowEventInline,
        OrderDocumentInline,
        SamplePhotoInline,
    ]
    actions = ('send_to_scheduling', 'send_to_testing', 'send_to_report_review', 'close_orders')

    @admin.action(description='流转到质量部排期')
    def send_to_scheduling(self, request, queryset):
        for order in queryset:
            order.mark_status(LabOrder.Status.SCHEDULING, request.user, '后台批量流转到质量部排期')

    @admin.action(description='流转到试验执行')
    def send_to_testing(self, request, queryset):
        for order in queryset:
            order.mark_status(LabOrder.Status.TESTING, request.user, '后台批量流转到试验执行')

    @admin.action(description='流转到报告审核')
    def send_to_report_review(self, request, queryset):
        for order in queryset:
            order.mark_status(LabOrder.Status.REPORT_REVIEW, request.user, '后台批量流转到报告审核')

    @admin.action(description='标记为已开票办结')
    def close_orders(self, request, queryset):
        for order in queryset:
            order.mark_status(LabOrder.Status.INVOICED_CLOSED, request.user, '后台批量办结')


@admin.register(BusinessReview)
class BusinessReviewAdmin(admin.ModelAdmin):
    list_display = ('order', 'biz_review_user', 'tech_review_user', 'tech_feasible', 'review_result', 'review_time')
    list_filter = ('tech_feasible', 'review_result')
    search_fields = ('order__order_no', 'order__customer_name', 'biz_quote_detail', 'reject_reason')


@admin.register(SchedulePlan)
class SchedulePlanAdmin(admin.ModelAdmin):
    list_display = ('order', 'test_type', 'lab_manager', 'device', 'outsource_factory', 'plan_start_time', 'plan_end_time', 'schedule_status')
    list_filter = ('test_type', 'schedule_status')
    search_fields = ('order__order_no', 'order__customer_name', 'outsource_factory', 'remark')


@admin.register(LabDevice)
class LabDeviceAdmin(admin.ModelAdmin):
    list_display = ('device_code', 'device_name', 'lab_type', 'device_status', 'model_spec', 'update_time')
    list_filter = ('lab_type', 'device_status')
    search_fields = ('device_code', 'device_name', 'model_spec', 'capability', 'remark')


@admin.register(LabStaffProfile)
class LabStaffProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'lab_type', 'position', 'is_active', 'update_time')
    list_filter = ('lab_type', 'position', 'is_active')
    search_fields = ('user__username', 'user__first_name', 'user__email')


@admin.register(ChangeRequest)
class ChangeRequestAdmin(admin.ModelAdmin):
    list_display = ('order', 'schedule', 'change_scene', 'change_user', 'change_status', 'change_time')
    list_filter = ('change_scene', 'change_status')
    search_fields = ('order__order_no', 'change_content', 'old_test_demand', 'new_test_demand')


@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = (
        'sample_no', 'order', 'sample_name', 'sample_count', 'sample_status',
        'actual_arrive_time', 'outbound_time', 'outbound_by',
    )
    list_filter = ('sample_status',)
    search_fields = ('sample_no', 'sample_name', 'sample_spec', 'order__order_no')


@admin.register(SamplePhoto)
class SamplePhotoAdmin(admin.ModelAdmin):
    list_display = ('order', 'schedule', 'original_name', 'file_size', 'uploaded_by', 'create_time')
    search_fields = ('order__order_no', 'original_name', 'uploaded_by__username')
    readonly_fields = ('file_size', 'uploaded_by', 'create_time')


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('order', 'sample', 'test_type', 'test_status', 'result_status', 'test_start_time', 'test_end_time', 'test_operator')
    list_filter = ('test_type', 'test_status', 'result_status')
    search_fields = ('order__order_no', 'sample__sample_no', 'test_item_list', 'test_standard', 'test_raw_data')


class ReportAuditInline(admin.TabularInline):
    model = ReportAudit
    extra = 0
    fields = ('audit_level', 'audit_user', 'audit_result', 'audit_opinion', 'audit_time')


@admin.register(TestReport)
class TestReportAdmin(admin.ModelAdmin):
    list_display = ('report_no', 'order', 'report_type', 'report_status', 'generated_at', 'remake_count', 'create_quality_user')
    list_filter = ('report_type', 'report_status')
    search_fields = ('report_no', 'order__order_no', 'final_conclusion', 'report_file_url')
    readonly_fields = ('generated_at',)
    inlines = [ReportAuditInline]


@admin.register(ReportAudit)
class ReportAuditAdmin(admin.ModelAdmin):
    list_display = ('report', 'audit_level', 'audit_user', 'audit_result', 'audit_time')
    list_filter = ('audit_level', 'audit_result')
    search_fields = ('report__report_no', 'audit_opinion')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_no', 'order', 'invoice_stage', 'report', 'invoice_amount', 'invoice_type', 'pay_status', 'order_finish_flag')
    list_filter = ('invoice_stage', 'invoice_type', 'pay_status', 'order_finish_flag')
    search_fields = ('invoice_no', 'order__order_no', 'report__report_no')


@admin.register(TestStandard)
class TestStandardAdmin(admin.ModelAdmin):
    list_display = ('industry', 'standard_code', 'standard_name', 'is_active')
    list_filter = ('industry', 'is_active')
    search_fields = ('industry', 'standard_code', 'standard_name', 'description')


@admin.register(WorkflowEvent)
class WorkflowEventAdmin(admin.ModelAdmin):
    list_display = ('order', 'event_type', 'action_code', 'actor', 'schedule', 'from_status', 'to_status', 'create_time')
    list_filter = ('event_type', 'action_code', 'from_status', 'to_status')
    search_fields = ('order__order_no', 'note', 'action_code')
    readonly_fields = ('create_time', 'update_time')
