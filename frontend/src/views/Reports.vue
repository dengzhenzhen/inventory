<template>
  <div>
    <div class="page-card">
      <div class="filter-bar">
        <el-date-picker v-model="range" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始" end-placeholder="结束" />
        <el-button type="primary" @click="load">生成报表</el-button>
        <span class="muted" style="margin-left: auto">按商品尺码移动加权成本计算，退货计入净额</span>
      </div>
      <el-alert v-if="summary.unknown_cost_lines || summary.provisional_cost_lines || summary.dirty_cost_lines" :title="`待核算 ${summary.unknown_cost_lines} 条，暂估 ${summary.provisional_cost_lines} 条，待重算 ${summary.dirty_cost_lines} 条；请到单据中心预览重算`" type="warning" :closable="false" />
      <div class="stat-grid" style="grid-template-columns: repeat(3, 1fr)">
        <div class="stat-card"><div class="label">进货金额</div><div class="value">￥{{ fmtMoney(summary.purchase_amount) }}</div></div>
        <div class="stat-card"><div class="label">销售金额</div><div class="value">￥{{ fmtMoney(summary.sale_amount) }}</div></div>
        <div class="stat-card"><div class="label">毛利</div><div class="value" style="color: #34c38f">￥{{ summary.profit===null?'待核算':fmtMoney(summary.profit) }}</div></div>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :sm="14">
        <div class="page-card">
          <div class="card-title">每日销售金额</div>
          <div class="bars" v-if="daily.length">
            <div class="bar-col" v-for="d in daily" :key="d.date">
              <div class="bar-val">￥{{ fmtMoney(d.amount) }}</div>
              <div class="bar" :style="{ height: barHeight(d.amount) + 'px' }"></div>
              <div class="bar-label">{{ d.date.slice(5) }}</div>
            </div>
          </div>
          <el-empty v-else description="暂无数据" />
        </div>
      </el-col>
      <el-col :xs="24" :sm="10">
        <div class="page-card">
          <div class="card-title">分类进货占比</div>
          <div v-for="c in rank" :key="c.name" class="rank-row">
            <div class="name">{{ c.name }}</div>
            <el-progress :percentage="c.pct" :stroke-width="14" :show-text="false" style="flex: 1" />
            <div class="muted" style="width: 70px; text-align: right">￥{{ fmtMoney(c.amount) }}</div>
          </div>
          <el-empty v-if="!rank.length" description="暂无数据" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { statsApi } from '../api'
import { fmtMoney } from '../utils'

const range = ref(null)
const summary = ref({ purchase_amount: 0, sale_amount: 0, profit: 0 })
const daily = ref([])
const rank = ref([])

function params() {
  return { date_from: range.value?.[0] || undefined, date_to: range.value?.[1] || undefined }
}
function barHeight(v) {
  const max = Math.max(...daily.value.map((d) => d.amount), 1)
  return Math.max(6, Math.round((v / max) * 160))
}
async function load() {
  const p = params()
  const [s, d, r] = await Promise.all([statsApi.summary(p), statsApi.dailySales(p), statsApi.categoryRank(p)])
  summary.value = s
  daily.value = d
  rank.value = r
}
onMounted(load)
</script>

<style scoped>
.rank-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; min-width: 0; }
.rank-row .name { width: 70px; font-size: 13px; flex: none; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank-row .muted { flex: none; }
</style>
