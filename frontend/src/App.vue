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
  project_name: string
  status: string
  status_key: string
  execution_mode: string
  expected_delivery_date: string
  is_urgent: boolean
  sales_owner?: string
}

type Dashboard = {
  company: string
  system: string
  metrics: Record<string, number>
  roles: string[]
  recent_orders: OrderItem[]
}

const user = ref<User>({ authenticated: false })
const dashboard = ref<Dashboard | null>(null)
const activeMenu = ref('dashboard')
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

const backgroundStyle = computed(() => ({
  backgroundImage: `linear-gradient(90deg, rgba(5, 14, 28, 0.54), rgba(5, 14, 28, 0.2)), url(${backgroundImage})`,
}))

const canCreateOrder = computed(() => {
  const roles = user.value.roles || []
  return Boolean(user.value.is_chairman || roles.includes('销售'))
})

const menuGroups = computed(() => [
  {
    title: '工作台',
    items: [
      { key: 'dashboard', label: '业务总览' },
      { key: 'orders', label: '订单管理' },
      { key: 'schedule', label: '排期管理' },
      { key: 'samples', label: '样品台账' },
    ],
  },
  {
    title: '实验室',
    items: [
      { key: 'suzhou', label: '苏州实验室' },
      { key: 'jiangyin', label: '江阴实验室' },
      { key: 'outsource', label: '委外试验' },
      { key: 'reports', label: '报告审核' },
    ],
  },
  {
    title: '财务与系统',
    items: [
      { key: 'invoice', label: '财务开票' },
      { key: 'audit', label: '流程日志' },
      ...(user.value.is_chairman ? [{ key: 'employees', label: '添加员工' }] : []),
    ],
  },
])

const metricCards = computed(() => {
  const metrics = dashboard.value?.metrics
  return [
    { label: '相关订单', value: metrics?.orders ?? 0 },
    { label: '进行中订单', value: metrics?.active_orders ?? 0 },
    { label: '试验执行中', value: metrics?.running_experiments ?? 0 },
    { label: '待处理报告', value: metrics?.pending_reports ?? 0 },
    { label: '变更待闭环', value: metrics?.change_requests ?? 0 },
  ]
})

const roleText = computed(() => user.value.roles?.join(' / ') || '普通用户')
const orders = computed(() => dashboard.value?.recent_orders ?? [])

async function loadMe() {
  const response = await fetch('/api/auth/me/', { credentials: 'include' })
  user.value = await response.json()
}

async function loadDashboard() {
  const response = await fetch('/api/lims/dashboard/', { credentials: 'include' })
  if (response.ok) dashboard.value = await response.json()
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
        <a href="/admin/">进入 Django 后台</a>
      </header>

      <section v-if="activeMenu === 'dashboard'" class="content-panel">
        <div class="metric-grid">
          <article v-for="item in metricCards" :key="item.label">
            <strong>{{ item.value }}</strong>
            <span>{{ item.label }}</span>
          </article>
        </div>
        <div class="panel-section-title">
          <h2>我的相关订单</h2>
          <p>按当前登录角色筛选，流程节点不在总览中铺开。</p>
        </div>
        <div class="orders-table">
          <div class="table-row table-head">
            <span>订单</span>
            <span>客户 / 项目</span>
            <span>路径</span>
            <span>状态</span>
            <span>交付</span>
          </div>
          <div v-for="order in orders" :key="order.order_no" class="table-row">
            <span><strong>{{ order.order_no }}</strong><em v-if="order.is_urgent">加急</em></span>
            <span>{{ order.customer }} / {{ order.project_name }}</span>
            <span>{{ order.execution_mode }}</span>
            <span>{{ order.status }}</span>
            <span>{{ order.expected_delivery_date || '待确认' }}</span>
          </div>
          <div v-if="orders.length === 0" class="empty-row">暂无与当前角色相关的订单。</div>
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

        <p v-if="orderMessage" class="order-result">{{ orderMessage }}</p>

        <div class="orders-table">
          <div class="table-row table-head">
            <span>订单</span>
            <span>客户 / 项目</span>
            <span>路径</span>
            <span>状态</span>
            <span>交付</span>
          </div>
          <div v-for="order in orders" :key="order.order_no" class="table-row">
            <span><strong>{{ order.order_no }}</strong><em v-if="order.is_urgent">加急</em></span>
            <span>{{ order.customer }} / {{ order.project_name }}</span>
            <span>{{ order.execution_mode }}</span>
            <span>{{ order.status }}</span>
            <span>{{ order.expected_delivery_date || '待确认' }}</span>
          </div>
          <div v-if="orders.length === 0" class="empty-row">暂无与当前角色相关的订单。</div>
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
        <p class="panel-kicker">模块规划</p>
        <h2>{{ menuGroups.flatMap(group => group.items).find(item => item.key === activeMenu)?.label }}</h2>
        <p>该模块已预留入口，后续会继续接入具体表单、审批动作和明细页面。</p>
      </section>
    </section>
  </main>
</template>
