<script setup lang="ts">
import type { OrderItem } from '../types'

defineProps<{
  order?: OrderItem | null
  loading?: boolean
  title?: string
}>()

function formatFileSize(size: number) {
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

function formatQuote(value?: string) {
  const amount = Number(value || 0)
  return Number.isFinite(amount) ? `¥${amount.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}` : value || '¥0.00'
}
</script>

<template>
  <section class="order-snapshot" aria-label="订单信息快照">
    <div class="snapshot-heading">
      <div>
        <span class="snapshot-eyebrow">ORDER CONTEXT</span>
        <h3>{{ title || '订单信息快照' }}</h3>
      </div>
      <el-space v-if="order" wrap>
        <el-tag v-if="order.is_urgent" type="warning">加急</el-tag>
        <el-tag effect="plain">{{ order.status }}</el-tag>
      </el-space>
    </div>

    <el-skeleton v-if="loading" :rows="5" animated />
    <el-empty v-else-if="!order" description="订单详情暂时无法读取" :image-size="64" />
    <el-descriptions v-else :column="2" border class="snapshot-descriptions">
      <el-descriptions-item label="订单号">{{ order.order_no }}</el-descriptions-item>
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
      <el-descriptions-item label="订单报价">{{ formatQuote(order.total_quote) }}</el-descriptions-item>
      <el-descriptions-item label="创建时间">{{ order.created_at || '未记录' }}</el-descriptions-item>
      <el-descriptions-item label="预计样品到达">{{ order.expected_sample_arrival || '待确认' }}</el-descriptions-item>
      <el-descriptions-item label="预计交付">{{ order.expected_delivery_date || '待确认' }}</el-descriptions-item>
      <el-descriptions-item label="试验需求" :span="2">
        <div class="snapshot-long-text">{{ order.test_demand || '未填写' }}</div>
      </el-descriptions-item>
      <el-descriptions-item label="测试方法" :span="2">
        <div class="snapshot-long-text">{{ order.test_method || '未填写' }}</div>
      </el-descriptions-item>
      <el-descriptions-item label="测试标准" :span="2">
        <div class="snapshot-long-text">{{ order.test_standard || '未填写' }}</div>
      </el-descriptions-item>
      <el-descriptions-item label="订单备注" :span="2">
        <div class="snapshot-long-text">{{ order.remark || '无' }}</div>
      </el-descriptions-item>
      <el-descriptions-item label="合同与附件" :span="2">
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
  </section>
</template>
