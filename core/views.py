import json
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseNotFound, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import BusinessReview, ChangeRequest, Experiment, Invoice, LabOrder, ReportAudit, Sample, SchedulePlan, TestReport, WorkflowEvent


ROLE_SALES = '销售'
ROLE_BUSINESS = '商务'
ROLE_TECH = '技术'
ROLE_QUALITY = '质量部'
ROLE_SUZHOU_LAB = '苏州实验室'
ROLE_JIANGYIN_LAB = '江阴实验室'
ROLE_OUTSOURCE = '委外供应商'
ROLE_GENERAL_MANAGER = '总经理'
ROLE_ACCOUNTING = '会计'
ROLE_CHAIRMAN = '董事长'
VALID_ROLES = [
    ROLE_SALES,
    ROLE_BUSINESS,
    ROLE_TECH,
    ROLE_QUALITY,
    ROLE_SUZHOU_LAB,
    ROLE_JIANGYIN_LAB,
    ROLE_OUTSOURCE,
    ROLE_GENERAL_MANAGER,
    ROLE_ACCOUNTING,
    ROLE_CHAIRMAN,
]


def frontend(request):
    index_path = settings.BASE_DIR / 'static' / 'frontend' / 'index.html'
    if not index_path.exists():
        return HttpResponseNotFound(
            'Vue frontend has not been built. Run: cd frontend && pnpm build'
        )
    return HttpResponse(index_path.read_text(encoding='utf-8'))


def _is_chairman(user):
    return bool(
        user
        and user.is_authenticated
        and (user.is_superuser or user.groups.filter(name=ROLE_CHAIRMAN).exists())
    )


def _roles(user):
    if not user.is_authenticated:
        return []
    valid_role_set = set(VALID_ROLES)
    roles = [
        name
        for name in user.groups.values_list('name', flat=True)
        if name in valid_role_set
    ]
    if _is_chairman(user) and ROLE_CHAIRMAN not in roles:
        roles.insert(0, ROLE_CHAIRMAN)
    return roles


def _display_user(user):
    if not user:
        return ''
    return user.first_name or user.username


def _can_view_finance(user):
    roles = set(_roles(user))
    return bool(_is_chairman(user) or ROLE_GENERAL_MANAGER in roles or ROLE_ACCOUNTING in roles)


def _user_payload(user):
    if not user.is_authenticated:
        return {'authenticated': False}
    roles = _roles(user)
    return {
        'authenticated': True,
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'display_name': user.first_name or user.username,
        'roles': roles,
        'is_chairman': _is_chairman(user),
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
    }


def _orders_for_user(user):
    orders = LabOrder.objects.select_related('sale_user')
    if _is_chairman(user):
        return orders

    roles = set(_roles(user))
    query = Q()
    if ROLE_SALES in roles:
        query |= Q(sale_user=user)
    if ROLE_BUSINESS in roles or ROLE_TECH in roles:
        query |= Q(order_status__in=[LabOrder.Status.PENDING_REVIEW, LabOrder.Status.SCHEDULING])
    if ROLE_QUALITY in roles:
        query |= Q(order_status__in=[
            LabOrder.Status.SCHEDULING,
            LabOrder.Status.TESTING,
            LabOrder.Status.REPORT_REVIEW,
        ])
    if ROLE_SUZHOU_LAB in roles:
        query |= Q(schedules__test_type=SchedulePlan.TestType.SUZHOU, schedules__lab_manager=user)
    if ROLE_JIANGYIN_LAB in roles:
        query |= Q(schedules__test_type=SchedulePlan.TestType.JIANGYIN, schedules__lab_manager=user)
    if ROLE_OUTSOURCE in roles:
        query |= Q(execution_mode__in=[LabOrder.ExecutionMode.OUTSOURCE, LabOrder.ExecutionMode.MIXED])
    if ROLE_GENERAL_MANAGER in roles:
        query |= Q()
        return orders
    if ROLE_ACCOUNTING in roles:
        query |= Q(reports__report_status=TestReport.Status.APPROVED) | Q(invoices__isnull=False)

    if not query:
        return orders.none()
    return orders.filter(query).distinct()


def _order_payload(order):
    delivery = order.expect_delivery_time
    if delivery:
        delivery_value = delivery.date().isoformat()
    else:
        delivery_value = ''

    return {
        'order_no': order.order_no,
        'customer': order.customer_name,
        'contact': order.customer_contact,
        'phone': order.customer_phone,
        'project_name': order.project_name,
        'test_demand': order.test_demand,
        'status': order.get_order_status_display(),
        'status_key': order.order_status,
        'execution_mode': order.get_execution_mode_display(),
        'expected_delivery_date': delivery_value,
        'total_quote': str(order.total_quote),
        'is_urgent': order.is_urgent,
        'sales_owner': order.sale_user.first_name or order.sale_user.username
        if order.sale_user
        else '',
        'created_at': order.create_time.strftime('%Y-%m-%d %H:%M') if order.create_time else '',
    }


def _report_payload(report):
    return {
        'report_no': report.report_no,
        'order_no': report.order.order_no,
        'customer': report.order.customer_name,
        'project_name': report.order.project_name,
        'status': report.get_report_status_display(),
        'status_key': report.report_status,
        'conclusion': report.final_conclusion,
        'remake_count': report.remake_count,
        'quality_user': report.create_quality_user.first_name or report.create_quality_user.username
        if report.create_quality_user
        else '',
    }


def _invoice_payload(invoice):
    order = invoice.order
    report = invoice.report
    return {
        'invoice_no': invoice.invoice_no,
        'order_no': order.order_no,
        'report_no': report.report_no if report else '',
        'customer': order.customer_name,
        'project_name': order.project_name,
        'invoice_amount': str(invoice.invoice_amount),
        'invoice_type': invoice.invoice_type,
        'invoice_date': invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else '',
        'pay_status': invoice.get_pay_status_display(),
        'finish_status': invoice.get_order_finish_flag_display(),
        'finance_user': invoice.finance_user.first_name or invoice.finance_user.username
        if invoice.finance_user
        else '',
    }


