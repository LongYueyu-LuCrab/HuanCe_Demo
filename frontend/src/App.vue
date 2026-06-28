<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import companyLogo from './assets/suzhou-huance-logo.png'
import backgroundImage from './assets/lims-background.png'

type User = {
  authenticated: boolean
  username?: string
  display_name?: string
  email?: string
  roles?: string[]
  is_chairman?: boolean
}

type OrderItem = {
  order_no: string
  customer: string
  contact?: string
  phone?: string
  project_name: string
  test_demand?: string
  status: string
  status_key: number
  execution_mode: string
  expected_delivery_date: string
  total_quote?: string
  is_urgent: boolean
  sales_owner?: string
  created_at?: string
}

type ScheduleItem = {
  order_no: string
  customer: string
  project_name: string
  status: string
  test_type: string
  start_time: string
  end_time: string
  schedule_status: string
  remark: string
}

type LabDevice = {
  name: string
  status: string
  order_no: string
  project_name: string
  end_time: string
  future_orders: ScheduleItem[]
}

type LabView = {
  name: string
  devices: LabDevice[]
  orders: ScheduleItem[]
}

type ReportItem = {
  report_no: string
  order_no: string
  customer: string
  project_name: string
  status: string
  status_key: number
  conclusion: string
  remake_count: number
  quality_user: string
}

type InvoiceItem = {
  invoice_no?: string
  order_no: string
  report_no: string
  customer: string
  project_name: string
  invoice_amount: string
  invoice_type: string
  invoice_date: string
  pay_status: string
  finish_status: string
  finance_user: string
}

type ListKey = 'orders' | 'suzhou' | 'jiangyin' | 'outsource' | 'reports' | 'pendingInvoices' | 'issuedInvoices'
type LabKey = 'suzhou' | 'jiangyin'

type Dashboard = {
  company: string
  system: string
  metrics: Record<string, number>
  roles: string[]
  recent_orders: OrderItem[]
  order_groups: Record<string, OrderItem[]>
  labs: {
    suzhou: LabView
    jiangyin: LabView
  }
  outsource_orders: OrderItem[]
  pending_reports: ReportItem[]
  finance: {
    pending_invoices: InvoiceItem[]
    issued_invoices: InvoiceItem[]
  }
}

const user = ref<User>({ authenticated: false })
const dashboard = ref<Dashboard | null>(null)
const activeMenu = ref('dashboard')
const activeMetric = ref('orders')
const selectedOrder = ref<OrderItem | null>(null)
const dashboardSearch = ref('')
const dashboardPageSize = ref(10)
const dashboardPage = ref(1)
const loading = ref(true)
const loginError = ref('')
const employeeMessage = ref('')
const orderMessage = ref('')
const showOrderForm = ref(false)

const loginForm = reactive({ username: '', password: '' })
const employeeForm = reactive({
  username: '',
  password: '',
  display_name: '',
  email: '',
  role: '销售',
})
const orderForm = reactive({
  customer_name: '',
  contact_name: '',
  phone: '',
  project_name: '',
  test_requirements: '',
  expected_sample_arrival: '',
  expected_delivery_date: '',
  quoted_amount: '',
  is_urgent: false,
})
const listSearch = reactive<Record<ListKey, string>>({
  orders: '',
  suzhou: '',
  jiangyin: '',
  outsource: '',
  reports: '',
  pendingInvoices: '',
  issuedInvoices: '',
})
const listPageSize = reactive<Record<ListKey, number>>({
  orders: 10,
  suzhou: 10,
  jiangyin: 10,
  outsource: 10,
  reports: 10,
  pendingInvoices: 10,
  issuedInvoices: 10,
})
const listPage = reactive<Record<ListKey, number>>({
  orders: 1,
  suzhou: 1,
  jiangyin: 1,
  outsource: 1,
  reports: 1,
  pendingInvoices: 1,
  issuedInvoices: 1,
})


const backgroundStyle = computed(() => ({
  backgroundImage: `linear-gradient(90deg, rgba(5, 14, 28, 0.54), rgba(5, 14, 28, 0.2)), url(${backgroundImage})`,
}))

const canCreateOrder = computed(() => {
  const roles = user.value.roles || []
  return Boolean(user.value.is_chairman || roles.includes('销售'))
})

const userRoles = computed(() => new Set(user.value.roles || []))
const hasRole = (role: string) => userRoles.value.has(role)
const canSeeAllBusiness = computed(() => Boolean(user.value.is_chairman || hasRole('总经理')))

type MenuItem = { key: string; label: string }
type MenuGroup = { title: string; items: MenuItem[] }

function group(title: string, items: MenuItem[]): MenuGroup | null {
  return items.length ? { title, items } : null
}

