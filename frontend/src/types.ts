export type User = {
  authenticated: boolean
  id?: number
  username?: string
  display_name?: string
  email?: string
  roles?: string[]
  is_chairman?: boolean
  is_staff?: boolean
  is_superuser?: boolean
}

export type OrderItem = {
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

export type ScheduleItem = {
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

export type TestStandardItem = {
  id: number
  industry: string
  standard_code: string
  standard_name: string
  description: string
  is_active: boolean
}

export type SampleItem = {
  sample_no: string
  order_no: string
  customer: string
  project_name: string
  sample_name: string
  sample_spec: string
  sample_count: number
  storage_condition: string
  actual_arrive_time: string
  sample_status: string
  test_type: string
  quality_user: string
}

export type ChangeItem = {
  order_no: string
  customer: string
  project_name: string
  scene: string
  status: string
  content: string
  change_user: string
  change_time: string
}

export type ReviewItem = {
  order_no: string
  customer: string
  project_name: string
  biz_user: string
  tech_user: string
  result: string
  tech_feasible: string
  reject_reason: string
  review_time: string
}

export type WorkflowEventItem = {
  order_no: string
  customer: string
  project_name: string
  actor: string
  event_type: string
  from_status: string
  to_status: string
  note: string
  create_time: string
}

export type LabDevice = {
  name: string
  status: string
  order_no: string
  project_name: string
  end_time: string
  future_orders: ScheduleItem[]
}

export type LabView = {
  name: string
  devices: LabDevice[]
  orders: ScheduleItem[]
}

export type ReportItem = {
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

export type InvoiceItem = {
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

export type Dashboard = {
  company: string
  system: string
  metrics: Record<string, number>
  payload_limits?: {
    list_limit: number
    workflow_events: number
    note: string
  }
  roles: string[]
  recent_orders: OrderItem[]
  order_groups: Record<string, OrderItem[]>
  labs: {
    suzhou: LabView
    jiangyin: LabView
  }
  outsource_orders: OrderItem[]
  schedules: ScheduleItem[]
  samples: SampleItem[]
  changes: ChangeItem[]
  reviews: ReviewItem[]
  workflow_events: WorkflowEventItem[]
  test_standards: TestStandardItem[]
  pending_reports: ReportItem[]
  finance: {
    pending_invoices: InvoiceItem[]
    issued_invoices: InvoiceItem[]
  }
}

export type MenuItem = {
  key: string
  label: string
  path: string
  icon?: string
}

export type MenuGroup = {
  title: string
  items: MenuItem[]
}
