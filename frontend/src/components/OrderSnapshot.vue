<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadUserFile } from 'element-plus'
import type { OrderItem } from '../types'
import WorkflowProgress from './WorkflowProgress.vue'
import OutsourceBadge from './OutsourceBadge.vue'
import { useSession } from '../stores/session'
import { workflowAction } from '../services/api'

const props = withDefaults(defineProps<{
  order?: OrderItem | null
  loading?: boolean
  showActions?: boolean
  title?: string
  orderSequence?: string[]
}>(), { showActions: true })

const emit = defineEmits<{
  navigateOrder: [orderNo: string]
  workflowCompleted: []
}>()

const session = useSession()
const activeSection = ref('overview')
const sampleArrivalVisible = ref(false)
const sampleArrivalSubmitting = ref(false)
const sampleArrivalScheduleId = ref<number | null>(null)
const samplePhotoFiles = ref<UploadUserFile[]>([])
const labRoles = computed(() => new Set(session.state.user.roles || []))
const isLabAccount = computed(() => (
  labRoles.value.has('苏州实验室')
  || labRoles.value.has('江阴实验室')
  || labRoles.value.has('实验操作员')
  || labRoles.value.has('商务部')
))
const canViewContracts = computed(() => Boolean(props.order?.can_view_contracts))
const actionableSchedules = computed(() => {
  if (!isLabAccount.value || !props.order) return []
  return (props.order.schedule_records || []).filter((schedule) => {
    const canSubmitResult = schedule.experiment_status.includes('待提交结果')
    if ([6, 7].includes(props.order?.status_key || 0)) return false
    if (![3, 4].includes(schedule.status_key) || schedule.schedule_status_key === 5) return false
    if (schedule.schedule_status_key === 4 && !canSubmitResult) return false
    if (labRoles.value.has('商务部')) return schedule.schedule_status_key !== 2
    if (labRoles.value.has('实验操作员')) return schedule.lab_type === session.state.user.lab_type
    return schedule.lab_manager_username === session.state.user.username
  })
})
const currentSteps = computed(() => props.order?.workflow_progress?.steps.filter((step) => step.state === 'current') || [])
const routeGroups = computed(() => {
  const records = props.order?.schedule_records || []
  const groups = new Map<string, { key: string; label: string; records: typeof records }>()
  for (const record of records) {
    const key = record.lab_type === 2 ? 'jiangyin' : record.is_outsource ? 'outsource' : 'suzhou'
    const label = key === 'jiangyin' ? '江阴实验室' : key === 'outsource' ? '外部委外' : '苏州实验室'
    if (!groups.has(key)) groups.set(key, { key, label, records: [] })
    groups.get(key)?.records.push(record)
  }
  return [...groups.values()]
})
const orderPosition = computed(() => props.order && props.orderSequence?.length ? props.orderSequence.indexOf(props.order.order_no) : -1)
const canNavigatePrevious = computed(() => orderPosition.value > 0)
const canNavigateNext = computed(() => orderPosition.value >= 0 && orderPosition.value < (props.orderSequence?.length || 0) - 1)

function navigateOrder(offset: number) {
  const index = orderPosition.value + offset
  const orderNo = props.orderSequence?.[index]
  if (orderNo) emit('navigateOrder', orderNo)
}

function isSection(...sections: string[]) {
  return sections.includes(activeSection.value)
}

function openLabAction(scheduleId: number, labType: number | null, action: 'schedule_assign' | 'sample_arrival' | 'process_change' | 'start_test' | 'end_test' | 'submit_test') {
  if (action === 'sample_arrival') {
    sampleArrivalScheduleId.value = scheduleId
    samplePhotoFiles.value = []
    sampleArrivalVisible.value = true
    return
  }
  const lab = labType === 2 ? 'jiangyin' : 'suzhou'
  window.location.assign(`/labs/${lab}?order=${encodeURIComponent(props.order?.order_no || '')}&schedule=${scheduleId}&action=${action}`)
}