const menuGroups = computed(() => {
  if (user.value.is_chairman) {
    return [
      group('工作台', [
        { key: 'dashboard', label: '业务总览' },
        { key: 'orders', label: '订单管理' },
        { key: 'schedule', label: '排期管理' },
        { key: 'samples', label: '样品台账' },
      ]),
      group('实验室', [
        { key: 'suzhou', label: '苏州实验室' },
        { key: 'jiangyin', label: '江阴实验室' },
        { key: 'outsource', label: '委外试验' },
        { key: 'reports', label: '报告审核' },
      ]),
      group('财务与系统', [
        { key: 'invoice', label: '财务开票' },
        { key: 'audit', label: '流程日志' },
        { key: 'employees', label: '添加员工' },
      ]),
    ].filter(Boolean) as MenuGroup[]
  }

  if (hasRole('销售')) {
    return [
      group('销售工作台', [
        { key: 'dashboard', label: '我的看板' },
        { key: 'orders', label: '我的订单' },
        { key: 'reports', label: '报告初审' },
      ]),
      group('追溯', [{ key: 'audit', label: '订单档案' }]),
    ].filter(Boolean) as MenuGroup[]
  }

  if (hasRole('商务')) {
    return [
      group('商务工作台', [
        { key: 'dashboard', label: '评审看板' },
        { key: 'orders', label: '订单评审中心' },
        { key: 'audit', label: '报价与评审台账' },
      ]),
    ].filter(Boolean) as MenuGroup[]
  }

  if (hasRole('技术')) {
    return [
      group('技术工作台', [
        { key: 'dashboard', label: '技术看板' },
        { key: 'orders', label: '技术评审工作台' },
        { key: 'audit', label: '检测标准与记录' },
      ]),
    ].filter(Boolean) as MenuGroup[]
  }

  if (hasRole('质量部')) {
    return [
      group('质量调度', [
        { key: 'dashboard', label: '质量看板' },
        { key: 'orders', label: '全订单档案' },
        { key: 'schedule', label: '排期调度' },
        { key: 'samples', label: '样品管理' },
      ]),
      group('执行与报告', [
        { key: 'suzhou', label: '苏州实验室' },
        { key: 'jiangyin', label: '江阴实验室' },
        { key: 'outsource', label: '委外试验' },
        { key: 'reports', label: '报告制作' },
        { key: 'audit', label: '变更与流程日志' },
      ]),
    ].filter(Boolean) as MenuGroup[]
  }

  if (hasRole('苏州实验室')) {
    return [
      group('苏州实验室', [
        { key: 'dashboard', label: '我的试验看板' },
        { key: 'suzhou', label: '我的试验任务' },
        { key: 'audit', label: '相关变更记录' },
      ]),
    ].filter(Boolean) as MenuGroup[]
  }

  if (hasRole('江阴实验室')) {
    return [
      group('江阴实验室', [
        { key: 'dashboard', label: '我的试验看板' },
        { key: 'jiangyin', label: '我的试验任务' },
        { key: 'audit', label: '相关变更记录' },
      ]),
    ].filter(Boolean) as MenuGroup[]
  }

  if (hasRole('总经理')) {
    return [
      group('经营总览', [
        { key: 'dashboard', label: '全局看板' },
        { key: 'orders', label: '全局订单查询' },
        { key: 'suzhou', label: '苏州负荷' },
        { key: 'jiangyin', label: '江阴负荷' },
        { key: 'outsource', label: '委外占比' },
      ]),
      group('审批与财务', [
        { key: 'reports', label: '报告终审' },
        { key: 'invoice', label: '财务台账' },
        { key: 'audit', label: '全链路档案' },
      ]),
    ].filter(Boolean) as MenuGroup[]
  }

  if (hasRole('会计')) {
    return [
      group('财务工作台', [
        { key: 'dashboard', label: '财务看板' },
        { key: 'invoice', label: '财务开票' },
        { key: 'orders', label: '订单核对' },
        { key: 'reports', label: '报告核对' },
      ]),
    ].filter(Boolean) as MenuGroup[]
  }

  return [group('工作台', [{ key: 'dashboard', label: '业务总览' }])].filter(Boolean) as MenuGroup[]
})

const visibleMenuKeys = computed(() => new Set(menuGroups.value.flatMap((menuGroup) => menuGroup.items.map((item) => item.key))))

function ensureVisibleWorkspace() {
  if (!visibleMenuKeys.value.has(activeMenu.value)) {
    activeMenu.value = menuGroups.value[0]?.items[0]?.key || 'dashboard'
  }
  if (!metricCards.value.some((item) => item.key === activeMetric.value)) {
    activeMetric.value = metricCards.value[0]?.key || 'orders'
  }
}

const metricCards = computed(() => {
  const metrics = dashboard.value?.metrics
  if (hasRole('销售') && !canSeeAllBusiness.value) {
    return [
      { key: 'orders', label: '我的客户订单', value: metrics?.orders ?? 0 },
      { key: 'active_orders', label: '我的进行中订单', value: metrics?.active_orders ?? 0 },
      { key: 'pending_reports', label: '待我初审报告', value: metrics?.pending_reports ?? 0 },
      { key: 'change_requests', label: '我的变更待确认', value: metrics?.change_requests ?? 0 },
    ]
  }
  if ((hasRole('商务') || hasRole('技术')) && !canSeeAllBusiness.value) {
    return [
      { key: 'orders', label: '待评审订单', value: metrics?.orders ?? 0 },
      { key: 'active_orders', label: '评审中订单', value: metrics?.active_orders ?? 0 },
      { key: 'change_requests', label: '评审驳回/变更', value: metrics?.change_requests ?? 0 },
    ]
  }
  if (hasRole('质量部') && !canSeeAllBusiness.value) {
    return [
      { key: 'active_orders', label: '待排期/试验订单', value: metrics?.active_orders ?? 0 },
      { key: 'running_experiments', label: '试验中订单', value: metrics?.running_experiments ?? 0 },
      { key: 'pending_reports', label: '待制作/重制报告', value: metrics?.pending_reports ?? 0 },
      { key: 'change_requests', label: '变更待调整排期', value: metrics?.change_requests ?? 0 },
    ]
  }
  if ((hasRole('苏州实验室') || hasRole('江阴实验室')) && !canSeeAllBusiness.value) {
    return [
      { key: 'orders', label: '分配给我的试验单', value: metrics?.orders ?? 0 },
      { key: 'running_experiments', label: '我的试验执行中', value: metrics?.running_experiments ?? 0 },
      { key: 'change_requests', label: '试验变更提醒', value: metrics?.change_requests ?? 0 },
    ]
  }
  if (hasRole('会计') && !canSeeAllBusiness.value) {
    const pendingInvoices = dashboard.value?.finance?.pending_invoices?.length ?? 0
    const issuedInvoices = dashboard.value?.finance?.issued_invoices?.length ?? 0
    return [
      { key: 'finance_orders', label: '待/已开票订单', value: pendingInvoices + issuedInvoices },
      { key: 'finance_orders', label: '待开票订单', value: pendingInvoices },
      { key: 'finance_orders', label: '已开票记录', value: issuedInvoices },
    ]
  }
  return [
    { key: 'orders', label: '全局订单', value: metrics?.orders ?? 0 },
    { key: 'active_orders', label: '进行中订单', value: metrics?.active_orders ?? 0 },
    { key: 'running_experiments', label: '试验执行中', value: metrics?.running_experiments ?? 0 },
    { key: 'pending_reports', label: '待审核报告', value: metrics?.pending_reports ?? 0 },
    { key: 'change_requests', label: '变更待闭环', value: metrics?.change_requests ?? 0 },
  ]
})

