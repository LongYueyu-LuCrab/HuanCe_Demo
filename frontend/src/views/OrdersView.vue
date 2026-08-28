<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, UploadFilled } from '@element-plus/icons-vue'
import type { UploadFile, UploadFiles, UploadRawFile, UploadUserFile } from 'element-plus'
import OrderTable from '../components/OrderTable.vue'
import OrderSnapshot from '../components/OrderSnapshot.vue'
import { createOrder, exportSalesManagerOrders, fetchOrderDetail, fetchSalesManagerOrders, workflowAction } from '../services/api'
import { useSession } from '../stores/session'
import type { OrderItem } from '../types'

const session = useSession()
const dialogVisible = ref(false)
const submitting = ref(false)
const actionDialogVisible = ref(false)
const actionSubmitting = ref(false)
const activeAction = ref('')
const activeOrder = ref<OrderItem | null>(null)
const actionOrderLoading = ref(false)
const actionForm = reactive<Record<string, unknown>>({})
const contractFileList = ref<UploadUserFile[]>([])
const outsourceContractFileList = ref<UploadUserFile[]>([])
const attachmentFileList = ref<UploadUserFile[]>([])
const form = reactive({
  customer_name: '',
  contact_name: '',
  phone: '',
  project_name: '',
  test_requirements: '',
  test_method: '',
  test_standard: '',
  expected_sample_arrival: '',
  expected_delivery_date: '',
  quoted_amount: '',
  is_urgent: false,
  industry_category: 'other' as 'automotive' | 'military' | 'other',
  execution_attributes: ['autonomous'] as Array<'autonomous' | 'outsource'>,
  outsource_company: '',
  outsource_amount: '',
  entrust_order_no: '',
  undertaking_amount: '',
  outsource_experiment_start_time: '',
  outsource_experiment_end_time: '',
})

const isOutsourceSelected = computed(() => form.execution_attributes.includes('outsource'))

const acceptedFilePattern = /\.(doc|docx|pdf|jpe?g|png)$/i
const maxFileSize = 20 * 1024 * 1024
const maxTotalFileSize = 40 * 1024 * 1024

function validateSelectedFile(file: UploadFile) {
  const raw = file.raw
  if (!raw || !acceptedFilePattern.test(file.name)) {
    ElMessage.error(`${file.name} 格式不支持，仅允许 Word、PDF、JPG、PNG`)
    return false
  }
  if (raw.size > maxFileSize) {
    ElMessage.error(`${file.name} 超过 20MB，请压缩后重新上传`)
    return false
  }
  return true
}

function handleContractChange(file: UploadFile, files: UploadFiles) {
  contractFileList.value = validateSelectedFile(file) ? files : files.filter((item) => item.uid !== file.uid)
}

function handleAttachmentChange(file: UploadFile, files: UploadFiles) {
  attachmentFileList.value = validateSelectedFile(file) ? files : files.filter((item) => item.uid !== file.uid)
}

function handleOutsourceContractChange(file: UploadFile, files: UploadFiles) {
  outsourceContractFileList.value = validateSelectedFile(file) ? files : files.filter((item) => item.uid !== file.uid)
}

function rawFiles(files: UploadUserFile[]) {
  return files.map((file) => file.raw).filter((file): file is UploadRawFile => Boolean(file))
}

const isSalesManager = computed(() => (session.state.user.roles || []).includes('销售经理'))
const isSales = computed(() => (session.state.user.roles || []).includes('销售'))
const managerOrders = ref<OrderItem[]>([])
const managerOrderTotal = ref(0)
const managerOrdersLoading = ref(false)
const managerOrderQuery = reactive({ keyword: '', page: 1, page_size: 10 })
const orders = computed(() => isSalesManager.value
  ? managerOrders.value
  : session.state.dashboard?.order_groups?.orders ?? session.state.dashboard?.recent_orders ?? [])
