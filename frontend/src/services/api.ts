import type { Dashboard, LabDevice, OrderItem, User } from '../types'

async function parseJson<T>(response: Response): Promise<T> {
  const data = await response.json()
  if (!response.ok) {
    throw new Error(data.error || '请求失败')
  }
  return data
}

export async function fetchCurrentUser(): Promise<User> {
  const response = await fetch('/api/auth/me/', { credentials: 'include' })
  return response.json()
}

export async function login(username: string, password: string): Promise<{ ok: boolean; user: User }> {
  const response = await fetch('/api/auth/login/', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  return parseJson(response)
}

export async function logout(): Promise<void> {
  await fetch('/api/auth/logout/', { method: 'POST', credentials: 'include' })
}

export async function fetchDashboard(): Promise<Dashboard> {
  const response = await fetch('/api/lims/dashboard/?limit=50', { credentials: 'include' })
  return parseJson(response)
}

export async function fetchOrderDetail(orderNo: string): Promise<OrderItem> {
  const response = await fetch(`/api/orders/${encodeURIComponent(orderNo)}/`, { credentials: 'include' })
  const data = await parseJson<{ ok: boolean; order: OrderItem }>(response)
  return data.order
}

export type SalesOrderQuery = {
  keyword?: string
  order_status?: string
  page?: number
  page_size?: number
}

function salesOrderParams(query: SalesOrderQuery) {
  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    params.set(key, String(value))
  })
  return params
}

export async function fetchSalesManagerOrders(query: SalesOrderQuery) {
  const response = await fetch(`/api/sales/orders/?${salesOrderParams(query)}`, { credentials: 'include' })
  return parseJson<{ ok: boolean; total: number; page: number; page_size: number; items: OrderItem[] }>(response)
}

export async function exportSalesManagerOrders(query: SalesOrderQuery): Promise<void> {
  const response = await fetch(`/api/sales/orders/export/?${salesOrderParams(query)}`, { credentials: 'include' })
  if (!response.ok) {
    const data = await response.json()
    throw new Error(data.error || '导出失败')
  }
  const blob = await response.blob()
  const disposition = response.headers.get('Content-Disposition') || ''
  const match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  const filename = match ? decodeURIComponent(match[1]) : '全部销售订单.xlsx'
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export type CreateOrderPayload = {
  customer_name: string
  contact_name: string
  phone: string
  project_name: string
  test_requirements: string
  test_method: string
  test_standard: string
  expected_sample_arrival: string
  expected_delivery_date: string
  quoted_amount: string
  is_urgent: boolean
  industry_category: 'automotive' | 'military' | 'other'
  execution_attributes: Array<'autonomous' | 'outsource'>
  outsource_company: string
  outsource_amount: string
  entrust_order_no: string
  undertaking_amount: string
  outsource_experiment_start_time: string
  outsource_experiment_end_time: string
  contract_files: File[]
  outsource_contract_files: File[]
  attachment_files: File[]
}

export async function createOrder(payload: CreateOrderPayload) {
  const formData = new FormData()
  Object.entries(payload).forEach(([key, value]) => {
    if (key.endsWith('_files')) {
      const files = value as File[]
      files.forEach((file) => formData.append(key, file))
      return
    }
    if (key === 'execution_attributes') {
      const attributes = value as string[]
      attributes.forEach((attribute) => formData.append(key, attribute))
      return
    }
    formData.append(key, typeof value === 'boolean' ? String(value) : String(value ?? ''))
  })
  const response = await fetch('/api/orders/create/', {
    method: 'POST',
    credentials: 'include',
    body: formData,
  })
  return parseJson(response)
}

export type WorkflowActionPayload = {
  action: string
  order_no?: string
  report_no?: string
  invoice_no?: string
  [key: string]: unknown
}

export async function workflowAction(payload: WorkflowActionPayload) {
  const hasFiles = Object.values(payload).some((value) => Array.isArray(value) && value.some((item) => item instanceof File))
  let body: BodyInit
  let headers: HeadersInit | undefined
  if (hasFiles) {
    const formData = new FormData()
    Object.entries(payload).forEach(([key, value]) => {
      if (Array.isArray(value)) {
        value.forEach((item) => formData.append(key, item instanceof File ? item : String(item)))
      } else if (value !== undefined && value !== null) {
        formData.append(key, typeof value === 'boolean' ? String(value) : String(value))
      }
    })
    body = formData
  } else {
    headers = { 'Content-Type': 'application/json' }
    body = JSON.stringify(payload)
  }
  const response = await fetch('/api/lims/action/', {
    method: 'POST',
    credentials: 'include',
    headers,
    body,
  })
  return parseJson(response)
}

export async function fetchLabDevices(): Promise<LabDevice[]> {
  const response = await fetch('/api/labs/devices/', { credentials: 'include' })
  const data = await parseJson<{ ok: boolean; devices: LabDevice[] }>(response)
  return data.devices
}

export async function fetchAvailableDevices(scheduleId: number, startDate: string, endDate: string): Promise<LabDevice[]> {
  const params = new URLSearchParams({ schedule_id: String(scheduleId), start_date: startDate, end_date: endDate })
  const response = await fetch(`/api/labs/devices/availability/?${params}`, { credentials: 'include' })
  const data = await parseJson<{ ok: boolean; devices: LabDevice[] }>(response)
  return data.devices
}

export type LabOrderQuery = {
  lab_type: number
  keyword?: string
  order_status?: string
  schedule_status?: string
  device_id?: string
  start_date?: string
  end_date?: string
  schedule_ids?: number[]
  page?: number
  page_size?: number
}

function labOrderParams(query: LabOrderQuery) {
  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    params.set(key, Array.isArray(value) ? value.join(',') : String(value))
  })
  return params
}