async function submitSampleArrival() {
  if (!props.order?.order_no || !sampleArrivalScheduleId.value) return
  if (samplePhotoFiles.value.length === 0) {
    ElMessage.warning('样品入库必须上传至少一张样品图片')
    return
  }
  sampleArrivalSubmitting.value = true
  try {
    await workflowAction({
      action: 'sample_arrival',
      order_no: props.order.order_no,
      schedule_id: sampleArrivalScheduleId.value,
      sample_arrived: true,
      sample_photos: samplePhotoFiles.value.map((item) => item.raw).filter((file): file is File => Boolean(file)),
    })
    ElMessage.success('样品入库完成，当前订单已刷新')
    sampleArrivalVisible.value = false
    await session.refreshDashboard()
    emit('workflowCompleted')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '样品入库失败')
  } finally {
    sampleArrivalSubmitting.value = false
  }
}

function formatFileSize(size: number) {
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

function formatQuote(value?: string) {
  const amount = Number(value || 0)
  return Number.isFinite(amount) ? `¥${amount.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}` : value || '¥0.00'
}

function resultTagType(result: string): 'success' | 'danger' | 'warning' | 'info' {
  if (result === 'pass') return 'success'
  if (result === 'fail') return 'danger'
  if (result === 'abnormal') return 'warning'
  return 'info'
}
</script>

<template>
  <section class="order-snapshot" aria-label="订单信息快照">
    <div class="snapshot-heading">
      <div>
        <h3>{{ title || '订单信息快照' }}</h3>
        <p v-if="order" class="snapshot-context-line">
          {{ order.order_no }} · {{ order.customer }} · {{ order.project_name || '未填写项目名称' }}
        </p>
      </div>
      <el-space v-if="order" wrap>
        <el-button v-if="orderSequence?.length" size="small" plain :disabled="!canNavigatePrevious" @click="navigateOrder(-1)">上一订单</el-button>
        <el-button v-if="orderSequence?.length" size="small" plain :disabled="!canNavigateNext" @click="navigateOrder(1)">下一订单</el-button>
        <el-tag v-if="order.is_urgent" type="warning">加急</el-tag>
        <el-tag effect="plain">{{ order.workflow_progress?.summary || order.status }}</el-tag>
      </el-space>
    </div>

    <el-skeleton v-if="loading" :rows="5" animated />
    <el-empty v-else-if="!order" description="订单详情暂时无法读取" :image-size="64" />
    <template v-else>
      <nav class="snapshot-tabs" aria-label="订单详情分区">
        <button :class="{ 'is-active': activeSection === 'overview' }" type="button" @click="activeSection = 'overview'">流程总览</button>
        <button :class="{ 'is-active': activeSection === 'execution' }" type="button" @click="activeSection = 'execution'">执行任务 <span>{{ order.schedule_records?.length || 0 }}</span></button>
        <button :class="{ 'is-active': activeSection === 'report' }" type="button" @click="activeSection = 'report'">报告与财务</button>
        <button :class="{ 'is-active': activeSection === 'documents' }" type="button" @click="activeSection = 'documents'">资料与备注</button>
      </nav>

      <WorkflowProgress v-if="order.workflow_progress && isSection('overview')" :progress="order.workflow_progress" />
      <section v-if="isSection('overview') && order.workflow_progress" class="workflow-route-summary" aria-label="执行路径摘要">
        <div class="section-heading-row">
          <div><h4>执行路径</h4><p>并行任务中最晚完成的路径决定整体订单进入报告阶段。</p></div>
          <strong>{{ routeGroups.length }} 条路径</strong>
        </div>
        <div class="workflow-route-grid">
          <article v-for="group in routeGroups" :key="group.key" class="workflow-route-card">
            <header><strong>{{ group.label }}</strong><span>{{ group.records.length }} 项任务</span></header>
            <div v-for="record in group.records" :key="record.id" class="workflow-route-row">
              <span>{{ record.test_type }}</span>
              <span class="workflow-route-status">{{ record.experiment_status || record.schedule_status || record.sample_arrival_status || '待处理' }}</span>
            </div>
          </article>
          <div v-if="!routeGroups.length" class="workflow-route-empty">尚未分配执行路径</div>
        </div>
      </section>
      <section v-if="isSection('overview', 'execution') && showActions !== false && actionableSchedules.length" class="snapshot-action-panel" aria-label="当前实验室操作">
        <div>
          <strong>当前节点可操作</strong>
          <p>排期、样品入库和实验执行分别记录操作人员、时间和变更内容。</p>
        </div>
        <div v-for="schedule in actionableSchedules" :key="schedule.id" class="snapshot-action-row">
          <span>{{ schedule.test_type }} · {{ schedule.remark || order.project_name }}</span>
          <el-space wrap>
            <el-button v-if="![4, 5].includes(schedule.schedule_status_key)" type="primary" @click="openLabAction(schedule.id, schedule.lab_type, schedule.schedule_status_key === 2 ? 'process_change' : 'schedule_assign')">
              {{ schedule.schedule_status_key === 2 ? '处理变更并排期' : schedule.is_scheduled ? '重新排期' : '排期 / 排台' }}
            </el-button>
            <el-button v-if="!labRoles.has('商务部') && ![4, 5].includes(schedule.schedule_status_key)" type="success" @click="openLabAction(schedule.id, schedule.lab_type, 'sample_arrival')">
              {{ schedule.sample_arrived ? '补充样品图片' : '样品入库' }}
            </el-button>
            <el-button
              v-if="!labRoles.has('商务部') && !schedule.test_type.includes('委外') && schedule.schedule_status_key !== 2 && schedule.is_scheduled && schedule.sample_arrived && schedule.device_id && !schedule.experiment_status"
              type="primary"
              @click="openLabAction(schedule.id, schedule.lab_type, 'start_test')"
            >开始试验</el-button>
            <el-button
              v-if="!labRoles.has('商务部') && schedule.experiment_status.includes('试验中') && schedule.schedule_status_key !== 2"
              type="warning"
              @click="openLabAction(schedule.id, schedule.lab_type, 'end_test')"
            >实验结束</el-button>
            <el-button
              v-if="!labRoles.has('商务部') && schedule.experiment_status.includes('待提交结果') && !schedule.schedule_status.includes('变更')"
              type="success"
              @click="openLabAction(schedule.id, schedule.lab_type, 'submit_test')"
            >提交结果</el-button>
          </el-space>
        </div>
      </section>
      <el-descriptions v-if="isSection('overview')" :column="2" border class="snapshot-descriptions">
      <el-descriptions-item label="订单号">
        <span class="order-reference">
          <strong>{{ order.order_no }}</strong>
          <OutsourceBadge :visible="order.is_outsource" />
        </span>
      </el-descriptions-item>
      <el-descriptions-item label="销售">{{ order.sales_owner || '未记录' }}</el-descriptions-item>
      <el-descriptions-item label="客户单位">{{ order.customer }}</el-descriptions-item>
      <el-descriptions-item label="联系人 / 电话">
        {{ [order.contact, order.phone].filter(Boolean).join(' / ') || '未填写' }}
      </el-descriptions-item>
      <el-descriptions-item label="项目名称">{{ order.project_name }}</el-descriptions-item>
      <el-descriptions-item label="行业属性">{{ order.industry_label || '其他' }}</el-descriptions-item>
      <el-descriptions-item label="订单执行属性">
        <el-space wrap :size="6">
          <el-tag v-for="attribute in order.execution_attributes" :key="attribute" size="small" effect="plain">
            {{ attribute }}
          </el-tag>
        </el-space>
      </el-descriptions-item>
      <el-descriptions-item label="当前执行路径">{{ order.execution_mode }}</el-descriptions-item>
      <el-descriptions-item label="工作流">{{ order.workflow_label }}</el-descriptions-item>
      <el-descriptions-item label="主责实验室负责人">{{ order.workflow_version === 1 ? '质量部' : (order.lead_lab_manager || '待技术分配') }}</el-descriptions-item>
      <el-descriptions-item v-if="order.can_view_amounts" label="订单报价">{{ formatQuote(order.total_quote) }}</el-descriptions-item>
      <el-descriptions-item label="创建时间">{{ order.created_at || '未记录' }}</el-descriptions-item>
      <el-descriptions-item label="预计样品到达">{{ order.expected_sample_arrival || '待确认' }}</el-descriptions-item>
      <el-descriptions-item label="预计交付">{{ order.expected_delivery_date || '待确认' }}</el-descriptions-item>
      <el-descriptions-item v-if="order.is_outsource" label="委外订单资料" :span="2">
        <section v-if="order.outsource_info" class="outsource-summary" aria-label="委外订单资料">
          <dl class="outsource-summary-grid">
            <div><dt>委外公司</dt><dd>{{ order.outsource_info.outsource_company }}</dd></div>
            <div><dt>委托单号</dt><dd>{{ order.outsource_info.entrust_order_no }}</dd></div>
            <div v-if="order.can_view_amounts"><dt>委外金额</dt><dd>{{ formatQuote(order.outsource_info.outsource_amount) }}</dd></div>
            <div v-if="order.can_view_amounts"><dt>承接金额</dt><dd>{{ formatQuote(order.outsource_info.undertaking_amount) }}</dd></div>
            <div><dt>实验开始</dt><dd>{{ order.outsource_info.experiment_start_time }}</dd></div>
            <div><dt>实验结束</dt><dd>{{ order.outsource_info.experiment_end_time }}</dd></div>
          </dl>
          <div v-if="canViewContracts" class="outsource-contract-links">
            <strong>委外合同</strong>
            <a
              v-for="document in order.documents.filter((item) => item.type === 'outsource_contract')"
              :key="document.id"
              :href="document.download_url"
              class="document-link"
            >
              <el-tag size="small" type="danger" effect="plain">委外合同</el-tag>
              <span>{{ document.name }}</span>
              <small>{{ formatFileSize(document.size) }}</small>
            </a>
          </div>
        </section>
        <el-alert
          v-else
          title="历史委外订单未录入销售阶段委外资料"
          type="warning"
          :closable="false"
          show-icon
        />
      </el-descriptions-item>
      <el-descriptions-item v-if="order.sample_records !== undefined && isSection('execution')" label="样品流转" :span="2">
        <div v-if="order.sample_records.length" class="sample-lifecycle-list">
          <section v-for="record in order.sample_records" :key="`${record.schedule_id}-${record.sample_no || 'pending'}`" class="sample-lifecycle-record">
            <div class="sample-lifecycle-head">
              <div>
                <strong>{{ record.sample_no || '待生成样品编号' }}</strong>
                <span>{{ record.test_type }}<template v-if="record.task_name"> · {{ record.task_name }}</template></span>
              </div>
              <el-tag size="small" effect="plain" :type="record.outbound_time ? 'info' : record.actual_arrive_time ? 'success' : 'warning'">
                {{ record.sample_status }}
              </el-tag>
            </div>
            <dl class="sample-lifecycle-times">
              <div><dt>预入库时间</dt><dd>{{ record.expected_arrive_time || '待确认' }}</dd></div>
              <div><dt>实际入库时间</dt><dd>{{ record.actual_arrive_time || '尚未入库' }}</dd></div>
              <div><dt>出库时间</dt><dd>{{ record.outbound_time || '尚未出库' }}</dd></div>
              <div><dt>操作人员</dt><dd>{{ record.outbound_by || record.registered_by || '未记录' }}</dd></div>
            </dl>
            <div v-if="record.photos.length" class="sample-photo-strip">
              <el-image
                v-for="photo in record.photos"
                :key="photo.id"
                :src="photo.url"
                :preview-src-list="record.photos.map((item) => item.url)"
                :alt="photo.name"
                fit="cover"
                preview-teleported
                class="sample-photo"
              />
            </div>
            <span v-else class="cell-sub">暂无入库照片</span>
          </section>
        </div>
        <span v-else class="cell-sub">订单尚未分配实验室任务</span>
      </el-descriptions-item>
      <el-descriptions-item v-if="order.report_records !== undefined && isSection('report')" label="检测报告" :span="2">
        <div v-if="order.report_records.length" class="report-record-list">
          <section v-for="report in order.report_records" :key="report.id" class="report-record-item">
            <div>
              <strong>{{ report.report_no }}</strong>
              <span>{{ report.report_type_label }} · {{ report.status }}</span>
              <small>{{ report.generated_at || '生成时间未记录' }}</small>
            </div>
            <a v-if="report.has_file" :href="report.download_url" class="report-download-link">下载 PDF</a>
            <el-tag v-else type="warning" effect="plain">文件待生成</el-tag>
          </section>
        </div>
        <span v-else class="cell-sub">该订单尚未出具检测报告</span>
      </el-descriptions-item>
      <el-descriptions-item v-if="order.experiment_records !== undefined && isSection('execution')" label="实验结果" :span="2">
        <div v-if="order.experiment_records.length" class="sample-lifecycle-list">
          <section v-for="record in order.experiment_records" :key="`${record.schedule_id}-${record.started_at}`" class="sample-lifecycle-record">
            <div class="sample-lifecycle-head">
              <div>
                <strong>{{ record.test_type }}</strong>
                <span>{{ record.task_name || '未填写实验项目' }}</span>
              </div>
              <el-space wrap :size="6">
                <el-tag size="small" effect="plain">{{ record.status }}</el-tag>
                <el-tag v-if="record.result" size="small" :type="resultTagType(record.result_key)">{{ record.result }}</el-tag>
              </el-space>
            </div>
            <dl class="sample-lifecycle-times">
              <div><dt>开始时间</dt><dd>{{ record.started_at || '未记录' }}</dd></div>
              <div><dt>结束时间</dt><dd>{{ record.ended_at || '未结束' }}</dd></div>
              <div><dt>操作人员</dt><dd>{{ record.operator || '未记录' }}</dd></div>
              <div><dt>实验结论</dt><dd>{{ record.conclusion || '未填写' }}</dd></div>
            </dl>
            <div class="snapshot-long-text"><strong>原始数据：</strong>{{ record.raw_data || '未填写' }}</div>
          </section>
        </div>
        <span v-else class="cell-sub">订单尚未开始实验</span>
      </el-descriptions-item>
      <el-descriptions-item v-if="isSection('documents')" label="试验需求" :span="2">
        <div class="snapshot-long-text">{{ order.test_demand || '未填写' }}</div>
      </el-descriptions-item>
      <el-descriptions-item v-if="isSection('documents')" label="测试方法" :span="2">
        <div class="snapshot-long-text">{{ order.test_method || '未填写' }}</div>
      </el-descriptions-item>
      <el-descriptions-item v-if="isSection('documents')" label="测试标准" :span="2">
        <div class="snapshot-long-text">{{ order.test_standard || '未填写' }}</div>
      </el-descriptions-item>
      <el-descriptions-item v-if="isSection('documents')" label="订单备注" :span="2">
        <div class="snapshot-long-text">{{ order.remark || '无' }}</div>
      </el-descriptions-item>
      <el-descriptions-item v-if="isSection('documents')" label="合同与附件" :span="2">
        <div v-if="order.documents?.length" class="document-list">
          <a
            v-for="document in order.documents"
            :key="document.id"
            :href="document.download_url"
            class="document-link"
          >
            <el-tag size="small" effect="plain">{{ document.type_label }}</el-tag>
            <span>{{ document.name }}</span>
            <small>{{ formatFileSize(document.size) }}</small>
          </a>
        </div>
        <span v-else class="cell-sub">销售未上传合同或附件</span>
      </el-descriptions-item>
      </el-descriptions>
      <section v-if="isSection('execution')" class="snapshot-tab-section">
        <div class="section-heading-row"><div><h4>执行任务</h4><p>按实验室路径查看排期、样品、设备和实验状态。</p></div><strong>{{ order.schedule_records?.length || 0 }} 项</strong></div>
        <div v-if="order.schedule_records?.length" class="execution-task-list">
          <article v-for="record in order.schedule_records" :key="record.id" class="execution-task-row">
            <div class="execution-task-main"><strong>{{ record.test_type }}</strong><span>{{ record.lab_type === 2 ? '江阴实验室' : record.is_outsource ? '外部委外' : '苏州实验室' }} · {{ record.lab_manager || '待分配负责人' }}</span></div>
            <div class="execution-task-state"><strong>{{ record.experiment_status || record.schedule_status || '待处理' }}</strong><span>{{ record.device_name || '设备待分配' }}</span></div>
            <el-tag size="small" effect="plain" :type="record.sample_arrived ? 'success' : 'warning'">{{ record.sample_arrived ? '样品已到' : '等待样品' }}</el-tag>
          </article>
        </div>
        <el-empty v-else description="尚未分配执行任务" :image-size="64" />
      </section>
      <section v-if="isSection('report')" class="snapshot-tab-section">
        <div class="section-heading-row"><div><h4>报告与财务</h4><p>报告状态、审核进度和开票信息集中在这里。</p></div></div>
        <div v-if="order.report_records?.length" class="report-record-list">
          <section v-for="report in order.report_records" :key="report.id" class="report-record-item">
            <div><strong>{{ report.report_no }}</strong><span>{{ report.report_type_label }} · {{ report.status }}</span><small>{{ report.generated_at || '生成时间未记录' }}</small></div>
            <a v-if="report.has_file" :href="report.download_url" class="report-download-link">下载 PDF</a><el-tag v-else type="warning" effect="plain">文件待生成</el-tag>
          </section>
        </div>
        <div v-else class="snapshot-empty-note">检测报告尚未生成，当前节点：{{ currentSteps.map((step) => step.title).join('、') || order.status }}</div>
        <div class="finance-context-grid"><div v-if="order.can_view_amounts"><span>订单报价</span><strong>{{ formatQuote(order.total_quote) }}</strong></div><div><span>预计交付</span><strong>{{ order.expected_delivery_date || '待确认' }}</strong></div><div><span>工作流</span><strong>{{ order.workflow_label }}</strong></div></div>
      </section>
      <section v-if="isSection('documents')" class="snapshot-tab-section">
        <div class="section-heading-row"><div><h4>资料与备注</h4><p>需求、标准、合同和补充说明统一归档。</p></div></div>
        <div class="document-context-grid">
          <div><span>试验需求</span><p class="snapshot-long-text">{{ order.test_demand || '未填写' }}</p></div>
          <div><span>测试方法</span><p class="snapshot-long-text">{{ order.test_method || '未填写' }}</p></div>
          <div><span>测试标准</span><p class="snapshot-long-text">{{ order.test_standard || '未填写' }}</p></div>
          <div><span>订单备注</span><p class="snapshot-long-text">{{ order.remark || '无' }}</p></div>
        </div>
        <div class="document-list document-context-list" v-if="order.documents?.length"><a v-for="document in order.documents" :key="document.id" :href="document.download_url" class="document-link"><el-tag size="small" effect="plain">{{ document.type_label }}</el-tag><span>{{ document.name }}</span><small>{{ formatFileSize(document.size) }}</small></a></div>
        <div v-else class="snapshot-empty-note">销售未上传合同或附件</div>
      </section>
    </template>
  </section>

  <el-dialog
    v-model="sampleArrivalVisible"
    title="办理样品入库"
    width="min(560px, 92vw)"
    append-to-body
  >
    <el-alert
      title="确认样品已到达"
      description="操作将在当前订单详情内完成，不会跳转到实验任务页面。系统会记录入库时间、操作账号和现场照片。"
      type="success"
      :closable="false"
      show-icon
    />
    <el-form label-position="top" class="mt-16">
      <el-form-item label="样品入库照片" required>
        <el-upload v-model:file-list="samplePhotoFiles" :auto-upload="false" multiple accept=".jpg,.jpeg,.png">
          <el-button type="primary" plain>上传样品图片</el-button>
          <template #tip><div class="el-upload__tip">支持 JPG、PNG；单张不超过 10MB，本次合计不超过 30MB。</div></template>
        </el-upload>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="sampleArrivalVisible = false">取消</el-button>
      <el-button type="primary" :loading="sampleArrivalSubmitting" @click="submitSampleArrival">确认入库</el-button>
    </template>
  </el-dialog>
</template>
