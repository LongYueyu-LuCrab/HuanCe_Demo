import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.models import Group
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseNotFound, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import ChangeRequest, Customer, Experiment, LabOrder, TestReport, WorkflowEvent


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
        and (user.is_superuser or user.groups.filter(name='董事长').exists())
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
    orders = LabOrder.objects.select_related('customer', 'sales_owner')
    if _is_chairman(user):
        return orders

    roles = set(_roles(user))
    query = Q()
    if '销售' in roles:
        query |= Q(sales_owner=user) | Q(status__in=[
            LabOrder.Status.SALES_REVISION,
            LabOrder.Status.CUSTOMER_CONFIRM,
            LabOrder.Status.SALES_REPORT_REVIEW,
        ])
    if '商务' in roles:
        query |= Q(status__in=[LabOrder.Status.REVIEWING, LabOrder.Status.BUSINESS_ASSIGN])
    if '质量部' in roles:
        query |= Q(status__in=[
            LabOrder.Status.QUALITY_SCHEDULING,
            LabOrder.Status.SAMPLE_REGISTER,
            LabOrder.Status.REPORT_DRAFT,
        ])
    if '苏州实验室' in roles:
        query |= Q(execution_mode__in=[LabOrder.ExecutionMode.SUZHOU, LabOrder.ExecutionMode.MIXED])
    if '江阴实验室' in roles:
        query |= Q(execution_mode__in=[LabOrder.ExecutionMode.JIANGYIN, LabOrder.ExecutionMode.MIXED])
    if '委外供应商' in roles:
        query |= Q(execution_mode__in=[LabOrder.ExecutionMode.OUTSOURCE, LabOrder.ExecutionMode.MIXED])
    if '总经理' in roles:
        query |= Q(status=LabOrder.Status.GM_REPORT_REVIEW)
    if '会计' in roles:
        query |= Q(status=LabOrder.Status.ACCOUNTING_INVOICE)

    if not query:
        return orders.none()
    return orders.filter(query).distinct()


def _order_payload(order):
    return {
        'order_no': order.order_no,
        'customer': order.customer.name,
        'project_name': order.project_name,
        'status': order.get_status_display(),
        'status_key': order.status,
        'execution_mode': order.get_execution_mode_display(),
        'expected_delivery_date': order.expected_delivery_date.isoformat()
        if order.expected_delivery_date
        else '',
        'is_urgent': order.is_urgent,
        'sales_owner': order.sales_owner.first_name or order.sales_owner.username
        if order.sales_owner
        else '',
    }


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


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


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
    if not (_is_chairman(request.user) or '销售' in roles):
        return JsonResponse({'ok': False, 'error': '仅销售或董事长可以下单'}, status=403, json_dumps_params={'ensure_ascii': False})

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': '请求格式错误'}, status=400, json_dumps_params={'ensure_ascii': False})

    customer_name = payload.get('customer_name', '').strip()
    project_name = payload.get('project_name', '').strip()
    test_requirements = payload.get('test_requirements', '').strip()
    contact_name = payload.get('contact_name', '').strip()
    phone = payload.get('phone', '').strip()
    expected_sample_arrival = _parse_date(payload.get('expected_sample_arrival'))
    expected_delivery_date = _parse_date(payload.get('expected_delivery_date'))

    if not customer_name or not project_name or not test_requirements:
        return JsonResponse({'ok': False, 'error': '客户名称、项目名称、试验需求必填'}, status=400, json_dumps_params={'ensure_ascii': False})

    try:
        quoted_amount = Decimal(str(payload.get('quoted_amount') or '0'))
    except InvalidOperation:
        return JsonResponse({'ok': False, 'error': '报价金额格式错误'}, status=400, json_dumps_params={'ensure_ascii': False})

    customer, _ = Customer.objects.get_or_create(name=customer_name)
    customer.contact_name = contact_name
    customer.phone = phone
    customer.save(update_fields=['contact_name', 'phone', 'updated_at'])

    order = LabOrder.objects.create(
        order_no=_next_order_no(),
        customer=customer,
        project_name=project_name,
        test_requirements=test_requirements,
        sales_owner=request.user,
        status=LabOrder.Status.REVIEWING,
        expected_sample_arrival=expected_sample_arrival,
        expected_delivery_date=expected_delivery_date,
        quoted_amount=quoted_amount,
        is_urgent=bool(payload.get('is_urgent')),
        remark='销售前台下单，等待商务技术评审。',
    )
    WorkflowEvent.objects.create(
        order=order,
        actor=request.user,
        event_type=WorkflowEvent.EventType.STATUS,
        to_status=order.status,
        note='销售下单，进入商务技术评审。',
    )
    return JsonResponse({'ok': True, 'order': _order_payload(order)}, json_dumps_params={'ensure_ascii': False})


def lims_dashboard(request):
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': '请先登录'}, status=401, json_dumps_params={'ensure_ascii': False})

    related_orders = _orders_for_user(request.user)
    active_related_orders = related_orders.exclude(
        status__in=[LabOrder.Status.CLOSED, LabOrder.Status.CANCELLED]
    )
    recent_orders = [
        _order_payload(order)
        for order in related_orders.order_by('-created_at')[:10]
    ]

    data = {
        'company': '苏州环测检测技术有限公司',
        'system': '实验室管理（LIMS）系统',
        'metrics': {
            'orders': related_orders.count(),
            'active_orders': active_related_orders.count(),
            'running_experiments': Experiment.objects.filter(order__in=related_orders, status=Experiment.Status.RUNNING).count(),
            'pending_reports': TestReport.objects.filter(order__in=related_orders).exclude(status=TestReport.Status.APPROVED).count(),
            'change_requests': ChangeRequest.objects.filter(order__in=related_orders).exclude(
                status__in=[ChangeRequest.Status.APPLIED, ChangeRequest.Status.REJECTED]
            ).count(),
        },
        'status_counts': {
            item['status']: item['count']
            for item in related_orders.values('status').annotate(count=Count('id'))
        },
        'mode_counts': {
            item['execution_mode']: item['count']
            for item in related_orders.values('execution_mode').annotate(count=Count('id'))
        },
        'recent_orders': recent_orders,
        'roles': [
            '销售',
            '商务',
            '质量部',
            '苏州实验室',
            '江阴实验室',
            '委外供应商',
            '总经理',
            '会计',
            '董事长',
        ],
    }
    return JsonResponse(data, json_dumps_params={'ensure_ascii': False})
