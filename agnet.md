# HuanCe LIMS Project Baseline

This document is the development baseline for the Suzhou HuanCe LIMS project. Future work should follow this file unless the user explicitly changes the architecture or business process.

## 1. Project

- Project name: HuanCe LIMS
- Company: 苏州环测检测技术有限公司
- Product: 实验室管理（LIMS）系统
- Domain: aroundtest.com / www.aroundtest.com
- Production server: 119.45.220.99
- Git remote: git@github.com:LongYueyu-LuCrab/HuanCe_Demo.git
- Current verified sales-order upgrade commit: `4b7d6f0`

## 2. Architecture

The system is a Django backend plus a Vue SPA frontend served by Django.

Backend:

- Django 6
- Python virtual environment: .venv locally, /opt/huance/venv on production
- Django admin with django-simpleui
- PostgreSQL on production
- SQLite allowed only for local development fallback
- Gunicorn + systemd on production
- Nginx reverse proxy on production

Frontend:

- Vue 3
- TypeScript
- Vue Router
- Element Plus
- Vite
- Frontend source: frontend/
- Built SPA output: static/frontend/

Production layout:

```text
/opt/huance/app            source code and built frontend
/opt/huance/venv           Python virtual environment
/opt/huance/.env           production environment variables
/opt/huance/run            Gunicorn socket directory
/opt/huance/media          uploaded files
/etc/systemd/system/huance.service
/etc/nginx/sites-available/huance
/etc/nginx/sites-enabled/huance
```

Never run production with Django runserver.

## 3. Important Local Paths

```text
core/                         Django LIMS app
core/models.py                LIMS business data model
core/views.py                 JSON APIs and workflow action handlers
core/admin.py                 Django admin registration
core/management/commands/     Demo data seed commands
huance/                       Django project settings and URLs
frontend/src/                 Vue source
frontend/src/router.ts        SPA routes
frontend/src/permissions.ts   role-based menu definitions
frontend/src/stores/session.ts session/dashboard state
frontend/src/services/api.ts  frontend API client
static/frontend/              built frontend served by Django
requirements.txt
manage.py
agnet.md
```

Do not commit:

```text
.venv/
db.sqlite3
db.sqlite3*
frontend/node_modules/
staticfiles/
media/
*.log
.env
```

Note: `static/frontend/` contains built assets needed by Django. It may be generated and deployed, but avoid unrelated churn.

## 4. Database Baseline

The LIMS business schema uses 9 core workflow business tables plus supporting reference tables and 1 workflow log table.

Core business tables:

```text
lims_sales_order          sales order root table
lims_biz_review           business and technical review
lims_project_schedule     project schedule and lab/outsource dispatch
lims_order_change         order change request
lims_sample_info          sample registration
lims_test_record          experiment/test execution record
lims_test_report          test report
lims_report_audit         sales and general-manager report audit
lims_finance_invoice      finance invoice and settlement
```

Workflow log:

```text
lims_workflow_event
```

Supporting reference tables:

```text
lims_test_standard        industry/category based test standard library
lims_order_document       protected sales-order contracts and attachments
lims_lab_device           Suzhou/Jiangyin laboratory equipment registry
lims_lab_staff_profile    laboratory staff affiliation and position
lims_sample_photo         protected sample-arrival photos by schedule
```

Structured workflow audit fields in `lims_workflow_event`:

```text
action_code              stable machine-readable action identifier
change_data              JSON snapshot of changed fields and values
schedule_id              optional related laboratory schedule
create_time              operation timestamp
user_id                  operator account
```

Sales-order extension fields:

```text
industry_category        automotive / military / other
autonomous_execution     order includes in-house testing
outsourced_execution     order includes outsourced testing
```

`autonomous_execution` and `outsourced_execution` are independent booleans, so an order may select either one or both. Order files are stored under `MEDIA_ROOT/private_order_documents/` and must be downloaded through the authenticated permission-checked API.

