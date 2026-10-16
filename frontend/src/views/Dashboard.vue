<template>
  <div>
    <div class="stat-grid">
      <div class="stat-card"><div class="label">进货金额</div><div class="value">￥{{ fmtMoney(stats.purchase_amount) }}</div></div>
      <div class="stat-card"><div class="label">销售金额</div><div class="value">￥{{ fmtMoney(stats.sale_amount) }}</div></div>
      <div class="stat-card"><div class="label">库存款数</div><div class="value">{{ stats.styles }}<small>款</small></div></div>
      <div class="stat-card"><div class="label">库存件数</div><div class="value">{{ stats.pieces }}<small>件</small></div></div>
    </div>

    <el-row :gutter="16">
      <el-col :span="12">
        <div class="page-card">
          <div class="card-title">最近进货 <el-button link type="primary" @click="$router.push('/purchase-list')">查看全部</el-button></div>
          <el-table :data="purchases" size="small">
            <el-table-column prop="style_code" label="款号" width="110" />
            <el-table-column prop="size_text" label="尺码" width="60" />
            <el-table-column prop="quantity" label="数量" width="60" />
            <el-table-column label="进货价" width="80"><template #default="{ row }">￥{{ fmtMoney(row.cost_price) }}</template></el-table-column>
            <el-table-column prop="purchase_date" label="日期" />
          </el-table>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="page-card">
          <div class="card-title">最近销售 <el-button link type="primary" @click="$router.push('/sale-list')">查看全部</el-button></div>
          <el-table :data="sales" size="small">
            <el-table-column prop="style_code" label="款号" width="110" />
            <el-table-column prop="size_text" label="尺码" width="60" />
            <el-table-column prop="quantity" label="数量" width="60" />
            <el-table-column label="售价" width="80"><template #default="{ row }">￥{{ fmtMoney(row.unit_price) }}</template></el-table-column>
            <el-table-column prop="sale_date" label="日期" />
          </el-table>
        </div>
      </el-col>
    </el-row>

    <div class="page-card">
      <div class="card-title">商品缩略图</div>
      <div style="display: flex; flex-wrap: wrap; gap: 10px">
        <div v-for="p in products" :key="p.id" style="width: 110px">
          <div class="img-box" style="width: 110px; height: 110px; font-size: 14px">
            <img v-if="p.main_image" :src="imgUrl(p.main_image)" alt="" />
            <span v-else>{{ p.style_code.slice(-3) }}</span>
          </div>
          <div class="muted" style="margin-top: 6px">{{ p.style_code }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { productApi, purchaseApi, saleApi, statsApi } from '../api'
import { fmtMoney, imgUrl } from '../utils'

const stats = ref({ purchase_amount: 0, sale_amount: 0, styles: 0, pieces: 0 })
const purchases = ref([])
const sales = ref([])
const products = ref([])

onMounted(async () => {
  const [s, pu, sa, pr] = await Promise.all([
    statsApi.summary(),
    purchaseApi.list({ page: 1, page_size: 5 }),
    saleApi.list({ page: 1, page_size: 5 }),
    productApi.list({ page: 1, page_size: 6 }),
  ])
  stats.value = s
  purchases.value = pu.items
  sales.value = sa.items
  products.value = pr.items
})
</script>