def _pending_invoice_payload(report):
    order = report.order
    return {
        'report_no': report.report_no,
        'order_no': order.order_no,
        'customer': order.customer_name,
        'project_name': order.project_name,
        'invoice_amount': str(order.total_quote),
        'invoice_type': '待确认',
        'invoice_date': '',
        'pay_status': '待开票',
        'finish_status': order.get_order_status_display(),
        'finance_user': '',
    }


def _schedule_payload(schedule):
    order = schedule.order
    return {
        'order_no': order.order_no,
        'customer': order.customer_name,
        'project_name': order.project_name,
        'status': order.get_order_status_display(),
        'test_type': schedule.get_test_type_display(),
        'start_time': schedule.plan_start_time.strftime('%Y-%m-%d') if schedule.plan_start_time else '',
        'end_time': schedule.plan_end_time.strftime('%Y-%m-%d') if schedule.plan_end_time else '',
        'schedule_status': schedule.get_schedule_status_display(),
        'remark': schedule.remark,
    }


def _sample_payload(sample):
    order = sample.order
    schedule = sample.schedule
    return {
        'sample_no': sample.sample_no,
        'order_no': order.order_no,
        'customer': order.customer_name,
        'project_name': order.project_name,
        'sample_name': sample.sample_name,
        'sample_spec': sample.sample_spec,
        'sample_count': sample.sample_count,
        'storage_condition': sample.storage_condition,
        'actual_arrive_time': sample.actual_arrive_time.strftime('%Y-%m-%d') if sample.actual_arrive_time else '',
        'sample_status': sample.get_sample_status_display(),
        'test_type': schedule.get_test_type_display() if schedule else '',
        'quality_user': _display_user(sample.quality_user),
    }


def _change_payload(change):
    order = change.order
    return {
        'order_no': order.order_no,
        'customer': order.customer_name,
        'project_name': order.project_name,
        'scene': change.get_change_scene_display(),
        'status': change.get_change_status_display(),
        'content': change.change_content,
        'change_user': _display_user(change.change_user),
        'change_time': change.change_time.strftime('%Y-%m-%d %H:%M') if change.change_time else '',
    }


def _review_payload(review):
    order = review.order
    return {
        'order_no': order.order_no,
        'customer': order.customer_name,
        'project_name': order.project_name,
        'biz_user': _display_user(review.biz_review_user),
        'tech_user': _display_user(review.tech_review_user),
        'result': '通过' if review.review_result else '驳回',
        'tech_feasible': '可行' if review.tech_feasible else '不可行',
        'reject_reason': review.reject_reason,
        'review_time': review.review_time.strftime('%Y-%m-%d %H:%M') if review.review_time else '',
    }


def _workflow_payload(event):
    order = event.order
    return {
        'order_no': order.order_no,
        'customer': order.customer_name,
        'project_name': order.project_name,
        'actor': _display_user(event.actor),
        'event_type': event.get_event_type_display(),
        'from_status': event.from_status,
        'to_status': event.to_status,
        'note': event.note,
        'create_time': event.create_time.strftime('%Y-%m-%d %H:%M') if event.create_time else '',
    }


def _lab_payload(test_type, name, related_orders=None, user=None):
    schedules = SchedulePlan.objects.select_related('order').filter(test_type=test_type).order_by('plan_start_time')
    if related_orders is not None:
        schedules = schedules.filter(order__in=related_orders)
    if user is not None and not _is_chairman(user):
        roles = set(_roles(user))
        can_view_lab = ROLE_QUALITY in roles or ROLE_GENERAL_MANAGER in roles
        if ROLE_SUZHOU_LAB in roles and test_type == SchedulePlan.TestType.SUZHOU:
            can_view_lab = True
            schedules = schedules.filter(lab_manager=user)
        elif ROLE_JIANGYIN_LAB in roles and test_type == SchedulePlan.TestType.JIANGYIN:
            can_view_lab = True
            schedules = schedules.filter(lab_manager=user)
        if not can_view_lab:
            schedules = schedules.none()
    active_statuses = [SchedulePlan.Status.RUNNING, SchedulePlan.Status.CHANGE_PENDING]
    active_schedules = schedules.filter(schedule_status__in=active_statuses)
    future_schedules = schedules.exclude(schedule_status=SchedulePlan.Status.FINISHED)

    device_names = {
        SchedulePlan.TestType.SUZHOU: ['20吨台', '50吨台', '三综合试验箱'],
        SchedulePlan.TestType.JIANGYIN: ['振动台', '盐雾试验箱', '高低温湿热箱'],
    }[test_type]
    active_list = list(active_schedules[:3])
    future_list = list(future_schedules[3:9])

    devices = []
    for index, device_name in enumerate(device_names):
        schedule = active_list[index] if index < len(active_list) else None
        devices.append({
            'name': device_name,
            'status': '运行中' if schedule else '空闲',
            'order_no': schedule.order.order_no if schedule else '',
            'project_name': schedule.order.project_name if schedule else '',
            'end_time': schedule.plan_end_time.strftime('%Y-%m-%d') if schedule and schedule.plan_end_time else '',
            'future_orders': [_schedule_payload(item) for item in future_list[index::len(device_names)][:3]],
        })

    return {
        'name': name,
        'devices': devices,
        'orders': [_schedule_payload(item) for item in schedules],
    }


def _pending_reports_for_user(user, related_orders):
    reports = TestReport.objects.select_related('order', 'create_quality_user').filter(order__in=related_orders)
    if _is_chairman(user):
        return reports.exclude(report_status=TestReport.Status.APPROVED)
    roles = set(_roles(user))
    query = Q()
    if ROLE_SALES in roles:
        query |= Q(report_status=TestReport.Status.SALES_REVIEW)
    if ROLE_GENERAL_MANAGER in roles:
        query |= Q(report_status=TestReport.Status.GM_REVIEW)
    if ROLE_QUALITY in roles:
        query |= Q(report_status__in=[TestReport.Status.DRAFT, TestReport.Status.REJECTED])
    if not query:
        return reports.none()
    return reports.filter(query)