All workflow business records attach to `lims_sales_order` through order relations. Keep future schema changes aligned with this 9 core table design unless the user explicitly approves a redesign. Reference tables such as `lims_test_standard` may be added when they reduce repeated manual entry and keep workflow data consistent.

Production database is PostgreSQL. Environment variables are loaded from `/opt/huance/.env`:

```text
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
POSTGRES_PORT
```

Do not copy production secrets into Git or this document.

## 5. Roles And Accounts

The system uses Django users and groups. Menus, dashboard data, row visibility, and workflow buttons depend on role/group.

Demo accounts:

| Role | Username | Password | Display Name |
|---|---|---|---|
| 董事长 / 超级管理员 | zhihao | 123456 | 董事长 |
| 销售 | sales01 | HuanCe@2026 | 销售一号 |
| 商务部评审人员 | business01 | HuanCe@2026 | 商务评审一号 |
| 技术评审人员 | tech01 | HuanCe@2026 | 技术评审一号 |
| 质量部专员 | quality01 | HuanCe@2026 | 质量专员一号 |
| 苏州实验室项目负责人 | suzhou_lab01 | HuanCe@2026 | 苏州实验室负责人 |
| 江阴实验室项目负责人 | jiangyin_lab01 | HuanCe@2026 | 江阴实验室负责人 |
| 总经理 | general_manager01 | HuanCe@2026 | 总经理一号 |
| 会计 | accountant01 | HuanCe@2026 | 会计一号 |

Additional sales demo users may exist:

```text
sales02 / sales03, password HuanCe@2026
```

Chairman logic:

- Django superusers are treated as chairman-level users.
- Users in the `董事长` group are also treated as chairman-level users.
- Chairman users can view all business data and add employees.

## 6. LIMS Workflow

Main flow:

```text
销售下单
-> 商务/技术联合评审
-> 商务任务书与订单分配
-> 质量部排期分流
-> 苏州实验室 / 江阴实验室 / 外部委外
-> 生成项目周期表
-> 销售确认样品和需求
-> 质量部样品编号登记
-> 实验室或委外开展试验
-> 质量部出具检测报告
-> 销售初审报告
-> 总经理终审报告
-> 会计开票办结
```

Required loopbacks:

- 商务/技术评审驳回 -> 销售修改订单或退单
- 样品到货前变更 -> 填写更改单 -> 回流质量部排期
- 试验过程中变更 -> 填写更改单 -> 回流质量部排期
- 销售报告初审驳回 -> 回流质量部重制报告
- 总经理报告终审驳回 -> 回流质量部重制报告

Order statuses in `LabOrder.Status`:

```text
1 待评审
2 评审驳回
3 排期中
4 试验中
5 报告审核中
6 已开票办结
7 退单
```

Report statuses in `TestReport.Status`:

```text
1 草稿
2 待销售初审
3 待总经理终审
4 审核驳回重制
5 审核通过待开票
```

## 7. Workflow Actions

The current system has a real workflow action layer, not only static display.

Unified backend action endpoint:

```text
POST /api/lims/action/
```

The frontend sends:

```json
{
  "action": "action_name",
  "order_no": "...",
  "report_no": "...",
  "invoice_no": "...",
  "other_form_fields": "..."
}
```

Implemented action names:

```text
review_pass              商务/技术评审通过；必须商务和技术两方都通过后才进入排期
review_reject            商务/技术评审驳回
order_update             销售修改订单并重提
order_cancel             销售退单
sales_confirm            销售确认无变更
create_change            销售/质量/实验室创建更改单
schedule_assign          质量部排期分配
process_change           质量部处理变更并闭环
start_test               苏州/江阴实验室开始试验
submit_test              苏州/江阴实验室提交试验结果
outsource_result         质量部录入委外试验结果回传，生成委外试验记录
issue_report             质量部出具报告
report_sales_pass        销售初审通过
report_sales_reject      销售初审驳回
report_gm_pass           总经理终审通过
report_gm_reject         总经理终审驳回
invoice_create           会计开票办结
invoice_pay              会计更新回款状态
standard_create          实验室/质量部/董事长新增或更新试验标准
```