const isTechnicalReviewer = computed(() => (session.state.user.roles || []).includes('技术'))
const routingOptions = computed(() => session.state.dashboard?.routing_options)
const allLabManagers = computed(() => [
  ...(routingOptions.value?.suzhou_managers || []),
  ...(routingOptions.value?.jiangyin_managers || []),
])
const leadManagerOptions = computed(() => {
  const selectedIds = new Set([
    Number(actionForm.suzhou_manager_id || 0),
    Number(actionForm.jiangyin_manager_id || 0),
    Number(actionForm.outsource_owner_id || 0),
  ])
  return allLabManagers.value.filter((manager) => selectedIds.has(manager.id))
})

async function loadManagerOrders(query = managerOrderQuery) {
  if (!isSalesManager.value) return
  Object.assign(managerOrderQuery, query)
  managerOrdersLoading.value = true
  try {
    const result = await fetchSalesManagerOrders(managerOrderQuery)
    managerOrders.value = result.items
    managerOrderTotal.value = result.total
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '销售订单加载失败')
  } finally {
    managerOrdersLoading.value = false
  }
}

async function exportSalesOrders() {
  try {
    await exportSalesManagerOrders({})
    ElMessage.success(isSalesManager.value ? '全部销售订单 Excel 已生成' : '我的全部订单 Excel 已生成')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导出失败')
  }
}

onMounted(() => {
  void loadManagerOrders()
})

function hasExecutionRoute(route: string) {
  return Array.isArray(actionForm.execution_routes) && actionForm.execution_routes.includes(route)
}

const actionTitleMap: Record<string, string> = {
  review_pass: '评审通过',
  review_reject: '评审驳回',
  order_update: '修改订单并重新提交',
  order_cancel: '退单',
  sales_confirm: '确认无变更',
  create_change: '填写更改单',
  schedule_assign: '排期分配',
  process_change: '处理变更',
  start_test: '开始试验',
  end_test: '实验结束',
  submit_test: '提交实验结果',
  outsource_result: '委外试验结果回传',
  issue_report: '出具检测报告',
}

function openWorkflow(action: string, order: OrderItem) {
  activeAction.value = action
  activeOrder.value = order
  Object.keys(actionForm).forEach((key) => delete actionForm[key])
  Object.assign(actionForm, {
    customer_name: order.customer,
    contact_name: order.contact || '',
    phone: order.phone || '',
    project_name: order.project_name,
    test_demand: order.test_demand || '',
    test_method: order.test_method || '',
    test_standard: order.test_standard || '',
    quoted_amount: order.total_quote || '',
    reason: '',
    reject_reason: '',
    biz_quote_detail: '',
    execution_routes: [] as string[],
    suzhou_manager_id: undefined,
    jiangyin_manager_id: undefined,
    outsource_owner_id: undefined,
    lead_lab_manager_id: undefined,
    suzhou_task: order.test_demand || '',
    jiangyin_task: order.test_demand || '',
    outsource_task: order.test_demand || '',
    note: '',
    change_scene: action === 'create_change' && order.status_key === 4 ? 2 : 1,
    change_content: '',
    new_test_demand: order.test_demand || '',
    test_type: 1,
    plan_start_time: '',
    plan_end_time: '',
    outsource_factory: '',
    outsource_price: '',
    outsource_cycle: '',
    test_item_list: order.test_demand || '',
    test_standard: order.test_standard || '',
    test_raw_data: '',
    test_conclusion_temp: '',
    result_status: '',
    test_start_time: '',
    test_end_time: '',
    report_no: '',
    report_type: 'formal',
    final_conclusion: '',
  })
  actionDialogVisible.value = true
  void loadWorkflowOrder(order.order_no)
}

async function loadWorkflowOrder(orderNo: string) {
  actionOrderLoading.value = true
  try {
    activeOrder.value = await fetchOrderDetail(orderNo)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '订单详情读取失败')
  } finally {
    actionOrderLoading.value = false
  }
}