def _next_order_no():
    prefix = f'LIMS-{date.today().year}-'
    last_order = LabOrder.objects.filter(order_no__startswith=prefix).order_by('-order_no').first()
    if not last_order:
        return f'{prefix}0001'
    try:
        next_number = int(last_order.order_no.rsplit('-', 1)[1]) + 1
    except (IndexError, ValueError):
        next_number = LabOrder.objects.filter(order_no__startswith=prefix).count() + 1
    return f'{prefix}{next_number:04d}'


def _parse_datetime(value):
    if not value:
        return None
    try:
        parsed_date = date.fromisoformat(value)
        parsed = datetime.combine(parsed_date, time.min)
    except ValueError:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed)
    return parsed


def _json_payload(request):
    try:
        return json.loads(request.body.decode('utf-8') or '{}'), None
    except json.JSONDecodeError:
        return {}, JsonResponse({'ok': False, 'error': '请求格式错误'}, status=400, json_dumps_params={'ensure_ascii': False})


def _has_any_role(user, *roles):
    user_roles = set(_roles(user))
    return _is_chairman(user) or any(role in user_roles for role in roles)


def _require_auth(request):
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': '请先登录'}, status=401, json_dumps_params={'ensure_ascii': False})
    return None


def _require_role(user, *roles):
    if not _has_any_role(user, *roles):
        return JsonResponse({'ok': False, 'error': '当前岗位无权执行此操作'}, status=403, json_dumps_params={'ensure_ascii': False})
    return None


def _get_order(payload):
    order_no = (payload.get('order_no') or '').strip()
    if not order_no:
        return None, JsonResponse({'ok': False, 'error': '缺少订单号'}, status=400, json_dumps_params={'ensure_ascii': False})
    try:
        return LabOrder.objects.select_related('sale_user').get(order_no=order_no), None
    except LabOrder.DoesNotExist:
        return None, JsonResponse({'ok': False, 'error': '订单不存在'}, status=404, json_dumps_params={'ensure_ascii': False})


def _get_report(payload):
    report_no = (payload.get('report_no') or '').strip()
    if not report_no:
        return None, JsonResponse({'ok': False, 'error': '缺少报告号'}, status=400, json_dumps_params={'ensure_ascii': False})
    try:
        return TestReport.objects.select_related('order').get(report_no=report_no), None
    except TestReport.DoesNotExist:
        return None, JsonResponse({'ok': False, 'error': '报告不存在'}, status=404, json_dumps_params={'ensure_ascii': False})


def _status_response(message, order=None):
    payload = {'ok': True, 'message': message}
    if order:
        payload['order'] = _order_payload(order)
    return JsonResponse(payload, json_dumps_params={'ensure_ascii': False})


def _event(order, actor, note, from_status=None, to_status=None, event_type=WorkflowEvent.EventType.STATUS):
    WorkflowEvent.objects.create(
        order=order,
        actor=actor,
        event_type=event_type,
        from_status=str(from_status or ''),
        to_status=str(to_status or order.order_status or ''),
        note=note,
    )


def _next_sample_no(order):
    return f'SMP-{order.order_no}-{order.samples.count() + 1:02d}'


def _next_report_no(order):
    return f'RPT-{order.order_no}-{order.reports.count() + 1:02d}'


def _next_invoice_no(order):
    return f'INV-{order.order_no}-{order.invoices.count() + 1:02d}'


def _first_user_in_group(role_name):
    return get_user_model().objects.filter(groups__name=role_name, is_active=True).first()


def current_user(request):
    return JsonResponse(_user_payload(request.user), json_dumps_params={'ensure_ascii': False})


