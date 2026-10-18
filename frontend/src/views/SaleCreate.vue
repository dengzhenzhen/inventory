<template>
  <div class="page-card" style="max-width: 760px">
    <div class="card-title">销售开单</div>
    <el-form :model="form" label-width="80px">
      <el-row :gutter="16">
        <el-col :xs="24" :sm="12">
          <el-form-item label="款号" required>
            <el-select v-model="form.style_code" filterable placeholder="搜索款号" style="width: 100%" @change="onStyleChange">
              <el-option v-for="p in products" :key="p.id" :label="p.style_code + (p.name ? ' · ' + p.name : '')" :value="p.style_code" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :xs="24" :sm="12"><el-form-item label="分类"><el-input v-model="categoryName" disabled /></el-form-item></el-col>
        <el-col :xs="24" :sm="12">
          <el-form-item label="尺码" required>
            <el-select v-model="form.size" placeholder="选择尺码" style="width: 100%" @change="refreshStock">
              <el-option v-for="s in dicts.size" :key="s.id" :label="s.name" :value="s.name" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :xs="24" :sm="12">
          <el-form-item label="当前库存">
            <el-tag :type="currentStock < 0 ? 'danger' : currentStock < severe ? 'warning' : 'success'" size="large">{{ currentStock }} 件</el-tag>
            <span class="muted" style="margin-left: 8px">零售价 ￥{{ fmtMoney(form.retail_price) }}</span>
          </el-form-item>
        </el-col>
        <el-col :xs="24" :sm="12"><el-form-item label="数量" required><el-input-number v-model="form.quantity" :min="1" style="width: 100%" /></el-form-item></el-col>
        <el-col :xs="24" :sm="12"><el-form-item label="售价" required><el-input-number v-model="form.unit_price" :min="0" :precision="2" style="width: 100%" /></el-form-item></el-col>
        <el-col :xs="24" :sm="12"><el-form-item label="日期" required><el-date-picker v-model="form.sale_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item></el-col>
        <el-col :span="24"><el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item></el-col>
      </el-row>

      <div v-if="oversell" class="warn-banner">
        ⚠️ 库存不足：当前「{{ form.style_code }} / {{ form.size }}」库存 {{ currentStock }} 件，本次销售 {{ form.quantity }} 件，将产生
        <b>负库存 {{ currentStock - form.quantity }}</b>。<span class="muted">（允许负库存但强提示，仍可继续保存）</span>
      </div>

      <el-form-item style="margin-top: 16px">
        <el-button type="primary" :loading="saving" @click="save">确认出库</el-button>
        <el-button @click="reset">重置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { dictApi, productApi, saleApi, stockApi } from '../api'
import { fmtMoney, today } from '../utils'

const dicts = reactive({ size: [] })
const products = ref([])
const categoryName = ref('')
const currentStock = ref(0)
const severe = 3
const saving = ref(false)

const blank = () => ({ style_code: '', size: '', quantity: 1, unit_price: 0, retail_price: 0, sale_date: today(), remark: '' })
const form = reactive(blank())

const oversell = computed(() => form.style_code && form.size && form.quantity > currentStock.value)

async function loadDicts() {
  dicts.size = await dictApi.list('size')
}
async function loadProducts() {
  products.value = (await productApi.list({ page: 1, page_size: 500 })).items
}

function onStyleChange(code) {
  const p = products.value.find((x) => x.style_code === code)
  if (p) {
    categoryName.value = p.category_name || ''
    form.retail_price = p.retail_price || 0
    form.unit_price = p.retail_price || 0
  }
  refreshStock()
}
async function refreshStock() {
  if (!form.style_code || !form.size) {
    currentStock.value = 0
    return
  }
  currentStock.value = (await stockApi.current(form.style_code, form.size)).stock
}
function reset() {
  Object.assign(form, blank())
  categoryName.value = ''
  currentStock.value = 0
}

async function save() {
  if (!form.style_code || !form.size) {
    ElMessage.error('请选择款号与尺码')
    return
  }
  saving.value = true
  try {
    const res = await saleApi.create({ ...form })
    if (res.warning) ElMessageBox.alert(res.warning, '库存不足提示', { type: 'warning' })
    else ElMessage.success('出库成功')
    reset()
  } catch (e) {
    /* handled */
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await loadDicts()
  await loadProducts()
})
</script>
