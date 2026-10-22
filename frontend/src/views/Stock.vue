<template>
  <div class="page-card">
    <div class="filter-bar">
      <el-input v-model="filters.keyword" placeholder="款号 / 品名" clearable style="width: 220px" />
      <el-select v-model="filters.category_id" placeholder="分类" clearable>
        <el-option v-for="c in dicts.category" :key="c.id" :label="c.name" :value="c.id" />
      </el-select>
      <el-checkbox v-model="filters.only_negative">仅看负库存</el-checkbox>
      <el-button type="primary" @click="page=1;load()">查询</el-button>
      <el-button type="success" plain @click="onExport">导出 Excel</el-button>
    </div>

    <el-table :data="rows" border stripe v-loading="loading">
      <el-table-column label="主图" width="80">
        <template #default="{ row }">
          <div class="img-box" style="width: 44px; height: 44px; font-size: 11px">
            <img v-if="row.product.main_image" :src="imgUrl(row.product.main_image)" alt="" />
            <span v-else>{{ row.style_code.slice(-3) }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="style_code" label="款号" width="120" />
      <el-table-column label="品名"><template #default="{ row }">{{ row.product.name }}</template></el-table-column>
      <el-table-column prop="category_name" label="分类" width="90" />
      <el-table-column prop="size_text" label="尺码" width="70" />
      <el-table-column prop="purchased" label="累计入库" width="90" />
      <el-table-column prop="sold" label="累计出库" width="90" />
      <el-table-column label="结存" width="120">
        <template #default="{ row }">
          <span :class="{ neg: row.stock < 0 }">{{ row.stock }}</span>
          <el-tag v-if="row.stock < 0" type="danger" size="small" style="margin-left: 6px">负库存</el-tag>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="prev,pager,next,total" @current-change="load" />
    <div class="muted" style="margin-top: 10px">净库存包含有效进销、退货、盘点调整和作废反向流水。</div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { dictApi, downloadFile, stockApi } from '../api'
import { imgUrl } from '../utils'

const dicts = reactive({ category: [] })
const filters = reactive({ keyword: '', category_id: null, only_negative: false })
const rows = ref([])
const loading = ref(false)
const page = ref(1), total = ref(0)

async function load() {
  loading.value = true
  try {
    const result = await stockApi.list({
      page: page.value,
      keyword: filters.keyword || undefined,
      category_id: filters.category_id || undefined,
      only_negative: filters.only_negative || undefined,
    })
    rows.value=result.items;total.value=result.total
  } finally {
    loading.value = false
  }
}

async function onExport() {
  await downloadFile('/export/stock.xlsx', 'stock.xlsx', filters)
  ElMessage.success('已开始下载')
}

onMounted(async () => {
  dicts.category = await dictApi.list('category')
  await load()
})
</script>