export async function fetchLaboratoryOrders(query: LabOrderQuery) {
  const response = await fetch(`/api/labs/orders/?${labOrderParams(query)}`, { credentials: 'include' })
  return parseJson<{ ok: boolean; total: number; items: import('../types').ScheduleItem[] }>(response)
}

export async function exportLaboratoryOrders(query: LabOrderQuery): Promise<void> {
  const response = await fetch(`/api/labs/orders/export/?${labOrderParams(query)}`, { credentials: 'include' })
  if (!response.ok) {
    const data = await response.json()
    throw new Error(data.error || '导出失败')
  }
  const blob = await response.blob()
  const disposition = response.headers.get('Content-Disposition') || ''
  const match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  const filename = match ? decodeURIComponent(match[1]) : '实验室订单台账.xlsx'
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export type LabDevicePayload = {
  device_code?: string
  device_name: string
  lab_type?: number
  model_spec?: string
  capability?: string
  device_status?: number
  remark?: string
}

export async function createLabDevice(payload: LabDevicePayload): Promise<LabDevice> {
  const response = await fetch('/api/labs/devices/', {
    method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  })
  const data = await parseJson<{ ok: boolean; device: LabDevice }>(response)
  return data.device
}

export async function updateLabDevice(deviceId: number, payload: LabDevicePayload): Promise<LabDevice> {
  const response = await fetch(`/api/labs/devices/${deviceId}/`, {
    method: 'PATCH', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  })
  const data = await parseJson<{ ok: boolean; device: LabDevice }>(response)
  return data.device
}

export async function deleteLabDevice(deviceId: number): Promise<void> {
  const response = await fetch(`/api/labs/devices/${deviceId}/`, { method: 'DELETE', credentials: 'include' })
  await parseJson(response)
}

export type AddEmployeePayload = {
  username: string
  password: string
  display_name: string
  email: string
  role: string
  lab_type?: number
}

export async function addEmployee(payload: AddEmployeePayload) {
  const response = await fetch('/api/employees/add/', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return parseJson(response)
}