Each action should:

- verify login
- verify role permission
- update the correct business table
- update order/report/schedule/sample/test/invoice status where needed
- append `WorkflowEvent`
- return JSON with `ok`, `message`, and updated record data where useful

## 8. Frontend Baseline

Logged-out state:

- Fullscreen background image
- HuanCe logo at top-left
- Centered login panel

Logged-in layout:

- Professional admin shell
- Left role-based menu
- Header with system state and role selector/user area
- Element Plus tables, cards, drawers/dialogs, tags, pagination

Main views:

```text
DashboardView.vue       role workbench and clickable metric order groups
OrdersView.vue          order list, sales order creation, workflow order actions
ScheduleView.vue        visible project schedules
LabView.vue             Suzhou/Jiangyin equipment and lab task actions
OutsourceView.vue       outsourced order list
ReportsView.vue         report audit actions
FinanceView.vue         invoice creation and payment-status update
AuditView.vue           workflow logs, change records, review ledger
EmployeesView.vue       chairman-only employee creation
LoginView.vue           login page
```

Reusable components:

```text
OrderTable.vue          paginated/searchable orders plus action buttons
ScheduleTable.vue       paginated/searchable schedules plus lab action buttons
ReportList.vue          paginated/searchable reports plus audit buttons
InvoiceTable.vue        paginated/searchable invoices plus finance buttons
```

Pagination/search baseline:

- Long lists must be finite height.
- Provide search input when listing orders, reports, schedules, samples, invoices, logs.
- Provide 10/15/20 page-size selector where appropriate.
- Avoid pages that grow endlessly downward.

## 9. Data Permissions

Data access is currently role-filtered in `_orders_for_user()` and related dashboard payloads:

- 董事长: all business data
- 销售: own orders
- 商务/技术: review-related orders
- 质量部: scheduling/testing/report-review orders
- 苏州实验室: schedules assigned to current Suzhou lab manager
- 江阴实验室: schedules assigned to current Jiangyin lab manager
- 总经理: all business data, with report final-audit action
- 会计: approved reports, invoices, and finance-related orders

Do not add a new menu or workflow button without checking role visibility and row-level access.

Laboratory role rules:

- `LabStaffProfile` is the authoritative Suzhou/Jiangyin affiliation for laboratory managers and operators.
- The `实验操作员` group is a workflow role. Operators may schedule tasks, confirm sample arrival, start tests, submit results, create in-test changes, and issue reports for their own laboratory.
- Laboratory operators cannot create, delete, or change laboratory devices. Device management remains a laboratory-manager/chairman responsibility.
- Laboratory managers and operators may query the complete order history of their own laboratory and export the filtered result to Excel.
- Suzhou users must never query or export Jiangyin laboratory rows, and vice versa.
- Each laboratory workflow mutation must append a `WorkflowEvent` containing action code, operator, timestamp, related schedule, and structured changed values.

Sample-arrival workflow rules:

- Sales must provide `expect_sample_arrive` when creating a new order.
- There is no independent `register_sample` workflow action in the current workflow.
- Laboratory managers/operators set `SchedulePlan.sample_arrived` while scheduling a task.
- Marking a task as arrived requires at least one JPG/PNG photo in `lims_sample_photo` unless that schedule already has a photo.
- `start_test` and outsourced-result submission must reject schedules whose sample has not arrived.
- The legacy `lims_sample_info` table is retained only for historical traceability and compatibility with existing experiment foreign keys; it is not a separate user-operated workflow node.
- Sample photos are private media and must only be served through the authenticated permission-checked API.

## 10. Demo Data

Primary demo seed command:

```powershell
.\.venv\Scripts\python.exe manage.py seed_lims_workflow_demo
```

This command creates/updates the demo users and recreates 100 `DEMO-2026-*` workflow orders.

Current coverage target:

- all 7 order statuses
- Suzhou schedules
- Jiangyin schedules
- outsourced schedules
- sample registration records
- waiting/running/finished test records
- pre-sample change requests
- during-test change requests
- sales report approval/rejection
- general-manager report approval/rejection
- pending invoice records
- issued invoice records
- workflow logs

Use this command before demos when a clean full-flow dataset is needed. It deletes and rebuilds only `DEMO-2026-*` orders.

## 11. API Baseline

Authentication:

```text
GET  /api/auth/me/
POST /api/auth/login/
POST /api/auth/logout/
```

LIMS:

```text
GET  /api/lims/dashboard/
POST /api/lims/action/
POST /api/orders/create/
GET  /api/orders/documents/<id>/download/
POST /api/employees/add/
GET  /api/labs/orders/
GET  /api/labs/orders/export/
```

Laboratory order query/export filters include keyword, order status, schedule status, device, planned date range, and selected schedule IDs. Export files are generated with `openpyxl`; the API must enforce laboratory row permissions independently of frontend filters.

`/api/lims/dashboard/` returns role-filtered:

- company/system labels
- metrics
- status counts
- mode counts
- recent orders
- order groups
- lab devices and lab schedules
- outsource orders
- schedules
- samples
- changes
- reviews
- workflow events
- pending reports
- finance pending/issued invoices
- current roles

## 12. Local Development

Use PowerShell from project root:

```powershell
cd G:\Codex\djiango_HuanCe
```

Run Django checks:

```powershell
.\.venv\Scripts\python.exe manage.py check
```

Run tests:

```powershell
.\.venv\Scripts\python.exe manage.py test
```

Run migrations:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

Seed full workflow demo data:

```powershell
.\.venv\Scripts\python.exe manage.py seed_lims_workflow_demo
```

Run local server:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Build frontend with a Node version compatible with current Vite. The system Node may be too old. Codex bundled Node works:

```powershell
cd frontend
& "C:\Users\LuCrab\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" ".\node_modules\typescript\bin\tsc"
& "C:\Users\LuCrab\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" ".\node_modules\vite\bin\vite.js" build
```

The Vite build may show dependency warnings about pure annotations or chunk size. Those warnings are acceptable if the command exits successfully.

## 13. Production Operations

SSH:

```text
host: 119.45.220.99
user: ubuntu
key: D:\IE_DownLoad\huance_server_key.pem
```

Windows OpenSSH may reject the PEM if its file permissions are too open. Paramiko can still use the key.

Production commands:

```bash
cd /opt/huance/app
set -a
. /opt/huance/.env
set +a
/opt/huance/venv/bin/python manage.py check
/opt/huance/venv/bin/python manage.py migrate --noinput
/opt/huance/venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart huance
systemctl is-active huance
```

Nginx:

```bash
sudo systemctl restart nginx
systemctl is-active nginx
```

Production health checks:

```powershell
Invoke-WebRequest -UseBasicParsing -Uri http://www.aroundtest.com/ -TimeoutSec 20
```

Expected:

```text
HTTP 200
```

## 14. Deployment Pattern

The production directory is not currently a Git working tree. Deployment has been done by uploading changed files and built `static/frontend/` assets, then running `collectstatic` and restarting `huance`.

When deploying:

1. Run backend checks and tests locally.
2. Run frontend typecheck/build locally.
3. Commit and push to GitHub.
4. Upload changed backend/frontend source files.
5. Upload generated `static/frontend/` files.
6. On production, run `manage.py check`.
7. Run migrations if there are migrations.
8. Run `collectstatic --noinput`.
9. Restart `huance`.
10. Verify HTTP 200.

## 15. Verification Snapshot

