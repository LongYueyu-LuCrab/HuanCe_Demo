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
  lab_type?: number | null
  lab_name?: string
  lab_position?: string
}

export type OrderItem = {
  order_no: string
  customer: string
  contact?: string
  phone?: string
  project_name: string
  industry_category: 'automotive' | 'military' | 'other'
  industry_label: string
  test_demand?: string
  test_method?: string
  test_standard?: string
  status: string
  status_key: number
  execution_mode: string
  execution_attributes: string[]
  workflow_version: number
  workflow_label: string
  lead_lab_manager: string
  lead_lab_manager_username: string
  sales_confirmed: boolean
  expected_sample_arrival: string
  expected_delivery_date: string
  total_quote?: string
  is_urgent: boolean
  sales_owner?: string
  created_at?: string
  remark?: string
  documents: OrderDocumentItem[]
}

export type OrderDocumentItem = {
  id: number
  type: 'contract' | 'attachment'
  type_label: string
  name: string
  size: number
  download_url: string
}

export type ScheduleItem = {
  id: number
  order_no: string
  customer: string
  project_name: string
  status: string
  status_key: number
  test_type: string
  start_time: string
  end_time: string
  schedule_status: string
  schedule_status_key: number
  lab_manager: string
  device_id: number | null
  device_code: string
  device_name: string
  is_lead: boolean
  sample_arrived: boolean
  sample_arrival_status: string
  sample_arrived_at: string
  sample_photos: SamplePhotoItem[]
  experiment_status: string
  workflow_version: number
  remark: string
}

export type SamplePhotoItem = {
  id: number
  name: string
  size: number
  url: string
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
  action_code: string
  schedule_id: number | null
  change_data: Record<string, { label: string; before: string; after: string }>
  change_summary: string
  create_time: string
}

export type LabDevice = {
  id: number
  device_code: string
  name: string
  lab_type: number
  lab_name: string
  model_spec: string
  capability: string
  status_key: number
  status: string
  configured_status: string
  remark: string
  available: boolean
  unavailable_reason: string
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
  routing_options: {
    suzhou_managers: UserOption[]
    jiangyin_managers: UserOption[]
  }
  pending_reports: ReportItem[]
  finance: {
    pending_invoices: InvoiceItem[]
    issued_invoices: InvoiceItem[]
  }
}

export type UserOption = {
  id: number
  username: string
  name: string
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
