<script setup lang="ts">
import { computed } from 'vue'
import { Check, Clock, CloseBold, Minus, MoreFilled } from '@element-plus/icons-vue'
import type { WorkflowProgress, WorkflowStepItem } from '../types'

const props = defineProps<{
  progress: WorkflowProgress
}>()

const phases = computed(() => {
  const groups = new Map<string, { key: string; title: string; steps: WorkflowStepItem[] }>()
  for (const step of props.progress.steps) {
    if (!groups.has(step.phase)) {
      groups.set(step.phase, { key: step.phase, title: step.phase_title, steps: [] })
    }
    groups.get(step.phase)?.steps.push(step)
  }
  return [...groups.values()]
})

const completionPercent = computed(() => {
  if (!props.progress.total_steps) return 0
  return Math.round((props.progress.completed_steps / props.progress.total_steps) * 100)
})

function phaseNumber(index: number) {
  return String(index + 1).padStart(2, '0')
}

function formatAmount(value: string) {
  const amount = Number(value || 0)
  return Number.isFinite(amount)
    ? amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : value
}
</script>

<template>
  <section class="workflow-progress" aria-label="订单流程节点示意图">
    <header class="workflow-progress-head">
      <div>
        <span class="snapshot-eyebrow">WORKFLOW TRACE</span>
        <h4>订单流程轨迹</h4>
        <p>{{ progress.summary }}</p>
      </div>
      <div class="workflow-progress-summary" aria-live="polite">
        <strong>{{ progress.current_step }}</strong>
        <span>{{ progress.completed_steps }} / {{ progress.total_steps }} 个节点已完成</span>
      </div>
    </header>

    <div class="workflow-progress-meter">
      <el-progress
        :percentage="completionPercent"
        :stroke-width="8"
        :show-text="false"
        color="#059669"
        aria-label="订单流程完成比例"
      />
      <span>{{ completionPercent }}%</span>
    </div>

    <div v-if="progress.preinvoice_count" class="workflow-side-note">
      <span>财务旁路</span>
      已记录 {{ progress.preinvoice_count }} 次预开票，累计 ¥{{ formatAmount(progress.preinvoice_total) }}；预开票不推进主流程。
    </div>

    <ol class="workflow-phase-grid">
      <li v-for="(phase, phaseIndex) in phases" :key="phase.key" class="workflow-phase">
        <div class="workflow-phase-head">
          <span>{{ phaseNumber(phaseIndex) }}</span>
          <strong>{{ phase.title }}</strong>
        </div>
        <ol class="workflow-node-list">
          <li
            v-for="step in phase.steps"
            :key="step.key"
            class="workflow-node"
            :class="`is-${step.state}`"
            :aria-current="step.state === 'current' ? 'step' : undefined"
          >
            <span class="workflow-node-icon" aria-hidden="true">
              <el-icon v-if="step.state === 'completed'"><Check /></el-icon>
              <el-icon v-else-if="step.state === 'current'"><Clock /></el-icon>
              <el-icon v-else-if="step.state === 'rejected'"><CloseBold /></el-icon>
              <el-icon v-else-if="step.state === 'terminated'"><Minus /></el-icon>
              <el-icon v-else><MoreFilled /></el-icon>
            </span>
            <div class="workflow-node-content">
              <div class="workflow-node-title">
                <strong>{{ step.sequence }}. {{ step.title }}</strong>
                <span class="workflow-state-label">{{ step.state_label }}</span>
              </div>
              <p>{{ step.detail }}</p>
              <div class="workflow-node-meta">
                <span>{{ step.owner }}</span>
                <time v-if="step.time">{{ step.time }}</time>
              </div>
            </div>
          </li>
        </ol>
      </li>
    </ol>
  </section>
</template>