Latest verified sales-order upgrade commit:

```text
4b7d6f0 Upgrade sales order intake and document uploads
```

Recent verification completed:

- Django `manage.py check`: passed
- Django tests: passed
- TypeScript check: passed
- Vite production build: passed
- Local full workflow smoke test: passed
- Local branch workflow smoke test: passed
- GitHub push: completed
- Production upload/deploy: completed
- Production `manage.py check`: passed
- Production `collectstatic`: completed
- Production `huance` service: active
- Production HTTP: 200

Full workflow smoke test path:

```text
sales01 creates order
business01 review_pass
quality01 schedule_assign
laboratory manager/operator confirms sample arrival during schedule_assign
suzhou_lab01 start_test
suzhou_lab01 submit_test
quality01 issue_report
sales01 report_sales_pass
general_manager01 report_gm_pass
accountant01 invoice_create
final order status = 已开票办结
```

Branch smoke test path:

```text
tech01 review_reject
sales01 order_update
business01 review_pass
sales01 create_change
order returns to scheduling / change request created
```

## 16. Known Gaps And Next Work

The workflow action layer is functional but still a pragmatic first version. Improve these later:

- Add dedicated forms per role with stronger validation.
- Add separate business and technical review states if the user wants true parallel approval.
- Add explicit task assignment records if the user wants a formal "商务任务书" document object.
- Add report PDF upload and file preview.
- Add invoice creation form validation and export.
- Add better audit timeline visualization.
- Add automated browser tests for all role flows.
- Add HTTPS for aroundtest.com.
- Add scheduled PostgreSQL backups.

## 17. Development Rules

- Treat this `agnet.md` as the baseline for future development.
- Preserve the 9 core workflow tables, workflow log, and approved supporting reference tables unless the user approves a migration plan.
- Do not break role-based menu and row-level permissions.
- Every workflow action must write `WorkflowEvent`.
- Every new workflow button must have backend permission checks.
- Prefer scoped changes over broad rewrites.
- Add migrations for database changes.
- Run Django checks/tests before committing.
- Run frontend typecheck/build before deployment.
- Never commit secrets, `.env`, virtual environments, database files, logs, or uploaded media.
- Keep production commands loading `/opt/huance/.env`.
- After deployment, verify service status and HTTP 200.

## 18. Complete Order Context Across Workflow

Sales-order fields are shared workflow context, not sales-only presentation data.

- Use `GET /api/orders/<order_no>/` to load the complete order context on demand.
- The endpoint must enforce the same row-level visibility rules as the current user's order list.
- Use `OrderSnapshot.vue` as the shared frontend presentation component.
- Business review, technical review, scheduling, sample registration, laboratory execution,
  report review, outsourcing, and finance must expose the complete visible order context.
- The context includes customer/contact details, project and test demand, quote, industry,
  test method, test standard, autonomous/outsourced attributes, dates, remarks, contracts,
  and attachments.
- Contracts and attachments remain protected resources and must be downloaded through the
  authenticated document endpoint; never expose their private storage path directly.
- Load full details lazily when a user opens a workflow action or detail drawer so dashboard
  payloads do not grow with document metadata.
- When adding future sales-order fields, update `_order_payload`, `OrderItem`, `OrderSnapshot`,
  relevant tests, and every downstream workflow view in the same change.

## 19. Workflow V2 Authoritative Baseline

This section supersedes older quality-department workflow descriptions for all newly created
orders. Older sections remain only as V1 history and compatibility documentation.

### 19.1 Versioning And Cutover

- `LabOrder.workflow_version=1`: legacy quality-department coordination workflow.
- `LabOrder.workflow_version=2`: technical-review-to-laboratory workflow and the default for new orders.
- Migration `0005` marks every pre-existing order as V1 and leaves its data and audit chain intact.
- The legacy `质量部` role cannot operate V2 orders and cannot be assigned to new employees.
- Keep V1 permissions only until all historical in-progress orders are complete.