const activeMetricOrders = computed(() => dashboard.value?.order_groups?.[activeMetric.value] ?? [])
const filteredMetricOrders = computed(() => {
  const keyword = dashboardSearch.value.trim().toLowerCase()
  const source = activeMetricOrders.value
  if (!keyword) return source
  return source.filter((order) =>
    [
      order.order_no,
      order.customer,
      order.contact,
      order.phone,
      order.project_name,
      order.test_demand,
      order.status,
      order.execution_mode,
      order.expected_delivery_date,
      order.sales_owner,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(keyword),
  )
})
const totalDashboardPages = computed(() =>
  Math.max(1, Math.ceil(filteredMetricOrders.value.length / dashboardPageSize.value)),
)
const pagedMetricOrders = computed(() => {
  const currentPage = Math.min(dashboardPage.value, totalDashboardPages.value)
  const start = (currentPage - 1) * dashboardPageSize.value
  return filteredMetricOrders.value.slice(start, start + dashboardPageSize.value)
})
const dashboardRangeText = computed(() => {
  const total = filteredMetricOrders.value.length
  if (total === 0) return '0 / 0'
  const currentPage = Math.min(dashboardPage.value, totalDashboardPages.value)
  const start = (currentPage - 1) * dashboardPageSize.value + 1
  const end = Math.min(start + dashboardPageSize.value - 1, total)
  return `${start}-${end} / ${total}`
})
const roleText = computed(() => user.value.roles?.join(' / ') || '普通用户')
const orders = computed(() => dashboard.value?.recent_orders ?? [])
const currentLabKey = computed<LabKey>(() => (activeMenu.value === 'jiangyin' ? 'jiangyin' : 'suzhou'))
const filteredOrders = computed(() => filterOrders(orders.value, listSearch.orders))
const pagedOrders = computed(() => paginateItems(filteredOrders.value, 'orders'))
const outsourceOrders = computed(() => dashboard.value?.outsource_orders ?? [])
const filteredOutsourceOrders = computed(() => filterOrders(outsourceOrders.value, listSearch.outsource))
const pagedOutsourceOrders = computed(() => paginateItems(filteredOutsourceOrders.value, 'outsource'))
const pendingReports = computed(() => dashboard.value?.pending_reports ?? [])
const filteredPendingReports = computed(() => {
  const keyword = listSearch.reports.trim().toLowerCase()
  const source = pendingReports.value
  if (!keyword) return source
  return source.filter((report) =>
    [
      report.report_no,
      report.order_no,
      report.customer,
      report.project_name,
      report.status,
      report.conclusion,
      report.quality_user,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(keyword),
  )
})
const pagedPendingReports = computed(() => paginateItems(filteredPendingReports.value, 'reports'))
const pendingInvoices = computed(() => dashboard.value?.finance?.pending_invoices ?? [])
const issuedInvoices = computed(() => dashboard.value?.finance?.issued_invoices ?? [])
const filteredPendingInvoices = computed(() => filterInvoices(pendingInvoices.value, listSearch.pendingInvoices))
const filteredIssuedInvoices = computed(() => filterInvoices(issuedInvoices.value, listSearch.issuedInvoices))
const pagedPendingInvoices = computed(() => paginateItems(filteredPendingInvoices.value, 'pendingInvoices'))
const pagedIssuedInvoices = computed(() => paginateItems(filteredIssuedInvoices.value, 'issuedInvoices'))

function filterOrders(source: OrderItem[], keywordValue: string) {
  const keyword = keywordValue.trim().toLowerCase()
  if (!keyword) return source
  return source.filter((order) =>
    [
      order.order_no,
      order.customer,
      order.contact,
      order.phone,
      order.project_name,
      order.test_demand,
      order.status,
      order.execution_mode,
      order.expected_delivery_date,
      order.sales_owner,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(keyword),
  )
}

function filterInvoices(source: InvoiceItem[], keywordValue: string) {
  const keyword = keywordValue.trim().toLowerCase()
  if (!keyword) return source
  return source.filter((invoice) =>
    [
      invoice.invoice_no,
      invoice.order_no,
      invoice.report_no,
      invoice.customer,
      invoice.project_name,
      invoice.invoice_amount,
      invoice.invoice_type,
      invoice.invoice_date,
      invoice.pay_status,
      invoice.finish_status,
      invoice.finance_user,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(keyword),
  )
}

function paginateItems<T>(source: T[], key: ListKey) {
  const currentPage = Math.min(listPage[key], listTotalPages(key, source.length))
  const start = (currentPage - 1) * listPageSize[key]
  return source.slice(start, start + listPageSize[key])
}

function listTotalPages(key: ListKey, total: number) {
  return Math.max(1, Math.ceil(total / listPageSize[key]))
}

function listRangeText(key: ListKey, total: number) {
  if (total === 0) return '0 / 0'
  const currentPage = Math.min(listPage[key], listTotalPages(key, total))
  const start = (currentPage - 1) * listPageSize[key] + 1
  const end = Math.min(start + listPageSize[key] - 1, total)
  return `${start}-${end} / ${total}`
}

function resetList(key: ListKey) {
  listPage[key] = 1
}

function previousListPage(key: ListKey) {
  if (listPage[key] > 1) listPage[key] -= 1
}

function nextListPage(key: ListKey, total: number) {
  if (listPage[key] < listTotalPages(key, total)) listPage[key] += 1
}

function openMetric(key: string) {
  activeMetric.value = key
  dashboardSearch.value = ''
  dashboardPage.value = 1
  selectedOrder.value = null
}

function chooseOrder(order: OrderItem) {
  selectedOrder.value = order
}

function resetDashboardList() {
  dashboardPage.value = 1
  selectedOrder.value = null
}

function previousDashboardPage() {
  if (dashboardPage.value > 1) dashboardPage.value -= 1
}

function nextDashboardPage() {
  if (dashboardPage.value < totalDashboardPages.value) dashboardPage.value += 1
}

function filteredLabOrders(key: LabKey) {
  const lab = dashboard.value?.labs?.[key]
  const keyword = listSearch[key].trim().toLowerCase()
  if (!lab) return []
  if (!keyword) return lab.orders
  return lab.orders.filter((order) =>
    [order.order_no, order.customer, order.project_name, order.status, order.remark]
      .join(' ')
      .toLowerCase()
      .includes(keyword),
  )
}

function pagedLabOrders(key: LabKey) {
  return paginateItems(filteredLabOrders(key), key)
}

async function loadMe() {
  const response = await fetch('/api/auth/me/', { credentials: 'include' })
  user.value = await response.json()
}

async function loadDashboard() {
  const response = await fetch('/api/lims/dashboard/', { credentials: 'include' })
  if (response.ok) {
    dashboard.value = await response.json()
    ensureVisibleWorkspace()
  }
}

async function loginSubmit() {
  loginError.value = ''
  const response = await fetch('/api/auth/login/', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(loginForm),
  })
  const data = await response.json()
  if (!response.ok) {
    loginError.value = data.error || '登录失败'
    return
  }
  user.value = data.user
  await loadDashboard()
}

async function logoutSubmit() {
  await fetch('/api/auth/logout/', { method: 'POST', credentials: 'include' })
  user.value = { authenticated: false }
  dashboard.value = null
  activeMenu.value = 'dashboard'
  loginForm.password = ''
}

async function addEmployee() {
  employeeMessage.value = ''
  const response = await fetch('/api/employees/add/', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(employeeForm),
  })
  const data = await response.json()
  if (!response.ok) {
    employeeMessage.value = data.error || '添加失败'
    return
  }
  employeeMessage.value = `已添加员工：${data.employee.display_name}`
  employeeForm.username = ''
  employeeForm.password = ''
  employeeForm.display_name = ''
  employeeForm.email = ''
}

async function createOrder() {
  orderMessage.value = ''
  const response = await fetch('/api/orders/create/', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(orderForm),
  })
  const data = await response.json()
  if (!response.ok) {
    orderMessage.value = data.error || '下单失败'
    return
  }
  orderMessage.value = `下单成功：${data.order.order_no}，已进入商务技术评审`
  Object.assign(orderForm, {
    customer_name: '',
    contact_name: '',
    phone: '',
    project_name: '',
    test_requirements: '',
    expected_sample_arrival: '',
    expected_delivery_date: '',
    quoted_amount: '',
    is_urgent: false,
  })
  showOrderForm.value = false
  await loadDashboard()
}

onMounted(async () => {
  try {
    await loadMe()
    if (user.value.authenticated) await loadDashboard()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main v-if="!loading && !user.authenticated" class="login-page" :style="backgroundStyle">
    <a class="login-brand" href="/">
      <img :src="companyLogo" alt="苏州环测检测技术有限公司 logo" />
      <span>
        <strong>苏州环测检测技术有限公司</strong>
        <small>Laboratory Information Management System</small>
      </span>
    </a>

    <form class="login-panel" @submit.prevent="loginSubmit">
      <p class="login-eyebrow">LIMS LOGIN</p>
      <h1>环测实验室系统</h1>
      <label>
        <span>用户名</span>
        <input v-model="loginForm.username" autocomplete="username" placeholder="请输入用户名" />
      </label>
      <label>
        <span>密码</span>
        <input v-model="loginForm.password" autocomplete="current-password" type="password" placeholder="请输入密码" />
      </label>
      <button type="submit">登录系统</button>
      <p v-if="loginError" class="form-message error">{{ loginError }}</p>
    </form>
  </main>

  <main v-else-if="!loading" class="app-layout">
    <aside class="sidebar">
      <a class="side-brand" href="/">
        <img :src="companyLogo" alt="苏州环测检测技术有限公司 logo" />
        <span>
          <strong>环测 LIMS</strong>
          <small>{{ roleText }}</small>
        </span>
      </a>

      <nav class="side-nav" aria-label="系统功能">
        <section v-for="group in menuGroups" :key="group.title">
          <h2>{{ group.title }}</h2>
          <button
            v-for="item in group.items"
            :key="item.key"
            type="button"
            :class="{ active: activeMenu === item.key }"
            @click="activeMenu = item.key"
          >
            {{ item.label }}
          </button>
        </section>
      </nav>

      <button class="logout-button" type="button" @click="logoutSubmit">退出登录</button>
    </aside>

    <section class="workspace">
      <header class="workspace-header">
        <div>
          <p>苏州环测检测技术有限公司</p>
          <h1>实验室管理（LIMS）系统</h1>
        </div>
        <a v-if="user.is_chairman || hasRole('总经理')" href="/admin/">进入 Django 后台</a>
      </header>

      <section v-if="activeMenu === 'dashboard'" class="content-panel">
        <div class="metric-grid">
          <button
            v-for="item in metricCards"
            :key="item.key"
            type="button"
            :class="{ active: activeMetric === item.key }"
            @click="openMetric(item.key)"
          >
            <strong>{{ item.value }}</strong>
            <span>{{ item.label }}</span>
          </button>
        </div>
        <div class="panel-section-title">
          <h2>{{ metricCards.find((item) => item.key === activeMetric)?.label }}明细</h2>
          <p>点击订单行查看客户、报价、交付、试验需求和当前流程状态。</p>
        </div>
        <div class="split-view">
          <div class="orders-list-panel">
            <div class="list-controls">
              <label class="search-control">
                <span>搜索订单</span>
                <input
                  v-model="dashboardSearch"
                  type="search"
                  placeholder="订单号、客户、项目、状态"
                  @input="resetDashboardList"
                >
              </label>
              <label class="page-size-control">
                <span>每页显示</span>
                <select v-model.number="dashboardPageSize" @change="resetDashboardList">
                  <option :value="10">10 条</option>
                  <option :value="15">15 条</option>
                  <option :value="20">20 条</option>
                </select>
              </label>
            </div>
            <div class="orders-table compact">
            <div class="table-row table-head">
              <span>订单</span>
              <span>客户 / 项目</span>
              <span>状态</span>
              <span>交付</span>
            </div>
            <button
              v-for="order in pagedMetricOrders"
              :key="order.order_no"
              type="button"
              class="table-row table-button"
              @click="chooseOrder(order)"
            >
              <span><strong>{{ order.order_no }}</strong><em v-if="order.is_urgent">加急</em></span>
              <span>{{ order.customer }} / {{ order.project_name }}</span>
              <span>{{ order.status }}</span>
              <span>{{ order.expected_delivery_date || '待确认' }}</span>
            </button>
            <div v-if="filteredMetricOrders.length === 0" class="empty-row">当前没有匹配的订单。</div>
          </div>
            <div class="pagination-bar">
              <span>{{ dashboardRangeText }}</span>
              <div>
                <button type="button" :disabled="dashboardPage <= 1" @click="previousDashboardPage">上一页</button>
                <strong>{{ Math.min(dashboardPage, totalDashboardPages) }} / {{ totalDashboardPages }}</strong>
                <button type="button" :disabled="dashboardPage >= totalDashboardPages" @click="nextDashboardPage">下一页</button>
              </div>
            </div>
          </div>
          <aside class="detail-panel">
            <template v-if="selectedOrder">
              <p class="panel-kicker">订单详情</p>
              <h3>{{ selectedOrder.order_no }}</h3>
              <dl>
                <div><dt>客户</dt><dd>{{ selectedOrder.customer }}</dd></div>
                <div><dt>项目</dt><dd>{{ selectedOrder.project_name }}</dd></div>
                <div><dt>状态</dt><dd>{{ selectedOrder.status }}</dd></div>
                <div><dt>执行路径</dt><dd>{{ selectedOrder.execution_mode }}</dd></div>
                <div><dt>销售</dt><dd>{{ selectedOrder.sales_owner || '未指定' }}</dd></div>
                <div><dt>报价</dt><dd>{{ selectedOrder.total_quote || '0.00' }}</dd></div>
                <div><dt>交付</dt><dd>{{ selectedOrder.expected_delivery_date || '待确认' }}</dd></div>
                <div><dt>需求</dt><dd>{{ selectedOrder.test_demand || '未填写' }}</dd></div>
              </dl>
            </template>
            <p v-else>选择左侧订单后，这里会显示订单的详细状态。</p>
          </aside>
        </div>
      </section>

      <section v-else-if="activeMenu === 'orders'" class="content-panel">
        <div class="panel-toolbar">
          <div>
            <h2>订单管理</h2>
            <p>销售下单后，订单会进入商务技术评审。</p>
          </div>
          <button v-if="canCreateOrder" class="toolbar-button" type="button" @click="showOrderForm = !showOrderForm">
            {{ showOrderForm ? '收起下单' : '销售下单' }}
          </button>
        </div>

        <form v-if="showOrderForm" class="order-form" @submit.prevent="createOrder">
          <label><span>客户名称</span><input v-model="orderForm.customer_name" /></label>
          <label><span>联系人</span><input v-model="orderForm.contact_name" /></label>
          <label><span>联系电话</span><input v-model="orderForm.phone" /></label>
          <label><span>项目名称</span><input v-model="orderForm.project_name" /></label>
          <label><span>预计样品到达</span><input v-model="orderForm.expected_sample_arrival" type="date" /></label>
          <label><span>预计交付日期</span><input v-model="orderForm.expected_delivery_date" type="date" /></label>
          <label><span>报价金额</span><input v-model="orderForm.quoted_amount" type="number" min="0" step="0.01" /></label>
          <label class="checkbox-label"><input v-model="orderForm.is_urgent" type="checkbox" /> 加急订单</label>
          <label class="wide"><span>试验需求</span><textarea v-model="orderForm.test_requirements" rows="4"></textarea></label>
          <button type="submit">提交订单</button>
          <p v-if="orderMessage" class="form-message">{{ orderMessage }}</p>
        </form>

        <div class="list-controls">
          <label class="search-control">
            <span>搜索订单</span>
            <input
              v-model="listSearch.orders"
              type="search"
              placeholder="订单号、客户、项目、状态"
              @input="resetList('orders')"
            >
          </label>
          <label class="page-size-control">
            <span>每页显示</span>
            <select v-model.number="listPageSize.orders" @change="resetList('orders')">
              <option :value="10">10 条</option>
              <option :value="15">15 条</option>
              <option :value="20">20 条</option>
            </select>
          </label>
        </div>
        <div class="orders-table">
          <div class="table-row table-head">
            <span>订单</span>
            <span>客户 / 项目</span>
            <span>路径</span>
            <span>状态</span>
            <span>交付</span>
          </div>
          <div v-for="order in pagedOrders" :key="order.order_no" class="table-row">
            <span><strong>{{ order.order_no }}</strong><em v-if="order.is_urgent">加急</em></span>
            <span>{{ order.customer }} / {{ order.project_name }}</span>
            <span>{{ order.execution_mode }}</span>
            <span>{{ order.status }}</span>
            <span>{{ order.expected_delivery_date || '待确认' }}</span>
          </div>
          <div v-if="filteredOrders.length === 0" class="empty-row">暂无符合条件的订单。</div>
        </div>
        <div class="pagination-bar">
          <span>{{ listRangeText('orders', filteredOrders.length) }}</span>
          <div>
            <button type="button" :disabled="listPage.orders <= 1" @click="previousListPage('orders')">上一页</button>
            <strong>{{ Math.min(listPage.orders, listTotalPages('orders', filteredOrders.length)) }} / {{ listTotalPages('orders', filteredOrders.length) }}</strong>
            <button type="button" :disabled="listPage.orders >= listTotalPages('orders', filteredOrders.length)" @click="nextListPage('orders', filteredOrders.length)">下一页</button>
          </div>
        </div>
      </section>

      <section v-else-if="activeMenu === 'suzhou' || activeMenu === 'jiangyin'" class="content-panel lab-panel">
        <div class="panel-toolbar">
          <div>
            <h2>{{ dashboard?.labs?.[activeMenu]?.name }}</h2>
            <p>上半部分看设备运行和未来排期，下半部分筛选本实验室执行订单。</p>
          </div>
        </div>
        <div class="device-grid">
          <article v-for="device in dashboard?.labs?.[activeMenu]?.devices" :key="device.name" class="device-card">
            <div>
              <h3>{{ device.name }}</h3>
              <span :class="['device-status', device.status === '运行中' ? 'running' : 'idle']">{{ device.status }}</span>
            </div>
            <p v-if="device.order_no">
              正在执行：<strong>{{ device.order_no }}</strong> / {{ device.project_name }}
            </p>
            <p v-else>当前无执行订单。</p>
            <small>预计结束：{{ device.end_time || '暂无' }}</small>
            <ul>
              <li v-for="future in device.future_orders" :key="future.order_no">
                {{ future.order_no }} · {{ future.start_time || '待排' }} 至 {{ future.end_time || '待定' }}
              </li>
              <li v-if="device.future_orders.length === 0">暂无未来排期</li>
            </ul>
          </article>
        </div>
        <div class="filter-block list-controls">
          <label class="search-control">
            <span>订单筛选</span>
            <input
              v-model="listSearch[currentLabKey]"
              type="search"
              placeholder="输入订单号、客户、项目、状态"
              @input="resetList(currentLabKey)"
            >
          </label>
          <label class="page-size-control">
            <span>每页显示</span>
            <select v-model.number="listPageSize[currentLabKey]" @change="resetList(currentLabKey)">
              <option :value="10">10 条</option>
              <option :value="15">15 条</option>
              <option :value="20">20 条</option>
            </select>
          </label>
        </div>
        <div class="orders-table schedule-table">
          <div class="table-row table-head">
            <span>订单</span>
            <span>客户 / 项目</span>
            <span>任务</span>
            <span>排期</span>
            <span>状态</span>
          </div>
          <div v-for="order in pagedLabOrders(currentLabKey)" :key="`${activeMenu}-${order.order_no}-${order.remark}`" class="table-row">
            <span><strong>{{ order.order_no }}</strong></span>
            <span>{{ order.customer }} / {{ order.project_name }}</span>
            <span>{{ order.remark || order.test_type }}</span>
            <span>{{ order.start_time || '待排' }} - {{ order.end_time || '待定' }}</span>
            <span>{{ order.status }} / {{ order.schedule_status }}</span>
          </div>
          <div v-if="filteredLabOrders(currentLabKey).length === 0" class="empty-row">没有匹配的实验室订单。</div>
        </div>
        <div class="pagination-bar">
          <span>{{ listRangeText(currentLabKey, filteredLabOrders(currentLabKey).length) }}</span>
          <div>
            <button type="button" :disabled="listPage[currentLabKey] <= 1" @click="previousListPage(currentLabKey)">上一页</button>
            <strong>{{ Math.min(listPage[currentLabKey], listTotalPages(currentLabKey, filteredLabOrders(currentLabKey).length)) }} / {{ listTotalPages(currentLabKey, filteredLabOrders(currentLabKey).length) }}</strong>
            <button type="button" :disabled="listPage[currentLabKey] >= listTotalPages(currentLabKey, filteredLabOrders(currentLabKey).length)" @click="nextListPage(currentLabKey, filteredLabOrders(currentLabKey).length)">下一页</button>
          </div>
        </div>
      </section>

      <section v-else-if="activeMenu === 'outsource'" class="content-panel">
        <div class="panel-section-title first">
          <h2>委外试验订单</h2>
          <p>展示执行路径为委外或排期中包含外部委托实验室的订单。</p>
        </div>
        <div class="list-controls">
          <label class="search-control">
            <span>搜索订单</span>
            <input
              v-model="listSearch.outsource"
              type="search"
              placeholder="订单号、客户、项目、状态"
              @input="resetList('outsource')"
            >
          </label>
          <label class="page-size-control">
            <span>每页显示</span>
            <select v-model.number="listPageSize.outsource" @change="resetList('outsource')">
              <option :value="10">10 条</option>
              <option :value="15">15 条</option>
              <option :value="20">20 条</option>
            </select>
          </label>
        </div>
        <div class="orders-table">
          <div class="table-row table-head">
            <span>订单</span>
            <span>客户 / 项目</span>
            <span>路径</span>
            <span>状态</span>
            <span>交付</span>
          </div>
          <div v-for="order in pagedOutsourceOrders" :key="order.order_no" class="table-row">
            <span><strong>{{ order.order_no }}</strong><em v-if="order.is_urgent">加急</em></span>
            <span>{{ order.customer }} / {{ order.project_name }}</span>
            <span>{{ order.execution_mode }}</span>
            <span>{{ order.status }}</span>
            <span>{{ order.expected_delivery_date || '待确认' }}</span>
          </div>
          <div v-if="filteredOutsourceOrders.length === 0" class="empty-row">当前没有匹配的委外试验订单。</div>
        </div>
        <div class="pagination-bar">
          <span>{{ listRangeText('outsource', filteredOutsourceOrders.length) }}</span>
          <div>
            <button type="button" :disabled="listPage.outsource <= 1" @click="previousListPage('outsource')">上一页</button>
            <strong>{{ Math.min(listPage.outsource, listTotalPages('outsource', filteredOutsourceOrders.length)) }} / {{ listTotalPages('outsource', filteredOutsourceOrders.length) }}</strong>
            <button type="button" :disabled="listPage.outsource >= listTotalPages('outsource', filteredOutsourceOrders.length)" @click="nextListPage('outsource', filteredOutsourceOrders.length)">下一页</button>
          </div>
        </div>
      </section>

      <section v-else-if="activeMenu === 'reports'" class="content-panel">
        <div class="panel-section-title first">
          <h2>当前待审核报告</h2>
          <p>按当前登录角色显示需要处理的报告；没有待办时显示 0 条。</p>
        </div>
        <div class="list-controls">
          <label class="search-control">
            <span>搜索报告</span>
            <input
              v-model="listSearch.reports"
              type="search"
              placeholder="报告号、订单号、客户、项目、状态"
              @input="resetList('reports')"
            >
          </label>
          <label class="page-size-control">
            <span>每页显示</span>
            <select v-model.number="listPageSize.reports" @change="resetList('reports')">
              <option :value="10">10 条</option>
              <option :value="15">15 条</option>
              <option :value="20">20 条</option>
            </select>
          </label>
        </div>
        <div class="report-list">
          <article v-for="report in pagedPendingReports" :key="report.report_no">
            <div>
              <strong>{{ report.report_no }}</strong>
              <span>{{ report.status }}</span>
            </div>
            <h3>{{ report.order_no }} · {{ report.project_name }}</h3>
            <p>{{ report.customer }}</p>
            <p>{{ report.conclusion || '暂无报告结论' }}</p>
            <small>出具人：{{ report.quality_user || '未记录' }} · 重制次数：{{ report.remake_count }}</small>
          </article>
          <div v-if="filteredPendingReports.length === 0" class="empty-row">当前没有匹配的待审核报告。</div>
        </div>
        <div class="pagination-bar">
          <span>{{ listRangeText('reports', filteredPendingReports.length) }}</span>
          <div>
            <button type="button" :disabled="listPage.reports <= 1" @click="previousListPage('reports')">上一页</button>
            <strong>{{ Math.min(listPage.reports, listTotalPages('reports', filteredPendingReports.length)) }} / {{ listTotalPages('reports', filteredPendingReports.length) }}</strong>
            <button type="button" :disabled="listPage.reports >= listTotalPages('reports', filteredPendingReports.length)" @click="nextListPage('reports', filteredPendingReports.length)">下一页</button>
          </div>
        </div>
      </section>

      <section v-else-if="activeMenu === 'invoice'" class="content-panel">
        <div class="panel-section-title first">
          <h2>财务开票</h2>
          <p>上半部分显示终审通过后等待会计开票的报告，下半部分显示已经开票办结的财务记录。</p>
        </div>

        <div class="panel-toolbar">
          <div>
            <h2>待开票订单</h2>
            <p>报告审核通过后进入这里，后续会接入正式开票操作表单。</p>
          </div>
        </div>
        <div class="list-controls">
          <label class="search-control">
            <span>搜索待开票</span>
            <input
              v-model="listSearch.pendingInvoices"
              type="search"
              placeholder="订单号、报告号、客户、项目"
              @input="resetList('pendingInvoices')"
            >
          </label>
          <label class="page-size-control">
            <span>每页显示</span>
            <select v-model.number="listPageSize.pendingInvoices" @change="resetList('pendingInvoices')">
              <option :value="10">10 条</option>
              <option :value="15">15 条</option>
              <option :value="20">20 条</option>
            </select>
          </label>
        </div>
        <div class="orders-table invoice-table">
          <div class="table-row table-head">
            <span>订单 / 报告</span>
            <span>客户 / 项目</span>
            <span>金额</span>
            <span>状态</span>
            <span>操作人</span>
          </div>
          <div v-for="invoice in pagedPendingInvoices" :key="`${invoice.order_no}-${invoice.report_no}`" class="table-row">
            <span><strong>{{ invoice.order_no }}</strong><small>{{ invoice.report_no }}</small></span>
            <span>{{ invoice.customer }} / {{ invoice.project_name }}</span>
            <span>{{ invoice.invoice_amount }}</span>
            <span>{{ invoice.pay_status }} / {{ invoice.finish_status }}</span>
            <span>{{ invoice.finance_user || '待会计处理' }}</span>
          </div>
          <div v-if="filteredPendingInvoices.length === 0" class="empty-row">当前没有匹配的待开票订单。</div>
        </div>
        <div class="pagination-bar">
          <span>{{ listRangeText('pendingInvoices', filteredPendingInvoices.length) }}</span>
          <div>
            <button type="button" :disabled="listPage.pendingInvoices <= 1" @click="previousListPage('pendingInvoices')">上一页</button>
            <strong>{{ Math.min(listPage.pendingInvoices, listTotalPages('pendingInvoices', filteredPendingInvoices.length)) }} / {{ listTotalPages('pendingInvoices', filteredPendingInvoices.length) }}</strong>
            <button type="button" :disabled="listPage.pendingInvoices >= listTotalPages('pendingInvoices', filteredPendingInvoices.length)" @click="nextListPage('pendingInvoices', filteredPendingInvoices.length)">下一页</button>
          </div>
        </div>

        <div class="panel-toolbar section-gap">
          <div>
            <h2>已开票记录</h2>
            <p>用于追溯发票号码、金额、回款状态和办结状态。</p>
          </div>
        </div>
        <div class="list-controls">
          <label class="search-control">
            <span>搜索发票</span>
            <input
              v-model="listSearch.issuedInvoices"
              type="search"
              placeholder="发票号、订单号、客户、项目、回款状态"
              @input="resetList('issuedInvoices')"
            >
          </label>
          <label class="page-size-control">
            <span>每页显示</span>
            <select v-model.number="listPageSize.issuedInvoices" @change="resetList('issuedInvoices')">
              <option :value="10">10 条</option>
              <option :value="15">15 条</option>
              <option :value="20">20 条</option>
            </select>
          </label>
        </div>
        <div class="orders-table invoice-table">
          <div class="table-row table-head">
            <span>发票 / 订单</span>
            <span>客户 / 项目</span>
            <span>金额</span>
            <span>状态</span>
            <span>操作人</span>
          </div>
          <div v-for="invoice in pagedIssuedInvoices" :key="invoice.invoice_no" class="table-row">
            <span><strong>{{ invoice.invoice_no }}</strong><small>{{ invoice.order_no }} / {{ invoice.report_no }}</small></span>
            <span>{{ invoice.customer }} / {{ invoice.project_name }}</span>
            <span>{{ invoice.invoice_amount }} · {{ invoice.invoice_type }}</span>
            <span>{{ invoice.pay_status }} / {{ invoice.finish_status }}<small>{{ invoice.invoice_date || '未登记日期' }}</small></span>
            <span>{{ invoice.finance_user || '未记录' }}</span>
          </div>
          <div v-if="filteredIssuedInvoices.length === 0" class="empty-row">当前没有匹配的已开票记录。</div>
        </div>
        <div class="pagination-bar">
          <span>{{ listRangeText('issuedInvoices', filteredIssuedInvoices.length) }}</span>
          <div>
            <button type="button" :disabled="listPage.issuedInvoices <= 1" @click="previousListPage('issuedInvoices')">上一页</button>
            <strong>{{ Math.min(listPage.issuedInvoices, listTotalPages('issuedInvoices', filteredIssuedInvoices.length)) }} / {{ listTotalPages('issuedInvoices', filteredIssuedInvoices.length) }}</strong>
            <button type="button" :disabled="listPage.issuedInvoices >= listTotalPages('issuedInvoices', filteredIssuedInvoices.length)" @click="nextListPage('issuedInvoices', filteredIssuedInvoices.length)">下一页</button>
          </div>
        </div>
      </section>

      <section v-else-if="activeMenu === 'employees' && user.is_chairman" class="content-panel employee-panel">
        <div>
          <p class="panel-kicker">董事长权限</p>
          <h2>添加员工</h2>
        </div>
        <form class="employee-form" @submit.prevent="addEmployee">
          <label><span>用户名</span><input v-model="employeeForm.username" /></label>
          <label><span>姓名/昵称</span><input v-model="employeeForm.display_name" /></label>
          <label><span>邮箱</span><input v-model="employeeForm.email" type="email" /></label>
          <label><span>初始密码</span><input v-model="employeeForm.password" type="password" /></label>
          <label>
            <span>角色</span>
            <select v-model="employeeForm.role">
              <option value="销售">销售</option>
              <option value="商务">商务</option>
              <option value="技术">技术</option>
              <option value="质量部">质量部</option>
              <option value="苏州实验室">苏州实验室</option>
              <option value="江阴实验室">江阴实验室</option>
              <option value="委外供应商">委外供应商</option>
              <option value="总经理">总经理</option>
              <option value="会计">会计</option>
              <option value="董事长">董事长</option>
            </select>
          </label>
          <button type="submit">创建员工</button>
          <p v-if="employeeMessage" class="form-message">{{ employeeMessage }}</p>
        </form>
      </section>

      <section v-else class="content-panel placeholder-panel">
        <p class="panel-kicker">模块入口</p>
        <h2>{{ menuGroups.flatMap((group) => group.items).find((item) => item.key === activeMenu)?.label }}</h2>
        <p>该模块会继续接入具体表单、审批动作和明细页面。</p>
      </section>
    </section>
  </main>
</template>
