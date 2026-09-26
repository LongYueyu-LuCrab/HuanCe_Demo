const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const ts = require('typescript')
const vue = require('vue')

// Execute the real component script with isolated transport/session dependencies.
// Browser regression separately covers Element Plus date-change events and rendering.
function component(name) {
  const calls = [], pending = [], messages = []
  const api = {
    fetchAvailableDevices: (...args) => new Promise((resolve, reject) => pending.push({ args, resolve, reject })),
    fetchOrderDetail: async () => ({}),
    fetchLaboratoryOrders: async () => ({ items: [], total: 0 }),
    workflowAction: async (payload) => calls.push({ ...payload }),
  }
  const source = fs.readFileSync(path.join(__dirname, '../src/views', name + '.vue'), 'utf8')
    .split('<script setup lang="ts">')[1].split('</script>')[0]
  const output = ts.transpileModule(source + '\nexport { form, openWorkflow, onPlanDatesChange, submitWorkflow, availabilityLoading, availabilityMessage };', {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText
  const exports = {}
  vm.runInNewContext(output, {
    exports, defineProps: () => ({}),
    require: (id) => {
      if (id === 'vue') return { ...vue, watch: () => {} }
      if (id === 'vue-router') return { useRoute: () => ({ params: {}, query: {} }), useRouter: () => ({}) }
      if (id === 'element-plus') return { ElMessage: { error: (m) => messages.push(m), warning: (m) => messages.push(m), success: () => {} } }
      if (id.includes('services/api')) return api
      if (id.includes('stores/session')) return { useSession: () => ({ state: { user: { roles: ['苏州实验室'] } }, refreshDashboard: async () => {} }) }
      return {}
    },
  })
  const schedule = { id: 1, order_no: 'REGRESSION', test_type: '苏州内部实验室', start_time: '2026-09-23', end_time: '2026-09-24', device_id: 7, sample_arrived: false, sample_photos: [] }
  exports.openWorkflow('schedule_assign', schedule)
  return { ...exports, pending, calls, messages, schedule }
}
const available = [{ id: 7, available: true }]
const settle = () => new Promise((resolve) => setImmediate(resolve))

for (const name of ['LabView', 'ScheduleView']) {
  test(name + ': advancing dates keeps the available original device and submits new dates', async () => {
    const c = component(name)
    c.pending.shift().resolve(available)
    await settle()
    c.form.plan_start_time = '2026-09-22'
    const changed = c.onPlanDatesChange()
    assert.equal(c.form.device_id, undefined)
    c.pending.shift().resolve(available)
    await changed
    assert.equal(c.form.device_id, 7)
    const submitted = c.submitWorkflow()
    assert.equal(c.calls.length, 0)
    c.pending.shift().resolve(available)
    await submitted
    assert.equal(c.calls.length, 1)
    assert.equal(c.calls[0].device_id, 7)
    assert.equal(c.calls[0].plan_start_time, '2026-09-22')
  })
  test(name + ': stale old-date availability cannot override a new-date conflict', async () => {
    const c = component(name)
    const old = c.pending.shift()
    c.form.plan_start_time = '2026-09-22'
    const changed = c.onPlanDatesChange()
    c.pending.shift().resolve([{ id: 7, available: false, unavailable_reason: '与其他订单排期冲突' }])
    await changed
    old.resolve(available)
    await settle()
    assert.equal(c.form.device_id, undefined)
    assert.match(c.availabilityMessage.value, /排期冲突/)
    const submitted = c.submitWorkflow()
    c.pending.shift().resolve([{ id: 7, available: false }])
    await submitted
    assert.equal(c.calls.length, 0)
  })
  test(name + ': failed availability can be retried without losing preferred device', async () => {
    const c = component(name)
    c.pending.shift().reject(new Error('query failed'))
    await settle()
    assert.equal(c.form.device_id, undefined)
    const submitted = c.submitWorkflow()
    c.pending.shift().resolve(available)
    await submitted
    assert.equal(c.calls[0].device_id, 7)
  })
}
