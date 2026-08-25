import type { Dashboard, MenuGroup, MenuItem, User } from './types'

function roleSet(user: User) {
  return new Set(user.roles || [])
}

function group(title: string, items: MenuItem[]): MenuGroup | null {
  return items.length ? { title, items } : null
}

export function hasRole(user: User, role: string) {
  return roleSet(user).has(role)
}

export function canSeeAllBusiness(user: User) {
  return Boolean(user.is_chairman || hasRole(user, '总经理'))
}

export function getMenuGroups(user: User): MenuGroup[] {
  if (user.is_chairman) {
    return [
      group('工作台', [
        { key: 'dashboard', label: '业务总览', path: '/dashboard', icon: 'DataBoard' },
        { key: 'orders', label: '订单管理', path: '/orders', icon: 'Tickets' },
        { key: 'schedule', label: '排期管理', path: '/schedule', icon: 'Calendar' },
      ]),
      group('实验室', [
        { key: 'suzhou', label: '苏州实验室', path: '/labs/suzhou', icon: 'Cpu' },
        { key: 'jiangyin', label: '江阴实验室', path: '/labs/jiangyin', icon: 'Operation' },
        { key: 'devices', label: '设备管理', path: '/devices', icon: 'Tools' },
        { key: 'outsource', label: '委外试验', path: '/outsource', icon: 'Van' },
        { key: 'reports', label: '报告审核', path: '/reports', icon: 'DocumentChecked' },
      ]),
      group('财务与系统', [
        { key: 'invoice', label: '财务开票', path: '/finance', icon: 'Money' },
        { key: 'audit', label: '流程日志', path: '/audit', icon: 'Clock' },
        { key: 'employees', label: '添加员工', path: '/employees', icon: 'UserFilled' },
      ]),
    ].filter(Boolean) as MenuGroup[]
  }

  if (hasRole(user, '销售')) {
    return [
      group('销售工作台', [
        { key: 'dashboard', label: '我的看板', path: '/dashboard', icon: 'DataBoard' },
        { key: 'orders', label: '我的订单', path: '/orders', icon: 'Tickets' },
        { key: 'reports', label: '报告初审', path: '/reports', icon: 'DocumentChecked' },
      ]),
      group('追溯', [{ key: 'audit', label: '订单档案', path: '/audit', icon: 'Clock' }]),
    ].filter(Boolean) as MenuGroup[]
  }

  if (hasRole(user, '商务')) {
    return [
      group('商务工作台', [
        { key: 'dashboard', label: '评审看板', path: '/dashboard', icon: 'DataBoard' },
        { key: 'orders', label: '订单评审中心', path: '/orders', icon: 'Tickets' },
        { key: 'audit', label: '报价与评审台账', path: '/audit', icon: 'Clock' },
      ]),
    ].filter(Boolean) as MenuGroup[]
  }

  if (hasRole(user, '技术')) {
    return [
      group('技术工作台', [
        { key: 'dashboard', label: '技术看板', path: '/dashboard', icon: 'DataBoard' },
        { key: 'orders', label: '技术评审工作台', path: '/orders', icon: 'Tickets' },
        { key: 'audit', label: '检测标准与记录', path: '/audit', icon: 'Clock' },
      ]),
    ].filter(Boolean) as MenuGroup[]
  }

  if (hasRole(user, '质量部')) {
    return [
      group('历史质量流程', [
        { key: 'dashboard', label: 'V1 在途订单', path: '/dashboard', icon: 'DataBoard' },
        { key: 'orders', label: '历史订单处理', path: '/orders', icon: 'Tickets' },
        { key: 'schedule', label: '历史排期', path: '/schedule', icon: 'Calendar' },
        { key: 'reports', label: '历史报告', path: '/reports', icon: 'DocumentChecked' },
        { key: 'audit', label: '流程日志', path: '/audit', icon: 'Clock' },
      ]),
    ].filter(Boolean) as MenuGroup[]
  }

  if (hasRole(user, '苏州实验室')) {
    return [group('苏州实验室', [
      { key: 'dashboard', label: '我的工作台', path: '/dashboard', icon: 'DataBoard' },
      { key: 'orders', label: '我的订单', path: '/orders', icon: 'Tickets' },
      { key: 'suzhou', label: '实验室任务', path: '/labs/suzhou', icon: 'Cpu' },
      { key: 'devices', label: '设备管理', path: '/devices', icon: 'Tools' },
      { key: 'schedule', label: '我的排期', path: '/schedule', icon: 'Calendar' },
      { key: 'outsource', label: '我负责的委外', path: '/outsource', icon: 'Van' },
      { key: 'reports', label: '报告任务', path: '/reports', icon: 'DocumentChecked' },
      { key: 'audit', label: '相关变更记录', path: '/audit', icon: 'Clock' },
    ])].filter(Boolean) as MenuGroup[]
  }

  if (hasRole(user, '江阴实验室')) {
    return [group('江阴实验室', [
      { key: 'dashboard', label: '我的工作台', path: '/dashboard', icon: 'DataBoard' },
      { key: 'orders', label: '我的订单', path: '/orders', icon: 'Tickets' },
      { key: 'jiangyin', label: '实验室任务', path: '/labs/jiangyin', icon: 'Operation' },
      { key: 'devices', label: '设备管理', path: '/devices', icon: 'Tools' },
      { key: 'schedule', label: '我的排期', path: '/schedule', icon: 'Calendar' },
      { key: 'outsource', label: '我负责的委外', path: '/outsource', icon: 'Van' },
      { key: 'reports', label: '报告任务', path: '/reports', icon: 'DocumentChecked' },
      { key: 'audit', label: '相关变更记录', path: '/audit', icon: 'Clock' },
    ])].filter(Boolean) as MenuGroup[]
  }

  if (hasRole(user, '实验操作员')) {
    const isJiangyin = user.lab_type === 2
    const labKey = isJiangyin ? 'jiangyin' : 'suzhou'
    const labName = isJiangyin ? '江阴实验室' : '苏州实验室'
    return [group(`${labName}操作台`, [
      { key: 'dashboard', label: '我的工作台', path: '/dashboard', icon: 'DataBoard' },
      { key: 'orders', label: '实验室订单', path: '/orders', icon: 'Tickets' },
      { key: labKey, label: '试验任务', path: `/labs/${labKey}`, icon: isJiangyin ? 'Operation' : 'Cpu' },
      { key: 'schedule', label: '排期与操作', path: '/schedule', icon: 'Calendar' },
      { key: 'outsource', label: '委外任务', path: '/outsource', icon: 'Van' },
      { key: 'reports', label: '报告任务', path: '/reports', icon: 'DocumentChecked' },
      { key: 'audit', label: '操作历史', path: '/audit', icon: 'Clock' },
    ])].filter(Boolean) as MenuGroup[]
  }

  if (hasRole(user, '总经理')) {
    return [
      group('经营总览', [
        { key: 'dashboard', label: '全局看板', path: '/dashboard', icon: 'DataBoard' },
        { key: 'orders', label: '全局订单查询', path: '/orders', icon: 'Tickets' },
        { key: 'suzhou', label: '苏州负荷', path: '/labs/suzhou', icon: 'Cpu' },
        { key: 'jiangyin', label: '江阴负荷', path: '/labs/jiangyin', icon: 'Operation' },
        { key: 'outsource', label: '委外占比', path: '/outsource', icon: 'Van' },
      ]),
      group('审批与财务', [
        { key: 'reports', label: '报告终审', path: '/reports', icon: 'DocumentChecked' },
        { key: 'invoice', label: '财务台账', path: '/finance', icon: 'Money' },
        { key: 'audit', label: '全链路档案', path: '/audit', icon: 'Clock' },
      ]),
    ].filter(Boolean) as MenuGroup[]
  }

  if (hasRole(user, '会计')) {
    return [group('财务工作台', [
      { key: 'dashboard', label: '财务看板', path: '/dashboard', icon: 'DataBoard' },
      { key: 'invoice', label: '财务开票', path: '/finance', icon: 'Money' },
      { key: 'orders', label: '订单核对', path: '/orders', icon: 'Tickets' },
      { key: 'reports', label: '报告核对', path: '/reports', icon: 'DocumentChecked' },
    ])].filter(Boolean) as MenuGroup[]
  }

  return [group('工作台', [{ key: 'dashboard', label: '业务总览', path: '/dashboard', icon: 'DataBoard' }])].filter(Boolean) as MenuGroup[]
}

