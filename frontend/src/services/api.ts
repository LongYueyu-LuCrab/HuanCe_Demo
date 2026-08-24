import type { Dashboard, OrderItem, User } from '../types'

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

export type CreateOrderPayload = {
  customer_name: string
  contact_name: string
  phone: string
  project_name: string
  test_requirements: string
  expected_sample_arrival: string
  expected_delivery_date: string
  quoted_amount: string
  is_urgent: boolean
  industry_category: 'automotive' | 'military' | 'other'
  execution_attributes: Array<'autonomous' | 'outsource'>
  contract_files: File[]
  attachment_files: File[]
}

export async function createOrder(payload: CreateOrderPayload) {
  const formData = new FormData()
  Object.entries(payload).forEach(([key, value]) => {
    if (key === 'contract_files' || key === 'attachment_files') {
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
  const response = await fetch('/api/lims/action/', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return parseJson(response)
}

export type AddEmployeePayload = {
  username: string
  password: string
  display_name: string
  email: string
  role: string
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
