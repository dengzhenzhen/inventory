<template>
  <div class="page-card">
    <div class="filter-bar">
      <el-input v-model="filters.style_code" placeholder="款号" clearable />
      <el-select v-model="filters.category_id" placeholder="分类" clearable>
        <el-option v-for="c in dicts.category" :key="c.id" :label="c.name" :value="c.id" />
      </el-select>
      <el-select v-model="filters.supplier_id" placeholder="厂家" clearable>
        <el-option v-for="s in dicts.supplier" :key="s.id" :label="s.name" :value="s.id" />
      </el-select>
      <el-select v-model="filters.size_id" placeholder="尺码" clearable>
        <el-option v-for="s in dicts.size" :key="s.id" :label="s.name" :value="s.id" />
      </el-select>
      <el-date-picker v-model="range" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始" end-placeholder="结束" />
      <el-button type="primary" @click="load">查询</el-button>
      <el-button @click="resetFilters">重置</el-button>
      <el-button type="success" plain @click="onExport">导出 Excel</el-button>
    </div>

    <el-table :data="rows" border stripe v-loading="loading">
      <el-table-column prop="style_code" label="款号" width="120" />
      <el-table-column prop="category_name" label="分类" width="90" />
      <el-table-column prop="supplier_name" label="厂家" width="160" />
      <el-table-column prop="size_text" label="尺码" width="70" />
      <el-table-column prop="quantity" label="数量" width="70" />
      <el-table-column label="进货价" width="90"><template #default="{ row }">￥{{ fmtMoney(row.cost_price) }}</template></el-table-column>
      <el-table-column label="金额" width="100"><template #default="{ row }">￥{{ fmtMoney(row.amount) }}</template></el-table-column>
      <el-table-column prop="purchase_date" label="日期" width="120" />
      <el-table-column prop="remark" label="备注" show-overflow-tooltip />
      <el-table-column label="操作" width="130" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" size="small" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      style="margin-top: 14px; justify-content: flex-end"
      layout="total, prev, pager, next"
      :total="total"
      :page-size="pageSize"
      :current-page="page"
      @current-change="onPage"
    />

    <el-dialog v-model="dialog" title="编辑进货记录" width="520px">
      <el-form :model="edit" label-width="80px">
        <el-form-item label="尺码">
          <el-select v-model="edit.size_text" filterable allow-create style="width: 100%">
            <el-option v-for="s in dicts.size" :key="s.id" :label="s.name" :value="s.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="数量"><el-input-number v-model="edit.quantity" :min="1" style="width: 100%" /></el-form-item>
        <el-form-item label="进货价"><el-input-number v-model="edit.cost_price" :min="0" :precision="2" style="width: 100%" /></el-form-item>
        <el-form-item label="日期"><el-date-picker v-model="edit.purchase_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="edit.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { dictApi, downloadFile, purchaseApi } from '../api'
import { fmtMoney } from '../utils'

const dicts = reactive({ category: [], supplier: [], size: [] })
const filters = reactive({ style_code: '', category_id: null, supplier_id: null, size_id: null })
const range = ref(null)
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)

const dialog = ref(false)
const edit = reactive({ id: null, size_text: '', quantity: 1, cost_price: 0, purchase_date: '', remark: '' })

async function loadDicts() {
  const [c, s, z] = await Promise.all([dictApi.list('category'), dictApi.list('supplier'), dictApi.list('size')])
  dicts.category = c
  dicts.supplier = s
  dicts.size = z
}

async function load() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize,
      style_code: filters.style_code || undefined,
      category_id: filters.category_id || undefined,
      supplier_id: filters.supplier_id || undefined,
      size_id: filters.size_id || undefined,
      date_from: range.value?.[0] || undefined,
      date_to: range.value?.[1] || undefined,
    }
    const res = await purchaseApi.list(params)
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function onPage(p) {
  page.value = p
  load()
}
function resetFilters() {
  filters.style_code = ''
  filters.category_id = null
  filters.supplier_id = null
  filters.size_id = null
  range.value = null
  page.value = 1
  load()
}

function openEdit(row) {
  Object.assign(edit, {
    id: row.id, size_text: row.size_text, quantity: row.quantity, cost_price: row.cost_price,
    purchase_date: row.purchase_date, remark: row.remark,
  })
  dialog.value = true
}
async function saveEdit() {
  await purchaseApi.update(edit.id, {
    size: edit.size_text, quantity: edit.quantity, cost_price: edit.cost_price,
    purchase_date: edit.purchase_date, remark: edit.remark,
  })
  ElMessage.success('已更新')
  dialog.value = false
  load()
}

async function onDelete(row) {
  await ElMessageBox.confirm(`确定删除款号 ${row.style_code} / ${row.size_text} 的进货记录？`, '提示', { type: 'warning' })
  await purchaseApi.remove(row.id)
  ElMessage.success('已删除')
  load()
}

async function onExport() {
  await downloadFile('/export/purchases.xlsx', 'purchases.xlsx')
  ElMessage.success('已开始下载')
}

onMounted(async () => {
  await loadDicts()
  await load()
})
</script>