export function getMetricCards(user: User, dashboard: Dashboard | null) {
  const metrics = dashboard?.metrics
  if (hasRole(user, '销售') && !canSeeAllBusiness(user)) {
    return [
      { key: 'orders', label: '我的客户订单', value: metrics?.orders ?? 0 },
      { key: 'active_orders', label: '我的进行中订单', value: metrics?.active_orders ?? 0 },
      { key: 'pending_reports', label: '待我初审报告', value: metrics?.pending_reports ?? 0 },
      { key: 'change_requests', label: '我的变更待确认', value: metrics?.change_requests ?? 0 },
    ]
  }
  if ((hasRole(user, '商务') || hasRole(user, '技术')) && !canSeeAllBusiness(user)) {
    return [
      { key: 'orders', label: '待评审订单', value: metrics?.orders ?? 0 },
      { key: 'active_orders', label: '评审中订单', value: metrics?.active_orders ?? 0 },
      { key: 'change_requests', label: '评审驳回/变更', value: metrics?.change_requests ?? 0 },
    ]
  }
  if (hasRole(user, '质量部') && !canSeeAllBusiness(user)) {
    return [
      { key: 'active_orders', label: '待排期/试验订单', value: metrics?.active_orders ?? 0 },
      { key: 'running_experiments', label: '试验中订单', value: metrics?.running_experiments ?? 0 },
      { key: 'pending_reports', label: '待制作/重制报告', value: metrics?.pending_reports ?? 0 },
      { key: 'change_requests', label: '变更待调整排期', value: metrics?.change_requests ?? 0 },
    ]
  }
  if ((hasRole(user, '苏州实验室') || hasRole(user, '江阴实验室') || hasRole(user, '实验操作员')) && !canSeeAllBusiness(user)) {
    return [
      { key: 'orders', label: '分配给我的试验单', value: metrics?.orders ?? 0 },
      { key: 'running_experiments', label: '我的试验执行中', value: metrics?.running_experiments ?? 0 },
      { key: 'change_requests', label: '试验变更提醒', value: metrics?.change_requests ?? 0 },
    ]
  }
  if (hasRole(user, '会计') && !canSeeAllBusiness(user)) {
    const pendingInvoices = dashboard?.finance?.pending_invoices?.length ?? 0
    const issuedInvoices = dashboard?.finance?.issued_invoices?.length ?? 0
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
}