async function submitWorkflow() {
  if (!activeOrder.value || !activeAction.value) return
  if ((activeAction.value === 'end_test' || activeAction.value === 'outsource_result') && !actionForm.result_status) {
    ElMessage.warning('请选择实验结果')
    return
  }
  actionSubmitting.value = true
  try {
    await workflowAction({
      action: activeAction.value,
      order_no: activeOrder.value.order_no,
      ...actionForm,
    })
    ElMessage.success('流程操作已完成')
    actionDialogVisible.value = false
    await session.refreshDashboard()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '流程操作失败')
  } finally {
    actionSubmitting.value = false
  }
}

async function submit() {
  if (!form.customer_name.trim() || !form.project_name.trim() || !form.test_requirements.trim() || !form.expected_sample_arrival) {
    ElMessage.warning('请填写客户名称、项目名称、试验需求和预计样品到达时间')
    return
  }
  if (form.execution_attributes.length === 0) {
    ElMessage.warning('订单执行属性至少选择“自主”或“委外”之一')
    return
  }
  if (isOutsourceSelected.value) {
    if (
      !form.outsource_company.trim()
      || !form.outsource_amount
      || !form.entrust_order_no.trim()
      || !form.undertaking_amount
      || !form.outsource_experiment_start_time
      || !form.outsource_experiment_end_time
      || rawFiles(outsourceContractFileList.value).length !== 1
    ) {
      ElMessage.warning('委外订单必须完整填写委外资料并上传一份委外合同')
      return
    }
    if (Number(form.outsource_amount) <= 0 || Number(form.undertaking_amount) <= 0) {
      ElMessage.warning('委外金额和承接金额必须大于 0')
      return
    }
    if (new Date(form.outsource_experiment_end_time) <= new Date(form.outsource_experiment_start_time)) {
      ElMessage.warning('委外实验结束时间必须晚于开始时间')
      return
    }
  }
  const selectedFiles = [
    ...rawFiles(contractFileList.value),
    ...(isOutsourceSelected.value ? rawFiles(outsourceContractFileList.value) : []),
    ...rawFiles(attachmentFileList.value),
  ]
  if (selectedFiles.reduce((total, file) => total + file.size, 0) > maxTotalFileSize) {
    ElMessage.warning('合同、委外合同与附件总大小不能超过 40MB')
    return
  }
  submitting.value = true
  try {
    await createOrder({
      ...form,
      contract_files: rawFiles(contractFileList.value),
      outsource_contract_files: isOutsourceSelected.value ? rawFiles(outsourceContractFileList.value) : [],
      attachment_files: rawFiles(attachmentFileList.value),
    })
    ElMessage.success('订单已提交，等待商务技术评审')
    dialogVisible.value = false
    Object.assign(form, {
      customer_name: '',
      contact_name: '',
      phone: '',
      project_name: '',
      test_requirements: '',
      test_method: '',
      test_standard: '',
      expected_sample_arrival: '',
      expected_delivery_date: '',
      quoted_amount: '',
      is_urgent: false,
      industry_category: 'other',
      execution_attributes: ['autonomous'],
      outsource_company: '',
      outsource_amount: '',
      entrust_order_no: '',
      undertaking_amount: '',
      outsource_experiment_start_time: '',
      outsource_experiment_end_time: '',
    })
    contractFileList.value = []
    outsourceContractFileList.value = []
    attachmentFileList.value = []
    await session.refreshDashboard()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '提交失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page-stack">
    <div class="page-toolbar">
      <div>
        <h2>订单管理</h2>
        <p>按当前角色显示可查看订单；销售可从这里发起新订单。</p>
      </div>
      <div class="toolbar-actions">
        <el-button v-if="isSalesManager || isSales" type="primary" plain :icon="Download" @click="exportSalesOrders">
          {{ isSalesManager ? '导出全部销售订单' : '导出我的全部订单' }}
        </el-button>
        <el-button v-if="session.canCreateOrder.value" type="primary" @click="dialogVisible = true">销售下单</el-button>
      </div>
    </div>

    <OrderTable
      :orders="orders"
      :user="session.state.user"
      :remote="isSalesManager"
      :total="managerOrderTotal"
      :loading="managerOrdersLoading"
      @query="loadManagerOrders"
      @workflow="openWorkflow"
    />

    <el-dialog v-model="dialogVisible" title="销售下单" width="min(960px, 94vw)">
      <el-form label-position="top" class="form-grid">
        <el-form-item label="客户名称"><el-input v-model="form.customer_name" /></el-form-item>
        <el-form-item label="联系人"><el-input v-model="form.contact_name" /></el-form-item>
        <el-form-item label="联系电话"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="项目名称"><el-input v-model="form.project_name" /></el-form-item>
        <el-form-item label="预计样品到达" required><el-date-picker v-model="form.expected_sample_arrival" value-format="YYYY-MM-DD" type="date" /></el-form-item>
        <el-form-item label="预计交付日期"><el-date-picker v-model="form.expected_delivery_date" value-format="YYYY-MM-DD" type="date" /></el-form-item>
        <el-form-item label="报价金额"><el-input v-model="form.quoted_amount" type="number" /></el-form-item>
        <el-form-item label="行业属性">
          <el-select v-model="form.industry_category" placeholder="请选择行业属性">
            <el-option label="汽车" value="automotive" />
            <el-option label="军工" value="military" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="加急"><el-switch v-model="form.is_urgent" /></el-form-item>
        <el-form-item label="订单执行属性">
          <el-checkbox-group v-model="form.execution_attributes">
            <el-checkbox value="autonomous">自主</el-checkbox>
            <el-checkbox value="outsource">委外</el-checkbox>
          </el-checkbox-group>
          <div class="field-help">可单选，也可同时选择自主与委外。</div>
        </el-form-item>
        <section v-if="isOutsourceSelected" class="form-wide outsource-intake-section" aria-labelledby="outsource-intake-title">
          <div class="outsource-intake-heading">
            <div>
              <span>OUTSOURCE INTAKE</span>
              <h3 id="outsource-intake-title">委外订单资料</h3>
            </div>
            <el-tag type="danger" effect="plain">全部必填</el-tag>
          </div>
          <div class="form-grid">
            <el-form-item label="委外公司" required>
              <el-input v-model="form.outsource_company" placeholder="填写实际承接试验的委外公司" />
            </el-form-item>
            <el-form-item label="委托单号" required>
              <el-input v-model="form.entrust_order_no" placeholder="填写对外委托业务单号" />
            </el-form-item>
            <el-form-item label="委外金额" required>
              <el-input v-model="form.outsource_amount" type="number" min="0" placeholder="支付给委外公司的成本" />
            </el-form-item>
            <el-form-item label="承接金额" required>
              <el-input v-model="form.undertaking_amount" type="number" min="0" placeholder="向客户承接的项目金额" />
            </el-form-item>
            <el-form-item label="实验开始时间" required>
              <el-date-picker
                v-model="form.outsource_experiment_start_time"
                type="datetime"
                value-format="YYYY-MM-DD HH:mm"
                placeholder="选择计划开始时间"
              />
            </el-form-item>
            <el-form-item label="实验结束时间" required>
              <el-date-picker
                v-model="form.outsource_experiment_end_time"
                type="datetime"
                value-format="YYYY-MM-DD HH:mm"
                placeholder="选择计划结束时间"
              />
            </el-form-item>
            <div class="form-wide order-upload-panel outsource-contract-upload">
              <div class="upload-panel-heading">
                <strong>委外合同</strong>
                <span>必传 1 份</span>
              </div>
              <el-upload
                v-model:file-list="outsourceContractFileList"
                :auto-upload="false"
                :limit="1"
                accept=".doc,.docx,.pdf,.jpg,.jpeg,.png"
                :on-change="handleOutsourceContractChange"
              >
                <el-button :icon="UploadFilled" type="danger" plain>上传委外合同</el-button>
                <template #tip><div class="el-upload__tip">支持 Word、PDF、JPG、PNG，单文件不超过 20MB</div></template>
              </el-upload>
            </div>
          </div>
        </section>
        <el-form-item label="试验需求" class="form-wide"><el-input v-model="form.test_requirements" type="textarea" :rows="4" /></el-form-item>
        <el-form-item label="测试方法" class="form-wide">
          <el-input v-model="form.test_method" type="textarea" :rows="3" placeholder="填写客户指定的试验方法、实施步骤或方法文件编号" />
        </el-form-item>
        <el-form-item label="测试标准" class="form-wide">
          <el-input v-model="form.test_standard" type="textarea" :rows="3" placeholder="填写适用的国标、行标、企标或客户标准编号" />
        </el-form-item>
        <div class="form-wide order-upload-grid">
          <div class="order-upload-panel">
            <div class="upload-panel-heading">
              <strong>合同文件</strong>
              <span>最多 1 份</span>
            </div>
            <el-upload
              v-model:file-list="contractFileList"
              :auto-upload="false"
              :limit="1"
              accept=".doc,.docx,.pdf,.jpg,.jpeg,.png"
              :on-change="handleContractChange"
            >
              <el-button :icon="UploadFilled">上传合同</el-button>
              <template #tip><div class="el-upload__tip">支持 Word、PDF、JPG、PNG，单文件不超过 20MB</div></template>
            </el-upload>
          </div>
          <div class="order-upload-panel">
            <div class="upload-panel-heading">
              <strong>业务附件</strong>
              <span>最多 10 份</span>
            </div>
            <el-upload
              v-model:file-list="attachmentFileList"
              :auto-upload="false"
              :limit="10"
              multiple
              accept=".doc,.docx,.pdf,.jpg,.jpeg,.png"
              :on-change="handleAttachmentChange"
            >
              <el-button :icon="UploadFilled">上传附件</el-button>
              <template #tip><div class="el-upload__tip">支持 Word、PDF、JPG、PNG；单文件 20MB，全部文件合计 40MB</div></template>
            </el-upload>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">提交订单</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="actionDialogVisible" :title="actionTitleMap[activeAction] || '流程操作'" width="min(960px, 94vw)">
      <OrderSnapshot
        :order="activeOrder"
        :loading="actionOrderLoading"
        :title="activeAction === 'review_pass' || activeAction === 'review_reject' ? '待评审订单信息' : '流程订单信息'"
      />
      <el-form label-position="top" class="form-grid action-form">
        <template v-if="activeAction === 'review_pass' || activeAction === 'review_reject'">
          <el-form-item :label="isTechnicalReviewer ? '技术评审说明' : '商务报价/评审说明'" class="form-wide"><el-input v-model="actionForm.biz_quote_detail" type="textarea" :rows="3" /></el-form-item>
          <template v-if="activeAction === 'review_pass' && isTechnicalReviewer && activeOrder?.workflow_version === 2">
            <el-form-item label="执行路径" class="form-wide">
              <el-checkbox-group v-model="actionForm.execution_routes">
                <el-checkbox value="suzhou">苏州内部实验室</el-checkbox>
                <el-checkbox value="jiangyin">江阴内部实验室</el-checkbox>
                <el-checkbox value="outsource">外部委外</el-checkbox>
              </el-checkbox-group>
              <div class="field-help">可多选；选择结果必须与销售填写的“自主/委外”属性一致。</div>
            </el-form-item>
            <template v-if="hasExecutionRoute('suzhou')">
              <el-form-item label="苏州实验室负责人">
                <el-select v-model="actionForm.suzhou_manager_id" placeholder="选择负责人">
                  <el-option v-for="manager in routingOptions?.suzhou_managers || []" :key="manager.id" :label="manager.name" :value="manager.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="苏州任务"><el-input v-model="actionForm.suzhou_task" /></el-form-item>
            </template>
            <template v-if="hasExecutionRoute('jiangyin')">
              <el-form-item label="江阴实验室负责人">
                <el-select v-model="actionForm.jiangyin_manager_id" placeholder="选择负责人">
                  <el-option v-for="manager in routingOptions?.jiangyin_managers || []" :key="manager.id" :label="manager.name" :value="manager.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="江阴任务"><el-input v-model="actionForm.jiangyin_task" /></el-form-item>
            </template>
            <template v-if="hasExecutionRoute('outsource')">
              <el-form-item label="委外管理负责人">
                <el-select v-model="actionForm.outsource_owner_id" placeholder="选择内部负责人">
                  <el-option v-for="manager in allLabManagers" :key="manager.id" :label="manager.name" :value="manager.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="委外任务"><el-input v-model="actionForm.outsource_task" /></el-form-item>
            </template>
            <el-form-item label="主责实验室负责人" class="form-wide">
              <el-select v-model="actionForm.lead_lab_manager_id" placeholder="从上述已分配负责人中选择">
                <el-option v-for="manager in leadManagerOptions" :key="manager.id" :label="manager.name" :value="manager.id" />
              </el-select>
              <div class="field-help">主责负责人负责汇总所有执行路径并出具最终检测报告。</div>
            </el-form-item>
          </template>
          <el-form-item v-if="activeAction === 'review_reject'" label="驳回原因" class="form-wide"><el-input v-model="actionForm.reject_reason" type="textarea" :rows="3" /></el-form-item>
        </template>

        <template v-else-if="activeAction === 'order_update'">
          <el-form-item label="客户名称"><el-input v-model="actionForm.customer_name" /></el-form-item>
          <el-form-item label="联系人"><el-input v-model="actionForm.contact_name" /></el-form-item>
          <el-form-item label="电话"><el-input v-model="actionForm.phone" /></el-form-item>
          <el-form-item label="项目名称"><el-input v-model="actionForm.project_name" /></el-form-item>
          <el-form-item label="报价"><el-input v-model="actionForm.quoted_amount" type="number" /></el-form-item>
          <el-form-item label="试验需求" class="form-wide"><el-input v-model="actionForm.test_demand" type="textarea" :rows="4" /></el-form-item>
          <el-form-item label="测试方法" class="form-wide"><el-input v-model="actionForm.test_method" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="测试标准" class="form-wide"><el-input v-model="actionForm.test_standard" type="textarea" :rows="3" /></el-form-item>
        </template>

        <template v-else-if="activeAction === 'order_cancel'">
          <el-form-item label="退单原因" class="form-wide"><el-input v-model="actionForm.reason" type="textarea" :rows="3" /></el-form-item>
        </template>

        <template v-else-if="activeAction === 'sales_confirm'">
          <el-form-item label="确认说明" class="form-wide"><el-input v-model="actionForm.note" type="textarea" :rows="3" placeholder="确认样品到货时间和试验需求无变更" /></el-form-item>
        </template>

        <template v-else-if="activeAction === 'create_change'">
          <el-form-item label="变更场景">
            <el-select v-model="actionForm.change_scene">
              <el-option label="样品到货前变更" :value="1" />
              <el-option label="试验过程中变更" :value="2" />
            </el-select>
          </el-form-item>
          <el-form-item label="变更后需求" class="form-wide"><el-input v-model="actionForm.new_test_demand" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="变更说明" class="form-wide"><el-input v-model="actionForm.change_content" type="textarea" :rows="3" /></el-form-item>
        </template>

        <template v-else-if="activeAction === 'schedule_assign'">
          <el-form-item label="执行路径">
            <el-select v-model="actionForm.test_type">
              <el-option label="苏州内部实验室" :value="1" />
              <el-option label="江阴内部实验室" :value="2" />
              <el-option label="外部委外" :value="3" />
            </el-select>
          </el-form-item>
          <el-form-item label="计划开始"><el-date-picker v-model="actionForm.plan_start_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item label="计划结束"><el-date-picker v-model="actionForm.plan_end_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item label="委外厂家"><el-input v-model="actionForm.outsource_factory" /></el-form-item>
          <el-form-item label="委外价格"><el-input v-model="actionForm.outsource_price" type="number" /></el-form-item>
          <el-form-item label="委外周期/天"><el-input v-model="actionForm.outsource_cycle" type="number" /></el-form-item>
        </template>

        <template v-else-if="activeAction === 'process_change'">
          <el-form-item label="调整后开始"><el-date-picker v-model="actionForm.plan_start_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item label="调整后结束"><el-date-picker v-model="actionForm.plan_end_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
        </template>

        <template v-else-if="activeAction === 'start_test'">
          <el-form-item label="试验项目" class="form-wide"><el-input v-model="actionForm.test_item_list" disabled type="textarea" :rows="3" /></el-form-item>
        </template>

        <template v-else-if="activeAction === 'end_test'">
          <el-form-item label="实验结果" class="form-wide" required>
            <el-radio-group v-model="actionForm.result_status">
              <el-radio-button value="pass">合格</el-radio-button>
              <el-radio-button value="fail">不合格</el-radio-button>
              <el-radio-button value="abnormal">异常</el-radio-button>
              <el-radio-button value="retest">待复测</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="原始检测数据" class="form-wide"><el-input v-model="actionForm.test_raw_data" type="textarea" :rows="4" /></el-form-item>
          <el-form-item label="实验结论" class="form-wide"><el-input v-model="actionForm.test_conclusion_temp" type="textarea" :rows="3" /></el-form-item>
          <el-alert class="form-wide" title="本操作只结束实验并保存结果，之后仍需点击“提交结果”" type="info" :closable="false" show-icon />
        </template>

        <template v-else-if="activeAction === 'submit_test'">
          <el-alert
            class="form-wide"
            title="确认正式提交实验结果"
            type="warning"
            :closable="false"
            description="全部执行路径都提交结果后，订单才会进入待出报告。"
            show-icon
          />
        </template>

        <template v-else-if="activeAction === 'outsource_result'">
          <el-form-item label="委外试验项目" class="form-wide"><el-input v-model="actionForm.test_item_list" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="执行标准"><el-input v-model="actionForm.test_standard" placeholder="例如：委外厂家报告编号 / 执行标准" /></el-form-item>
          <el-form-item label="委外开始时间"><el-date-picker v-model="actionForm.test_start_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item label="委外完成时间"><el-date-picker v-model="actionForm.test_end_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item label="实验结果" class="form-wide" required>
            <el-radio-group v-model="actionForm.result_status">
              <el-radio-button value="pass">合格</el-radio-button>
              <el-radio-button value="fail">不合格</el-radio-button>
              <el-radio-button value="abnormal">异常</el-radio-button>
              <el-radio-button value="retest">待复测</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="委外原始数据 / 回传摘要" class="form-wide"><el-input v-model="actionForm.test_raw_data" type="textarea" :rows="4" /></el-form-item>
          <el-form-item label="委外实验结论" class="form-wide"><el-input v-model="actionForm.test_conclusion_temp" type="textarea" :rows="3" /></el-form-item>
          <el-alert class="form-wide" title="回传并结束委外实验后，仍需点击“提交结果”" type="info" :closable="false" show-icon />
        </template>

        <template v-else-if="activeAction === 'issue_report'">
          <el-form-item label="报告编号"><el-input v-model="actionForm.report_no" placeholder="留空自动生成" /></el-form-item>
          <el-form-item label="报告版本" class="form-wide">
            <el-radio-group v-model="actionForm.report_type">
              <el-radio-button value="formal">正式版</el-radio-button>
              <el-radio-button value="draft">草稿版</el-radio-button>
              <el-radio-button value="data_only">仅数据</el-radio-button>
            </el-radio-group>
            <div class="field-help">正式版带示例章占位水印，草稿版无水印，仅数据版聚焦实验数据。</div>
          </el-form-item>
          <el-form-item label="最终结论" class="form-wide"><el-input v-model="actionForm.final_conclusion" type="textarea" :rows="4" /></el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="actionDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="actionSubmitting" @click="submitWorkflow">确认执行</el-button>
      </template>
    </el-dialog>
  </div>
</template>
