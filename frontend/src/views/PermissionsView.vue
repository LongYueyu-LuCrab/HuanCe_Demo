<script setup lang="ts">
const rows = [
  { role: '董事长', scope: '全局订单、实验室、财务与系统', actions: '商务评审、退单、员工、权限核对' },
  { role: '总经理', scope: '全局订单与报告财务', actions: '技术评审、报告终审、财务核对' },
  { role: '销售经理', scope: '全部销售订单', actions: '订单查询、销售订单档案、报告初审' },
  { role: '销售', scope: '本人客户订单', actions: '下单、修改重提、退单、报告初审' },
  { role: '商务部', scope: '全部订单与实验室协同', actions: '下单、排期协调、报告初审' },
  { role: '苏州实验室 / 江阴实验室', scope: '所属实验室任务与样品', actions: '排期、样品、实验结果、委外' },
  { role: '实验操作员', scope: '所属实验室分配任务', actions: '样品流转、开始/结束实验、提交结果' },
  { role: '会计', scope: '财务开票与订单核对', actions: '预开票、最终开票、回款、作废' },
  { role: '质量部', scope: '历史 V1 订单流程', actions: '历史排期、报告与变更处理' },
]
</script>

<template>
  <div class="page-stack">
    <div class="page-toolbar">
      <div>
        <h2>权限矩阵</h2>
        <p>用于核对角色的菜单入口、数据范围和关键流程动作；实际权限仍以后端校验为准。</p>
      </div>
    </div>
    <el-card shadow="never" class="hc-card">
      <el-table :data="rows" empty-text="暂无权限配置">
        <el-table-column prop="role" label="角色" min-width="190" />
        <el-table-column prop="scope" label="数据范围" min-width="300" />
        <el-table-column prop="actions" label="关键动作" min-width="420" />
      </el-table>
    </el-card>
    <el-alert title="提示：权限矩阵是协作说明，不提供绕过权限的入口；新增角色或调整岗位后，请同步更新此表。" type="info" :closable="false" show-icon />
  </div>
</template>