### 19.2 V2 Workflow

```text
sales order
-> business and technical dual review
-> technical reviewer selects one or more routes and route managers
-> technical reviewer selects one lead laboratory manager
-> assigned laboratory managers plan their own routes
-> sales confirms requirements after schedules are available
-> each assigned laboratory manager schedules the route, confirms arrival, and uploads sample photos
-> internal laboratory execution and/or internally-owned outsource execution
-> every route submits a finished experiment record
-> lead laboratory manager consolidates and issues the final report
-> sales report review
-> general-manager final review
-> accounting invoice and closure
```

### 19.3 Responsibility Rules

- Technical reviewers own route selection and initial assignment, not detailed scheduling.
- Routes are `苏州实验室`, `江阴实验室`, and `外部委外`; multiple routes are allowed.
- Every route is a `SchedulePlan` and has its own `lab_manager`.
- Outsource routes must also have an internal Suzhou or Jiangyin manager.
- `LabOrder.lead_lab_manager` must be one of the assigned route managers.
- Laboratory managers can only update schedules, sample-arrival status, changes, and results assigned to themselves.
- A sales change creates a pending change for every route; a laboratory change affects only its own route.
- Starting an experiment is blocked until that route is marked as sample-arrived.
- Final report creation is blocked until every schedule and experiment is finished.
- Only the lead laboratory manager can create or remake the consolidated final report.
- Sales and general-manager rejection returns the report to the same lead laboratory manager.

### 19.4 Field Semantics

- `SchedulePlan.assigned_by`: technical reviewer who created the route assignment.
- `SchedulePlan.quality_user`: retained database field; semantically the current schedule operator.
- `Sample.quality_user`: retained legacy compatibility field; new sample-arrival confirmation is stored on `SchedulePlan`.
- `TestReport.create_quality_user`: retained database field; semantically the report creator.
- `LabOrder.sales_confirmed_at`: cleared whenever a change returns the order to scheduling.

### 19.5 Required Tests

Every workflow change must preserve both test paths:

- V1 historical order remains operable by the legacy quality role.
- V2 order completes through business review, technical route assignment, per-lab scheduling,
  sales confirmation, per-route sample-arrival/test/outsource handling, lead report creation, report audit,
  and finance closure.
- Quality role receives HTTP 403 for V2 operational actions.
- Non-assigned laboratory managers cannot operate another manager's route.
- Non-lead laboratory managers cannot issue the final report.

## 20. Laboratory Equipment And Scheduling Baseline

Migration `0006` introduces formal equipment scheduling for internal laboratory routes.

- `LabDevice` is stored in `lims_lab_device` and belongs to either Suzhou or Jiangyin.
- Configured equipment states are `设备正常`, `维修中`, and `设备停用`.
- `实验中` is a derived display state when a linked schedule is running; never persist it manually.
- `SchedulePlan.device` links an internal route to its selected test bench. Historical schedules may remain null.
- Every new V2 internal schedule and every V2 schedule change must include a device.
- The selected device must belong to the schedule's laboratory and be in normal state.
- Two non-finished schedules cannot overlap on the same device. The authoritative overlap rule is
  `existing.start < requested.end AND existing.end > requested.start`.
- Availability shown by the frontend is advisory; `_action_schedule_assign` and
  `_action_process_change` must always validate again inside a database transaction.
- A device with any schedule history cannot be deleted. Managers must set it to `设备停用` instead.
- A running device cannot be changed directly to maintenance or disabled.
- Suzhou/Jiangyin managers can manage only their own laboratory's devices; the chairman can manage both.
- Starting a test uses the route task and the sales/technical order standard automatically. Laboratory
  users do not choose industry or test standard in the start-test dialog.
- The equipment management page and laboratory overview must show real current/future schedule data,
  never synthesized placeholder devices or mock bookings.
