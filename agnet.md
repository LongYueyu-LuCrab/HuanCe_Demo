# HuanCe LIMS Project Notes

## Project Overview

This project is a Django + Vue LIMS prototype for:

苏州环测检测技术有限公司

The system is intended to manage the full laboratory workflow from sales order creation through business/technical review, scheduling, sample registration, testing, report review, invoicing, and closure.

## Tech Stack

- Backend: Django 6
- Admin UI: django-simpleui
- Frontend: Vue 3 + Vite
- Database: SQLite for local development
- Package manager: pnpm for frontend dependencies

## Important Paths

- Django project: `huance/`
- Django app: `core/`
- Vue frontend: `frontend/`
- Local database: `db.sqlite3`
- Virtual environment: `.venv/`
- Built frontend assets: `static/frontend/`

## Local Commands

Run Django checks:

```powershell
.\.venv\Scripts\python.exe manage.py check
```

Run tests:

```powershell
.\.venv\Scripts\python.exe manage.py test core
```

Run migrations:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

Seed demo LIMS data:

```powershell
.\.venv\Scripts\python.exe manage.py seed_lims_demo
```

Build frontend:

```powershell
cd frontend
pnpm build
```

Run development server:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

## Authentication

The Vue frontend uses Django session authentication through these APIs:

- `GET /api/auth/me/`
- `POST /api/auth/login/`
- `POST /api/auth/logout/`

The chairman role is represented by the Django group:

```text
董事长
```

Superusers are also treated as chairman-level users.

## LIMS APIs

- `GET /api/lims/dashboard/`
- `POST /api/orders/create/`
- `POST /api/employees/add/`

Dashboard data is filtered by the current user's role:

- 董事长: all orders
- 销售: own orders and sales-related states
- 商务: review and assignment states
- 质量部: scheduling, sample registration, report drafting
- 苏州实验室 / 江阴实验室 / 委外供应商: related execution paths
- 总经理: final report review
- 会计: invoicing

## Workflow Notes

The intended business flow is:

1. 销售下单
2. 商务技术评审
3. 商务任务书与订单分配
4. 质量部统筹排期
5. 苏州实验室 / 江阴实验室 / 委外供应商执行
6. 生成项目总周期表
7. 销售确认样品与需求
8. 样品编号登记
9. 试验执行与动态变更
10. 质量部出具报告
11. 销售审核报告
12. 总经理终审报告
13. 会计开票办结

Two change-back paths should remain part of future development:

- 样品到货前变更回流到质量部排期
- 试验进行中变更回流到质量部排期

Report review has two rejection loops:

- 销售审核驳回 -> 质量部重新出具报告
- 总经理审核驳回 -> 质量部重新出具报告

## Git Notes

Remote repository:

```text
git@github.com:LongYueyu-LuCrab/HuanCe_Demo.git
```

Do not commit:

- `.venv/`
- `db.sqlite3`
- `frontend/node_modules/`
- `static/frontend/`
- log files

## Current UX Direction

The frontend has two major states:

1. Logged out:
   - Fullscreen background image
   - Company logo at top-left
   - Animated centered login panel

2. Logged in:
   - Left vertical navigation
   - Role-based dashboard
   - Order management with sales order creation
   - Chairman-only employee creation

## Development Guidelines

- Keep core workflow state in Django models.
- Keep user-facing operational screens in Vue.
- Keep Django Admin as the back-office data maintenance surface.
- Add migrations for every model change.
- Update tests when role filtering or workflow state behavior changes.
- Run `manage.py test core` before committing.
