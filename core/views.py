import json
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.models import Group
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseNotFound, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import ChangeRequest, Experiment, LabOrder, ReportAudit, SchedulePlan, TestReport, WorkflowEvent


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
    return list(user.groups.values_list('name', flat=True))


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
        query |= Q(sale_user=user) | Q(order_status__in=[
            LabOrder.Status.REVIEW_REJECTED,
            LabOrder.Status.REPORT_REVIEW,
        ])
    if ROLE_BUSINESS in roles or ROLE_TECH in roles:
        query |= Q(order_status__in=[LabOrder.Status.PENDING_REVIEW, LabOrder.Status.SCHEDULING])
    if ROLE_QUALITY in roles:
        query |= Q(order_status__in=[
            LabOrder.Status.SCHEDULING,
            LabOrder.Status.TESTING,
            LabOrder.Status.REPORT_REVIEW,
        ])
    if ROLE_SUZHOU_LAB in roles:
        query |= Q(execution_mode__in=[LabOrder.ExecutionMode.SUZHOU, LabOrder.ExecutionMode.MIXED])
    if ROLE_JIANGYIN_LAB in roles:
        query |= Q(execution_mode__in=[LabOrder.ExecutionMode.JIANGYIN, LabOrder.ExecutionMode.MIXED])
    if ROLE_OUTSOURCE in roles:
        query |= Q(execution_mode__in=[LabOrder.ExecutionMode.OUTSOURCE, LabOrder.ExecutionMode.MIXED])
    if ROLE_GENERAL_MANAGER in roles:
        query |= Q(order_status=LabOrder.Status.REPORT_REVIEW)
    if ROLE_ACCOUNTING in roles:
        query |= Q(order_status=LabOrder.Status.REPORT_REVIEW)

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


def _lab_payload(test_type, name):
    schedules = SchedulePlan.objects.select_related('order').filter(test_type=test_type).order_by('plan_start_time')
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
    pending_reports = _pending_reports_for_user(request.user, related_orders)
    outsource_orders = [
        _order_payload(order)
        for order in related_orders.filter(
            Q(execution_mode=LabOrder.ExecutionMode.OUTSOURCE)
            | Q(schedules__test_type=SchedulePlan.TestType.OUTSOURCE)
        ).distinct().order_by('-create_time')
    ]

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
        },
        'labs': {
            'suzhou': _lab_payload(SchedulePlan.TestType.SUZHOU, '苏州实验室'),
            'jiangyin': _lab_payload(SchedulePlan.TestType.JIANGYIN, '江阴实验室'),
        },
        'outsource_orders': outsource_orders,
        'pending_reports': [_report_payload(report) for report in pending_reports.order_by('-create_time')],
        'roles': [
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
        ],
    }
    return JsonResponse(data, json_dumps_params={'ensure_ascii': False})
