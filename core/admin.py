from django.contrib import admin

from .models import (
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


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_name', 'phone', 'email', 'updated_at')
    search_fields = ('name', 'contact_name', 'phone', 'email')


class ScheduleItemInline(admin.TabularInline):
    model = ScheduleItem
    extra = 0
    fields = ('resource_type', 'owner_name', 'task_name', 'start_date', 'end_date', 'cost')


@admin.register(SchedulePlan)
class SchedulePlanAdmin(admin.ModelAdmin):
    list_display = ('order', 'version', 'owner', 'start_date', 'end_date', 'approved')
    list_filter = ('approved', 'start_date', 'end_date')
    search_fields = ('order__order_no', 'order__project_name', 'summary')
    inlines = [ScheduleItemInline]


class BusinessReviewInline(admin.StackedInline):
    model = BusinessReview
    extra = 0
    fields = (
        'reviewer',
        ('business_passed', 'technical_passed'),
        'quotation_note',
        'feasibility_note',
        'delivery_note',
        'reviewed_at',
    )


class ChangeRequestInline(admin.TabularInline):
    model = ChangeRequest
    extra = 0
    fields = ('stage', 'requester', 'status', 'reason', 'requested_changes')


class SampleInline(admin.TabularInline):
    model = Sample
    extra = 0
    fields = ('sample_no', 'name', 'quantity', 'received_at', 'storage_location')


class ExperimentInline(admin.TabularInline):
    model = Experiment
    extra = 0
    fields = ('name', 'sample', 'schedule_item', 'executor', 'status', 'started_at', 'finished_at')


class TestReportInline(admin.TabularInline):
    model = TestReport
    extra = 0
    fields = ('report_no', 'version', 'status', 'prepared_by', 'sales_reviewed_by', 'gm_reviewed_by')


class WorkflowEventInline(admin.TabularInline):
    model = WorkflowEvent
    extra = 0
    fields = ('event_type', 'actor', 'from_status', 'to_status', 'note', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(LabOrder)
class LabOrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_no',
        'customer',
        'project_name',
        'status',
        'execution_mode',
        'expected_delivery_date',
        'quoted_amount',
        'is_urgent',
    )
    list_filter = ('status', 'execution_mode', 'is_urgent', 'chairman_visible')
    search_fields = ('order_no', 'project_name', 'customer__name', 'test_requirements')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'closed_at')
    fieldsets = (
        ('订单基础信息', {
            'fields': (
                'order_no',
                'customer',
                'project_name',
                'test_requirements',
                'sales_owner',
                'quoted_amount',
            )
        }),
        ('流程状态', {
            'fields': (
                'status',
                'execution_mode',
                'is_urgent',
                'chairman_visible',
                'expected_sample_arrival',
                'expected_delivery_date',
                'closed_at',
            )
        }),
        ('备注与时间', {
            'fields': ('remark', 'created_at', 'updated_at')
        }),
    )
    inlines = [
        BusinessReviewInline,
        ChangeRequestInline,
        SampleInline,
        ExperimentInline,
        TestReportInline,
        WorkflowEventInline,
    ]
    actions = ('send_to_quality', 'send_to_testing', 'send_to_report', 'close_orders')

    @admin.action(description='流转到质量部排期')
    def send_to_quality(self, request, queryset):
        for order in queryset:
            order.mark_status(LabOrder.Status.QUALITY_SCHEDULING, request.user, '后台批量流转到质量部排期')

    @admin.action(description='流转到试验执行')
    def send_to_testing(self, request, queryset):
        for order in queryset:
            order.mark_status(LabOrder.Status.TESTING, request.user, '后台批量流转到试验执行')

    @admin.action(description='流转到质量部出具报告')
    def send_to_report(self, request, queryset):
        for order in queryset:
            order.mark_status(LabOrder.Status.REPORT_DRAFT, request.user, '后台批量流转到出具报告')

    @admin.action(description='标记为办结')
    def close_orders(self, request, queryset):
        for order in queryset:
            order.mark_status(LabOrder.Status.CLOSED, request.user, '后台批量办结')


@admin.register(BusinessReview)
class BusinessReviewAdmin(admin.ModelAdmin):
    list_display = ('order', 'reviewer', 'business_passed', 'technical_passed', 'reviewed_at')
    list_filter = ('business_passed', 'technical_passed')
    search_fields = ('order__order_no', 'order__project_name', 'quotation_note', 'feasibility_note')


@admin.register(ChangeRequest)
class ChangeRequestAdmin(admin.ModelAdmin):
    list_display = ('order', 'stage', 'requester', 'status', 'updated_at')
    list_filter = ('stage', 'status')
    search_fields = ('order__order_no', 'reason', 'requested_changes')


@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = ('sample_no', 'order', 'name', 'quantity', 'received_at', 'storage_location')
    search_fields = ('sample_no', 'name', 'order__order_no')


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('order', 'name', 'executor', 'status', 'started_at', 'finished_at')
    list_filter = ('status',)
    search_fields = ('order__order_no', 'name', 'executor', 'result_summary')


@admin.register(TestReport)
class TestReportAdmin(admin.ModelAdmin):
    list_display = ('report_no', 'order', 'version', 'status', 'prepared_by', 'sales_reviewed_by', 'gm_reviewed_by')
    list_filter = ('status',)
    search_fields = ('report_no', 'order__order_no', 'conclusion', 'reject_reason')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_no', 'order', 'accountant', 'amount', 'issued_at')
    search_fields = ('invoice_no', 'order__order_no', 'note')


@admin.register(WorkflowEvent)
class WorkflowEventAdmin(admin.ModelAdmin):
    list_display = ('order', 'event_type', 'actor', 'from_status', 'to_status', 'created_at')
    list_filter = ('event_type', 'from_status', 'to_status')
    search_fields = ('order__order_no', 'note')
    readonly_fields = ('created_at', 'updated_at')
