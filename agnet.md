# HuanCe LIMS Project Baseline

This document is the working baseline for future development of the HuanCe LIMS project.

Project name: HuanCe LIMS

Company: 苏州环测检测技术有限公司

Domain reserved: aroundtest.com

Current production server: 119.45.220.99

Git remote:

```text
git@github.com:LongYueyu-LuCrab/HuanCe_Demo.git
```

Current verified commit:

```text
36d08cd Add PostgreSQL deployment configuration
```

## 1. Architecture

The project is a Django + Vue laboratory information management system.

Local development stack:

- Backend: Django 6.0.6
- Admin UI: django-simpleui
- Frontend: Vue 3 + Vite
- Local database fallback: SQLite, only for development
- Frontend package manager: pnpm
- Local virtual environment: `.venv/`

Production stack on Tencent Cloud:

- OS: Ubuntu Server 22.04 LTS
- Python: 3.12
- Database: PostgreSQL
- App server: Gunicorn
- Reverse proxy: Nginx
- Process manager: systemd
- Production app path: `/opt/huance/app`
- Production virtual environment: `/opt/huance/venv`
- Production env file: `/opt/huance/.env`
- Production media path: `/opt/huance/media`

Production URL currently available:

```text
http://119.45.220.99/
```

After DNS is configured:

```text
http://aroundtest.com/
http://www.aroundtest.com/
```

HTTPS is not configured yet. Add HTTPS after DNS and ICP/domain steps are ready.

## 2. Important Local Paths

```text
core/                         Django LIMS app
huance/                       Django project settings and URLs
frontend/                     Vue frontend source
static/frontend/              Built Vue frontend served by Django
core/migrations/0001_initial.py
requirements.txt
manage.py
agnet.md
```

Do not commit local runtime data:

```text
.venv/
db.sqlite3
db.sqlite3*
frontend/node_modules/
static/frontend/
staticfiles/
media/
*.log
```

## 3. Database Baseline

The LIMS business data model is now standardized as 9 core business tables plus 1 workflow log table.

Core business tables:

```text
lims_sales_order
lims_biz_review
lims_project_schedule
lims_order_change
lims_sample_info
lims_test_record
lims_test_report
lims_report_audit
lims_finance_invoice
```

Workflow log table:

```text
lims_workflow_event
```

Production database is PostgreSQL. Local development can still fall back to SQLite when `POSTGRES_DB` is not set.

Production database settings are read from environment variables:

```text
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
POSTGRES_PORT
```

The PostgreSQL password is stored only on the server in `/opt/huance/.env`. Do not copy secrets into Git or this document.

## 4. Roles

The system uses Django users and groups for staff roles.

Current workflow roles:

```text
销售
商务
技术
质量部
苏州实验室
江阴实验室
委外供应商
总经理
会计
董事长
```

Chairman logic:

- Django superusers are treated as chairman-level users.
- Users in the `董事长` group are also treated as chairman-level users.
- Chairman users can view all workflow orders and add employees.

## 5. Workflow Baseline

The core business process is:

1. 销售下单
2. 商务 + 技术联合评审
3. 商务任务书与订单分配
4. 质量部统筹排期
5. 苏州实验室 / 江阴实验室 / 委外供应商并行执行
6. 生成项目周期排期
7. 销售确认样品与需求
8. 质量部登记样品编号
9. 试验执行
10. 试验中动态变更回流排期
11. 质量部出具报告
12. 销售初审报告
13. 总经理终审报告
14. 会计开票办结

Required loopbacks:

- Business/technical review rejected -> return to sales for order edit or cancellation.
- Pre-sample change -> create change request -> return to quality scheduling.
- During-test change -> create change request -> return to quality scheduling.
- Sales report rejection -> return to quality for report remake.
- General manager report rejection -> return to quality for report remake.

## 6. Current Frontend Baseline

Logged-out state:

- Fullscreen background image.
- Company logo at top-left.
- Centered animated login panel.

Logged-in layout:

- Left vertical navigation.
- Role text under the HuanCe LIMS logo.
- Django admin shortcut in the header.

Implemented frontend modules:

- 业务总览
  - Metric cards are clickable.
  - Cards open filtered order lists.
  - Clicking an order shows detailed status, customer, project, quote, delivery, demand, and owner.
- 订单管理
  - Sales/chairman can create orders.
- 苏州实验室
  - Shows equipment cards, running orders, expected finish time, future schedule, and order filtering.
- 江阴实验室
  - Same structure as Suzhou lab.
- 委外试验
  - Shows outsourced orders.
- 报告审核
  - Shows reports that the current role needs to audit.
- 添加员工
  - Chairman only.

Reserved modules:

- 排期管理
- 样品台账
- 财务开票
- 流程日志

These should be implemented using the current 9+1 database baseline.

## 7. Backend APIs

Authentication:

```text
GET  /api/auth/me/
POST /api/auth/login/
POST /api/auth/logout/
```

LIMS:

```text
GET  /api/lims/dashboard/
POST /api/orders/create/
POST /api/employees/add/
```

`/api/lims/dashboard/` currently returns:

- role-filtered metrics
- order groups for clickable dashboard cards
- lab equipment and scheduling information
- outsourced orders
- pending reports for the current role
- recent orders
- supported roles

## 8. Local Development Commands

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
pnpm run build
```

Run local development server:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

## 9. Production Commands

SSH user:

```text
ubuntu
```

Production app directory:

```bash
cd /opt/huance/app
```

Check service state:

```bash
systemctl status huance
systemctl status nginx
systemctl status postgresql
```

Restart services:

```bash
sudo systemctl restart huance
sudo systemctl restart nginx
```

Run Django commands with production environment loaded:

```bash
cd /opt/huance/app
set -a
. /opt/huance/.env
set +a
/opt/huance/venv/bin/python manage.py check
/opt/huance/venv/bin/python manage.py migrate
/opt/huance/venv/bin/python manage.py collectstatic --noinput
```

Check production database table count:

```bash
cd /opt/huance/app
set -a
. /opt/huance/.env
set +a
/opt/huance/venv/bin/python manage.py shell -c "from django.db import connection; print(connection.vendor); print(len([t for t in connection.introspection.table_names() if t.startswith('lims_')]))"
```

Expected result:

```text
postgresql
10
```

## 10. Deployment Notes

Current deployment was performed by uploading a clean zip package to the Tencent Cloud server.

Production service layout:

```text
/opt/huance/app            source code and static build
/opt/huance/venv           Python virtual environment
/opt/huance/.env           production environment variables
/opt/huance/run            Gunicorn socket directory
/opt/huance/media          uploaded files
/etc/systemd/system/huance.service
/etc/nginx/sites-available/huance
/etc/nginx/sites-enabled/huance
```

Nginx proxies requests to Gunicorn through:

```text
/opt/huance/run/gunicorn.sock
```

Do not run production using:

```bash
python manage.py runserver
```

## 11. Verification Status

Latest local verification:

- Local Git working tree clean.
- Local HEAD equals GitHub `origin/main`.
- Latest commit: `36d08cd Add PostgreSQL deployment configuration`.

Latest production verification:

- `huance` service active.
- `nginx` service active.
- Django check passes when `/opt/huance/.env` is loaded.
- Production database vendor is PostgreSQL.
- 10 `lims_` tables are present.
- `http://119.45.220.99/` returns HTTP 200.

## 12. Next Operational Tasks

Later tasks not yet completed:

1. Add DNS A records for `aroundtest.com` and `www.aroundtest.com` to `119.45.220.99`.
2. Configure HTTPS after DNS is active.
3. Change the initial server password and move to SSH key login.
4. Add scheduled PostgreSQL backups.
5. Decide whether report PDF/media files remain on server disk or move to Tencent COS later.

## 13. Development Rules Going Forward

- Treat this `agnet.md` as the project baseline.
- Keep model changes aligned with the 9+1 LIMS table design.
- Add migrations for every database change.
- Update tests when workflow roles, status transitions, dashboard filters, or APIs change.
- Run `manage.py check` and `manage.py test core` before committing.
- Build Vue before deployment.
- Never commit `.env`, database files, uploaded media, virtual environments, or secrets.
- For production commands, always load `/opt/huance/.env` before running Django management commands manually.
