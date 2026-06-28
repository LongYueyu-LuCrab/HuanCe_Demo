import type { Dashboard, User } from '../types'

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
  const response = await fetch('/api/lims/dashboard/', { credentials: 'include' })
  return parseJson(response)
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
}

export async function createOrder(payload: CreateOrderPayload) {
  const response = await fetch('/api/orders/create/', {
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