@csrf_exempt
def lims_login(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': '请求格式错误'}, status=400, json_dumps_params={'ensure_ascii': False})

    username = payload.get('username', '').strip()
    password = payload.get('password', '')
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({'ok': False, 'error': '用户名或密码错误'}, status=400, json_dumps_params={'ensure_ascii': False})
    if not user.is_active:
        return JsonResponse({'ok': False, 'error': '账号已停用'}, status=403, json_dumps_params={'ensure_ascii': False})

    login(request, user)
    return JsonResponse({'ok': True, 'user': _user_payload(user)}, json_dumps_params={'ensure_ascii': False})


@csrf_exempt
def lims_logout(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    logout(request)
    return JsonResponse({'ok': True})


@csrf_exempt
def add_employee(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    if not _is_chairman(request.user):
        return JsonResponse({'ok': False, 'error': '仅董事长可以添加员工'}, status=403, json_dumps_params={'ensure_ascii': False})

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': '请求格式错误'}, status=400, json_dumps_params={'ensure_ascii': False})

    username = payload.get('username', '').strip()
    password = payload.get('password', '').strip()
    email = payload.get('email', '').strip()
    display_name = payload.get('display_name', '').strip()
    role = payload.get('role', '').strip()

    if not username or not password:
        return JsonResponse({'ok': False, 'error': '用户名和密码必填'}, status=400, json_dumps_params={'ensure_ascii': False})

    user_model = get_user_model()
    if user_model.objects.filter(username=username).exists():
        return JsonResponse({'ok': False, 'error': '用户名已存在'}, status=400, json_dumps_params={'ensure_ascii': False})

    employee = user_model.objects.create_user(
        username=username,
        password=password,
        email=email,
        first_name=display_name,
        is_staff=True,
    )
    if role:
        group, _ = Group.objects.get_or_create(name=role)
        employee.groups.add(group)

    return JsonResponse(
        {
            'ok': True,
            'employee': {
                'id': employee.id,
                'username': employee.username,
                'display_name': employee.first_name or employee.username,
                'email': employee.email,
                'role': role,
            },
        },
        json_dumps_params={'ensure_ascii': False},
    )


@csrf_exempt
def create_order(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': '请先登录'}, status=401, json_dumps_params={'ensure_ascii': False})

    roles = set(_roles(request.user))
    if not (_is_chairman(request.user) or ROLE_SALES in roles):
        return JsonResponse({'ok': False, 'error': '仅销售或董事长可以下单'}, status=403, json_dumps_params={'ensure_ascii': False})

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': '请求格式错误'}, status=400, json_dumps_params={'ensure_ascii': False})

    customer_name = payload.get('customer_name', '').strip()
    project_name = payload.get('project_name', '').strip()
    test_demand = payload.get('test_requirements', '').strip()
    customer_contact = payload.get('contact_name', '').strip()
    customer_phone = payload.get('phone', '').strip()
    expect_sample_arrive = _parse_datetime(payload.get('expected_sample_arrival'))
    expect_delivery_time = _parse_datetime(payload.get('expected_delivery_date'))

    if not customer_name or not project_name or not test_demand:
        return JsonResponse({'ok': False, 'error': '客户名称、项目名称、试验需求必填'}, status=400, json_dumps_params={'ensure_ascii': False})

    try:
        total_quote = Decimal(str(payload.get('quoted_amount') or '0'))
    except InvalidOperation:
        return JsonResponse({'ok': False, 'error': '报价金额格式错误'}, status=400, json_dumps_params={'ensure_ascii': False})

    remark = '销售前台下单，等待商务技术评审。'
    if payload.get('is_urgent'):
        remark = f'加急；{remark}'

    order = LabOrder.objects.create(
        order_no=_next_order_no(),
        customer_name=customer_name,
        customer_contact=customer_contact,
        customer_phone=customer_phone,
        project_name=project_name,
        test_demand=test_demand,
        sale_user=request.user,
        order_status=LabOrder.Status.PENDING_REVIEW,
        expect_sample_arrive=expect_sample_arrive,
        expect_delivery_time=expect_delivery_time,
        total_quote=total_quote,
        create_by=request.user.username,
        update_by=request.user.username,
        remark=remark,
    )
    WorkflowEvent.objects.create(
        order=order,
        actor=request.user,
        event_type=WorkflowEvent.EventType.STATUS,
        to_status=str(order.order_status),
        note='销售下单，进入商务技术评审。',
    )
    return JsonResponse({'ok': True, 'order': _order_payload(order)}, json_dumps_params={'ensure_ascii': False})


@csrf_exempt
@transaction.atomic
def lims_action(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    auth_error = _require_auth(request)
    if auth_error:
        return auth_error

    payload, parse_error = _json_payload(request)
    if parse_error:
        return parse_error

    action = (payload.get('action') or '').strip()
    handlers = {
        'review_pass': _action_review_pass,
        'review_reject': _action_review_reject,
        'order_update': _action_order_update,
        'order_cancel': _action_order_cancel,
        'sales_confirm': _action_sales_confirm,
        'create_change': _action_create_change,
        'schedule_assign': _action_schedule_assign,
        'process_change': _action_process_change,
        'register_sample': _action_register_sample,
        'start_test': _action_start_test,
        'submit_test': _action_submit_test,
        'issue_report': _action_issue_report,
        'report_sales_pass': _action_report_sales_pass,
        'report_sales_reject': _action_report_sales_reject,
        'report_gm_pass': _action_report_gm_pass,
        'report_gm_reject': _action_report_gm_reject,
        'invoice_create': _action_invoice_create,
        'invoice_pay': _action_invoice_pay,
    }
    handler = handlers.get(action)
    if not handler:
        return JsonResponse({'ok': False, 'error': '未知流程动作'}, status=400, json_dumps_params={'ensure_ascii': False})
    return handler(request, payload)


def _action_review_pass(request, payload):
    role_error = _require_role(request.user, ROLE_BUSINESS, ROLE_TECH)
    if role_error:
        return role_error
    order, error = _get_order(payload)
    if error:
        return error
    if order.order_status != LabOrder.Status.PENDING_REVIEW:
        return JsonResponse({'ok': False, 'error': '只有待评审订单可以评审通过'}, status=400, json_dumps_params={'ensure_ascii': False})
    BusinessReview.objects.create(
        order=order,
        biz_review_user=request.user if ROLE_BUSINESS in _roles(request.user) else _first_user_in_group(ROLE_BUSINESS),
        tech_review_user=request.user if ROLE_TECH in _roles(request.user) else _first_user_in_group(ROLE_TECH),
        biz_quote_detail=payload.get('biz_quote_detail') or '商务技术联合评审通过。',
        tech_feasible=True,
        review_result=True,
        review_time=timezone.now(),
    )
    order.mark_status(LabOrder.Status.SCHEDULING, request.user, '商务技术评审通过，进入商务任务分配与质量部排期')
    return _status_response('评审通过，订单已进入排期', order)


def _action_review_reject(request, payload):
    role_error = _require_role(request.user, ROLE_BUSINESS, ROLE_TECH)
    if role_error:
        return role_error
    order, error = _get_order(payload)
    if error:
        return error
    if order.order_status != LabOrder.Status.PENDING_REVIEW:
        return JsonResponse({'ok': False, 'error': '只有待评审订单可以驳回'}, status=400, json_dumps_params={'ensure_ascii': False})
    reason = payload.get('reject_reason') or '评审不通过，退回销售补充信息。'
    BusinessReview.objects.create(
        order=order,
        biz_review_user=request.user if ROLE_BUSINESS in _roles(request.user) else _first_user_in_group(ROLE_BUSINESS),
        tech_review_user=request.user if ROLE_TECH in _roles(request.user) else _first_user_in_group(ROLE_TECH),
        biz_quote_detail=payload.get('biz_quote_detail') or '',
        tech_feasible=bool(payload.get('tech_feasible', False)),
        review_result=False,
        reject_reason=reason,
        review_time=timezone.now(),
    )
    order.mark_status(LabOrder.Status.REVIEW_REJECTED, request.user, f'商务技术评审驳回：{reason}')
    return _status_response('评审已驳回，订单回到销售', order)


def _action_order_update(request, payload):
    role_error = _require_role(request.user, ROLE_SALES)
    if role_error:
        return role_error
    order, error = _get_order(payload)
    if error:
        return error
    if not _is_chairman(request.user) and order.sale_user_id != request.user.id:
        return JsonResponse({'ok': False, 'error': '销售只能修改自己的订单'}, status=403, json_dumps_params={'ensure_ascii': False})
    if order.order_status not in [LabOrder.Status.PENDING_REVIEW, LabOrder.Status.REVIEW_REJECTED]:
        return JsonResponse({'ok': False, 'error': '当前订单状态不可修改'}, status=400, json_dumps_params={'ensure_ascii': False})
    order.customer_name = payload.get('customer_name') or order.customer_name
    order.customer_contact = payload.get('contact_name') or order.customer_contact
    order.customer_phone = payload.get('phone') or order.customer_phone
    order.project_name = payload.get('project_name') or order.project_name
    order.test_demand = payload.get('test_demand') or payload.get('test_requirements') or order.test_demand
    if payload.get('quoted_amount') not in [None, '']:
        order.total_quote = Decimal(str(payload.get('quoted_amount')))
    order.expect_sample_arrive = _parse_datetime(payload.get('expected_sample_arrival')) or order.expect_sample_arrive
    order.expect_delivery_time = _parse_datetime(payload.get('expected_delivery_date')) or order.expect_delivery_time
    order.order_status = LabOrder.Status.PENDING_REVIEW
    order.update_by = request.user.username
    order.save()
    _event(order, request.user, '销售修改订单后重新提交商务技术评审')
    return _status_response('订单已修改并重新提交评审', order)


def _action_order_cancel(request, payload):
    role_error = _require_role(request.user, ROLE_SALES)
    if role_error:
        return role_error
    order, error = _get_order(payload)
    if error:
        return error
    if not _is_chairman(request.user) and order.sale_user_id != request.user.id:
        return JsonResponse({'ok': False, 'error': '销售只能退自己的订单'}, status=403, json_dumps_params={'ensure_ascii': False})
    if order.order_status not in [LabOrder.Status.PENDING_REVIEW, LabOrder.Status.REVIEW_REJECTED]:
        return JsonResponse({'ok': False, 'error': '当前订单状态不可退单'}, status=400, json_dumps_params={'ensure_ascii': False})
    order.mark_status(LabOrder.Status.CANCELLED, request.user, payload.get('reason') or '销售退单，流程终止')
    return _status_response('订单已退单', order)


def _action_sales_confirm(request, payload):
    role_error = _require_role(request.user, ROLE_SALES)
    if role_error:
        return role_error
    order, error = _get_order(payload)
    if error:
        return error
    if not _is_chairman(request.user) and order.sale_user_id != request.user.id:
        return JsonResponse({'ok': False, 'error': '销售只能确认自己的订单'}, status=403, json_dumps_params={'ensure_ascii': False})
    if order.order_status != LabOrder.Status.SCHEDULING:
        return JsonResponse({'ok': False, 'error': '只有排期中订单可以确认需求'}, status=400, json_dumps_params={'ensure_ascii': False})
    _event(order, request.user, payload.get('note') or '销售确认样品与需求无变更，流转质量部样品登记')
    return _status_response('销售已确认无变更', order)


def _action_create_change(request, payload):
    role_error = _require_role(request.user, ROLE_SALES, ROLE_QUALITY, ROLE_SUZHOU_LAB, ROLE_JIANGYIN_LAB)
    if role_error:
        return role_error
    order, error = _get_order(payload)
    if error:
        return error
    scene = int(payload.get('change_scene') or ChangeRequest.Scene.BEFORE_SAMPLE)
    schedule = order.schedules.first()
    if schedule:
        schedule.schedule_status = SchedulePlan.Status.CHANGE_PENDING
        schedule.save(update_fields=['schedule_status', 'update_time'])
    change = ChangeRequest.objects.create(
        order=order,
        schedule=schedule,
        change_scene=scene,
        old_test_demand=order.test_demand,
        new_test_demand=payload.get('new_test_demand') or order.test_demand,
        change_content=payload.get('change_content') or '订单需求发生变更，回流质量部重新调整排期。',
        change_user=request.user,
        change_time=timezone.now(),
        change_status=ChangeRequest.Status.PENDING,
    )
    order.mark_status(LabOrder.Status.SCHEDULING, request.user, f'创建变更单：{change.change_content}')
    return _status_response('变更单已创建，回流质量部排期', order)


def _action_schedule_assign(request, payload):
    role_error = _require_role(request.user, ROLE_QUALITY)
    if role_error:
        return role_error
    order, error = _get_order(payload)
    if error:
        return error
    if order.order_status not in [LabOrder.Status.SCHEDULING, LabOrder.Status.TESTING]:
        return JsonResponse({'ok': False, 'error': '当前订单不可排期'}, status=400, json_dumps_params={'ensure_ascii': False})
    test_type = int(payload.get('test_type') or SchedulePlan.TestType.SUZHOU)
    manager = None
    if test_type == SchedulePlan.TestType.SUZHOU:
        manager = _first_user_in_group(ROLE_SUZHOU_LAB)
    elif test_type == SchedulePlan.TestType.JIANGYIN:
        manager = _first_user_in_group(ROLE_JIANGYIN_LAB)
    SchedulePlan.objects.create(
        order=order,
        test_type=test_type,
        lab_manager=manager,
        outsource_factory=payload.get('outsource_factory') or '',
        outsource_price=Decimal(str(payload.get('outsource_price') or '0')),
        outsource_cycle=int(payload.get('outsource_cycle') or 0) or None,
        plan_start_time=_parse_datetime(payload.get('plan_start_time')) or timezone.now(),
        plan_end_time=_parse_datetime(payload.get('plan_end_time')) or (timezone.now() + timezone.timedelta(days=7)),
        schedule_status=SchedulePlan.Status.NEW,
        quality_user=request.user,
        remark=payload.get('remark') or '质量部排期分配',
    )
    order.order_status = LabOrder.Status.SCHEDULING
    order.execution_mode = test_type if test_type in [1, 2, 3] else order.execution_mode
    order.update_by = request.user.username
    order.save()
    _event(order, request.user, '质量部完成试验排期分配，生成项目周期表')
    return _status_response('排期已创建', order)


def _action_process_change(request, payload):
    role_error = _require_role(request.user, ROLE_QUALITY)
    if role_error:
        return role_error
    order, error = _get_order(payload)
    if error:
        return error
    change = order.change_requests.exclude(change_status=ChangeRequest.Status.APPLIED).first()
    if not change:
        return JsonResponse({'ok': False, 'error': '没有待处理变更单'}, status=400, json_dumps_params={'ensure_ascii': False})
    if change.schedule:
        change.schedule.plan_start_time = _parse_datetime(payload.get('plan_start_time')) or change.schedule.plan_start_time
        change.schedule.plan_end_time = _parse_datetime(payload.get('plan_end_time')) or change.schedule.plan_end_time
        change.schedule.schedule_status = SchedulePlan.Status.NEW
        change.schedule.save()
    change.change_status = ChangeRequest.Status.APPLIED
    change.save(update_fields=['change_status', 'update_time'])
    _event(order, request.user, '质量部已处理变更单并更新项目周期表', event_type=WorkflowEvent.EventType.CHANGE)
    return _status_response('变更已闭环', order)


def _action_register_sample(request, payload):
    role_error = _require_role(request.user, ROLE_QUALITY)
    if role_error:
        return role_error
    order, error = _get_order(payload)
    if error:
        return error
    schedule = order.schedules.first()
    if not schedule:
        return JsonResponse({'ok': False, 'error': '请先完成排期'}, status=400, json_dumps_params={'ensure_ascii': False})
    Sample.objects.create(
        order=order,
        schedule=schedule,
        sample_no=payload.get('sample_no') or _next_sample_no(order),
        sample_name=payload.get('sample_name') or f'{order.project_name} 样品',
        sample_spec=payload.get('sample_spec') or '客户送检样品',
        sample_count=int(payload.get('sample_count') or 1),
        storage_condition=payload.get('storage_condition') or '常温',
        actual_arrive_time=_parse_datetime(payload.get('actual_arrive_time')) or timezone.now(),
        sample_status=Sample.Status.REGISTERED,
        quality_user=request.user,
    )
    order.mark_status(LabOrder.Status.TESTING, request.user, '质量部完成样品编号登记，进入试验执行')
    return _status_response('样品已登记', order)


def _action_start_test(request, payload):
    role_error = _require_role(request.user, ROLE_SUZHOU_LAB, ROLE_JIANGYIN_LAB)
    if role_error:
        return role_error
    order, error = _get_order(payload)
    if error:
        return error
    roles = set(_roles(request.user))
    allowed_type = SchedulePlan.TestType.SUZHOU if ROLE_SUZHOU_LAB in roles else SchedulePlan.TestType.JIANGYIN
    schedule = order.schedules.filter(test_type=allowed_type, lab_manager=request.user).first()
    if not schedule:
        return JsonResponse({'ok': False, 'error': '没有分配给当前实验室负责人的排期'}, status=403, json_dumps_params={'ensure_ascii': False})
    sample = order.samples.filter(schedule=schedule).first()
    if not sample:
        return JsonResponse({'ok': False, 'error': '请先由质量部登记样品'}, status=400, json_dumps_params={'ensure_ascii': False})
    sample.sample_status = Sample.Status.TESTING
    sample.save(update_fields=['sample_status', 'update_time'])
    schedule.schedule_status = SchedulePlan.Status.RUNNING
    schedule.save(update_fields=['schedule_status', 'update_time'])
    Experiment.objects.get_or_create(
        order=order,
        schedule=schedule,
        sample=sample,
        defaults={
            'test_item_list': payload.get('test_item_list') or schedule.remark or order.test_demand,
            'test_standard': payload.get('test_standard') or '待录入',
            'test_start_time': timezone.now(),
            'test_operator': request.user,
            'test_status': Experiment.Status.RUNNING,
            'test_type': schedule.test_type,
        },
    )
    order.mark_status(LabOrder.Status.TESTING, request.user, '实验室开始试验')
    return _status_response('试验已开始', order)


def _action_submit_test(request, payload):
    role_error = _require_role(request.user, ROLE_SUZHOU_LAB, ROLE_JIANGYIN_LAB)
    if role_error:
        return role_error
    order, error = _get_order(payload)
    if error:
        return error
    experiment = order.experiments.filter(test_operator=request.user).exclude(test_status=Experiment.Status.FINISHED).first()
    if not experiment:
        return JsonResponse({'ok': False, 'error': '没有待提交的试验记录'}, status=400, json_dumps_params={'ensure_ascii': False})
    experiment.test_raw_data = payload.get('test_raw_data') or experiment.test_raw_data or '试验数据已录入。'
    experiment.test_conclusion_temp = payload.get('test_conclusion_temp') or '试验完成，等待质量部出报告。'
    experiment.test_end_time = timezone.now()
    experiment.test_status = Experiment.Status.FINISHED
    experiment.save()
    if experiment.sample:
        experiment.sample.sample_status = Sample.Status.FINISHED
        experiment.sample.save(update_fields=['sample_status', 'update_time'])
    if experiment.schedule:
        experiment.schedule.schedule_status = SchedulePlan.Status.FINISHED
        experiment.schedule.save(update_fields=['schedule_status', 'update_time'])
    _event(order, request.user, '实验室提交试验结果，质量部可出具报告')
    return _status_response('试验结果已提交', order)


def _action_issue_report(request, payload):
    role_error = _require_role(request.user, ROLE_QUALITY)
    if role_error:
        return role_error
    order, error = _get_order(payload)
    if error:
        return error
    experiment = order.experiments.order_by('-create_time').first()
    if not experiment:
        return JsonResponse({'ok': False, 'error': '请先完成试验记录'}, status=400, json_dumps_params={'ensure_ascii': False})
    report = TestReport.objects.create(
        order=order,
        test_record=experiment,
        report_no=payload.get('report_no') or _next_report_no(order),
        report_file_url=payload.get('report_file_url') or '',
        final_conclusion=payload.get('final_conclusion') or '检测完成，形成正式检测报告。',
        report_status=TestReport.Status.SALES_REVIEW,
        create_quality_user=request.user,
    )
    order.mark_status(LabOrder.Status.REPORT_REVIEW, request.user, f'质量部出具报告 {report.report_no}，提交销售初审')
    return _status_response('报告已提交销售初审', order)


def _audit_report(request, payload, expected_status, level, result, next_status, note):
    report, error = _get_report(payload)
    if error:
        return error
    if report.report_status != expected_status:
        return JsonResponse({'ok': False, 'error': '报告当前状态不可执行此审核'}, status=400, json_dumps_params={'ensure_ascii': False})
    ReportAudit.objects.create(
        report=report,
        audit_level=level,
        audit_user=request.user,
        audit_result=result,
        audit_opinion=payload.get('audit_opinion') or note,
        audit_time=timezone.now(),
    )
    report.report_status = next_status
    if result == ReportAudit.Result.REJECTED:
        report.remake_count += 1
    report.save()
    _event(report.order, request.user, note, event_type=WorkflowEvent.EventType.REVIEW)
    return JsonResponse({'ok': True, 'message': note, 'report': _report_payload(report)}, json_dumps_params={'ensure_ascii': False})


def _action_report_sales_pass(request, payload):
    role_error = _require_role(request.user, ROLE_SALES)
    if role_error:
        return role_error
    return _audit_report(request, payload, TestReport.Status.SALES_REVIEW, ReportAudit.Level.SALES, ReportAudit.Result.APPROVED, TestReport.Status.GM_REVIEW, '销售初审通过，提交总经理终审')


def _action_report_sales_reject(request, payload):
    role_error = _require_role(request.user, ROLE_SALES)
    if role_error:
        return role_error
    return _audit_report(request, payload, TestReport.Status.SALES_REVIEW, ReportAudit.Level.SALES, ReportAudit.Result.REJECTED, TestReport.Status.REJECTED, '销售初审驳回，退回质量部重制')


def _action_report_gm_pass(request, payload):
    role_error = _require_role(request.user, ROLE_GENERAL_MANAGER)
    if role_error:
        return role_error
    return _audit_report(request, payload, TestReport.Status.GM_REVIEW, ReportAudit.Level.GENERAL_MANAGER, ReportAudit.Result.APPROVED, TestReport.Status.APPROVED, '总经理终审通过，推送会计开票')


def _action_report_gm_reject(request, payload):
    role_error = _require_role(request.user, ROLE_GENERAL_MANAGER)
    if role_error:
        return role_error
    return _audit_report(request, payload, TestReport.Status.GM_REVIEW, ReportAudit.Level.GENERAL_MANAGER, ReportAudit.Result.REJECTED, TestReport.Status.REJECTED, '总经理终审驳回，退回质量部重制')


def _action_invoice_create(request, payload):
    role_error = _require_role(request.user, ROLE_ACCOUNTING)
    if role_error:
        return role_error
    report, error = _get_report(payload)
    if error:
        return error
    if report.report_status != TestReport.Status.APPROVED:
        return JsonResponse({'ok': False, 'error': '只有终审通过的报告可以开票'}, status=400, json_dumps_params={'ensure_ascii': False})
    if report.invoices.exists():
        return JsonResponse({'ok': False, 'error': '该报告已开票'}, status=400, json_dumps_params={'ensure_ascii': False})
    invoice = Invoice.objects.create(
        order=report.order,
        report=report,
        invoice_no=payload.get('invoice_no') or _next_invoice_no(report.order),
        invoice_amount=Decimal(str(payload.get('invoice_amount') or report.order.total_quote)),
        invoice_type=payload.get('invoice_type') or '增值税专票',
        invoice_date=_parse_datetime(payload.get('invoice_date')) or timezone.now(),
        pay_status=int(payload.get('pay_status') or Invoice.PayStatus.UNPAID),
        finance_user=request.user,
        order_finish_flag=Invoice.FinishFlag.FINISHED,
    )
    report.order.mark_status(LabOrder.Status.INVOICED_CLOSED, request.user, f'会计开票办结：{invoice.invoice_no}')
    return JsonResponse({'ok': True, 'message': '开票办结完成', 'invoice': _invoice_payload(invoice)}, json_dumps_params={'ensure_ascii': False})


def _action_invoice_pay(request, payload):
    role_error = _require_role(request.user, ROLE_ACCOUNTING)
    if role_error:
        return role_error
    invoice_no = (payload.get('invoice_no') or '').strip()
    try:
        invoice = Invoice.objects.select_related('order', 'report', 'finance_user').get(invoice_no=invoice_no)
    except Invoice.DoesNotExist:
        return JsonResponse({'ok': False, 'error': '发票不存在'}, status=404, json_dumps_params={'ensure_ascii': False})
    invoice.pay_status = int(payload.get('pay_status') or Invoice.PayStatus.PAID)
    invoice.finance_user = request.user
    invoice.save()
    _event(invoice.order, request.user, '会计更新回款状态')
    return JsonResponse({'ok': True, 'message': '回款状态已更新', 'invoice': _invoice_payload(invoice)}, json_dumps_params={'ensure_ascii': False})


def lims_dashboard(request):
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': '请先登录'}, status=401, json_dumps_params={'ensure_ascii': False})

    related_orders = _orders_for_user(request.user)
    active_related_orders = related_orders.exclude(
        order_status__in=[LabOrder.Status.INVOICED_CLOSED, LabOrder.Status.CANCELLED]
    )
    recent_orders = [
        _order_payload(order)
        for order in related_orders.order_by('-create_time')[:10]
    ]
    all_orders = [_order_payload(order) for order in related_orders.order_by('-create_time')]
    active_orders = [
        _order_payload(order)
        for order in active_related_orders.order_by('-create_time')
    ]
    report_orders = [
        _order_payload(order)
        for order in related_orders.filter(order_status=LabOrder.Status.REPORT_REVIEW).order_by('-create_time')
    ]
    running_order_ids = Experiment.objects.filter(
        order__in=related_orders,
        test_status=Experiment.Status.RUNNING,
    ).values_list('order_id', flat=True)
    running_orders = [
        _order_payload(order)
        for order in related_orders.filter(id__in=running_order_ids).order_by('-create_time')
    ]
    change_order_ids = ChangeRequest.objects.filter(
        order__in=related_orders,
    ).exclude(change_status=ChangeRequest.Status.APPLIED).values_list('order_id', flat=True)
    change_orders = [
        _order_payload(order)
        for order in related_orders.filter(id__in=change_order_ids).order_by('-create_time')
    ]
    can_view_finance = _can_view_finance(request.user)
    finance_order_ids = []
    if can_view_finance:
        finance_order_ids = list(
            TestReport.objects.filter(
                order__in=related_orders,
                report_status=TestReport.Status.APPROVED,
                invoices__isnull=True,
            ).values_list('order_id', flat=True)
        ) + list(
            Invoice.objects.filter(order__in=related_orders).values_list('order_id', flat=True)
        )
    finance_orders = [
        _order_payload(order)
        for order in related_orders.filter(id__in=finance_order_ids).distinct().order_by('-create_time')
    ]
    pending_reports = _pending_reports_for_user(request.user, related_orders)
    outsource_orders = [
        _order_payload(order)
        for order in related_orders.filter(
            Q(execution_mode=LabOrder.ExecutionMode.OUTSOURCE)
            | Q(schedules__test_type=SchedulePlan.TestType.OUTSOURCE)
        ).distinct().order_by('-create_time')
    ]
    schedules = SchedulePlan.objects.select_related('order', 'lab_manager', 'quality_user').filter(
        order__in=related_orders
    ).order_by('-plan_start_time', '-create_time')
    samples = Sample.objects.select_related('order', 'schedule', 'quality_user').filter(
        order__in=related_orders
    ).order_by('-actual_arrive_time', '-create_time')
    changes = ChangeRequest.objects.select_related('order', 'schedule', 'change_user').filter(
        order__in=related_orders
    ).order_by('-change_time', '-create_time')
    reviews = BusinessReview.objects.select_related('order', 'biz_review_user', 'tech_review_user').filter(
        order__in=related_orders
    ).order_by('-review_time', '-create_time')
    workflow_events = WorkflowEvent.objects.select_related('order', 'actor').filter(
        order__in=related_orders
    ).order_by('-create_time')[:500]
    pending_invoice_reports = TestReport.objects.none()
    invoices = Invoice.objects.none()
    if can_view_finance:
        pending_invoice_reports = TestReport.objects.select_related('order').filter(
            order__in=related_orders,
            report_status=TestReport.Status.APPROVED,
            invoices__isnull=True,
        ).order_by('-create_time')
        invoices = Invoice.objects.select_related('order', 'report', 'finance_user').filter(
            order__in=related_orders,
        ).order_by('-invoice_date', '-create_time')

    data = {
        'company': '苏州环测检测技术有限公司',
        'system': '实验室管理（LIMS）系统',
        'metrics': {
            'orders': related_orders.count(),
            'active_orders': active_related_orders.count(),
            'running_experiments': Experiment.objects.filter(order__in=related_orders, test_status=Experiment.Status.RUNNING).count(),
            'pending_reports': TestReport.objects.filter(order__in=related_orders).exclude(report_status=TestReport.Status.APPROVED).count(),
            'change_requests': ChangeRequest.objects.filter(order__in=related_orders).exclude(
                change_status=ChangeRequest.Status.APPLIED
            ).count(),
        },
        'status_counts': {
            item['order_status']: item['count']
            for item in related_orders.values('order_status').annotate(count=Count('id'))
        },
        'mode_counts': {
            item['execution_mode']: item['count']
            for item in related_orders.values('execution_mode').annotate(count=Count('id'))
        },
        'recent_orders': recent_orders,
        'order_groups': {
            'orders': all_orders,
            'active_orders': active_orders,
            'running_experiments': running_orders,
            'pending_reports': report_orders,
            'change_requests': change_orders,
            'finance_orders': finance_orders,
        },
        'labs': {
            'suzhou': _lab_payload(SchedulePlan.TestType.SUZHOU, '苏州实验室', related_orders, request.user),
            'jiangyin': _lab_payload(SchedulePlan.TestType.JIANGYIN, '江阴实验室', related_orders, request.user),
        },
        'outsource_orders': outsource_orders,
        'schedules': [_schedule_payload(schedule) for schedule in schedules],
        'samples': [_sample_payload(sample) for sample in samples],
        'changes': [_change_payload(change) for change in changes],
        'reviews': [_review_payload(review) for review in reviews],
        'workflow_events': [_workflow_payload(event) for event in workflow_events],
        'pending_reports': [_report_payload(report) for report in pending_reports.order_by('-create_time')],
        'finance': {
            'pending_invoices': [_pending_invoice_payload(report) for report in pending_invoice_reports],
            'issued_invoices': [_invoice_payload(invoice) for invoice in invoices],
        },
        'roles': _roles(request.user),
    }
    return JsonResponse(data, json_dumps_params={'ensure_ascii': False})
