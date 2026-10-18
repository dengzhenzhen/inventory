<template>
  <div class="page-card">
    <div class="card-title">
      进货录入
      <el-switch v-model="batch" active-text="批量录入" />
    </div>

    <el-form v-if="!batch" :model="form" label-width="80px" style="max-width: 760px">
      <el-row :gutter="16">
        <el-col :xs="24" :sm="12">
          <el-form-item label="款号" required>
            <div class="style-picker">
              <el-select v-model="form.style_code" filterable allow-create default-first-option placeholder="选择或输入新款号" style="flex: 1; min-width: 0" @change="onStyleChange">
                <el-option v-for="p in products" :key="p.id" :label="p.style_code + (p.name ? ' · ' + p.name : '')" :value="p.style_code" />
              </el-select>
              <el-button class="scan-btn" title="扫描条形码或二维码" @click="scanOpen = true">
                <el-icon><Camera /></el-icon><span class="scan-label">扫码</span>
              </el-button>
            </div>
            <div class="muted" v-if="form.style_code && !products.find((p) => p.style_code === form.style_code)">该款号不存在，保存时将自动新建档案</div>
          </el-form-item>
        </el-col>
        <el-col :xs="24" :sm="12">
          <el-form-item label="分类">
            <el-select v-model="form.category" filterable allow-create placeholder="选择或输入" style="width: 100%">
              <el-option v-for="c in dicts.category" :key="c.id" :label="c.name" :value="c.name" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :xs="24" :sm="12">
          <el-form-item label="厂家">
            <el-select v-model="form.supplier" filterable allow-create placeholder="选择或输入" style="width: 100%">
              <el-option v-for="s in dicts.supplier" :key="s.id" :label="s.name" :value="s.name" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :xs="24" :sm="12">
          <el-form-item label="尺码">
            <el-select v-model="form.size" filterable allow-create placeholder="选择或输入" style="width: 100%">
              <el-option v-for="s in dicts.size" :key="s.id" :label="s.name" :value="s.name" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :xs="24" :sm="12"><el-form-item label="数量" required><el-input-number v-model="form.quantity" :min="1" style="width: 100%" /></el-form-item></el-col>
        <el-col :xs="24" :sm="12"><el-form-item label="进货价" required><el-input-number v-model="form.cost_price" :min="0" :precision="2" style="width: 100%" /></el-form-item></el-col>
        <el-col :xs="24" :sm="12"><el-form-item label="日期" required><el-date-picker v-model="form.purchase_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item></el-col>
        <el-col :xs="24" :sm="12">
          <el-form-item label="主图">
            <div class="upload-box" @click="pickImage">
              <img v-if="form.main_image" :src="imgUrl(form.main_image)" style="width: 100%; height: 100%; object-fit: cover; border-radius: 10px" />
              <template v-else><div style="font-size: 24px">+</div><div style="font-size: 12px">上传图片</div></template>
            </div>
            <input ref="fileInput" type="file" accept="image/*" style="display: none" @change="onFile" />
          </el-form-item>
        </el-col>
        <el-col :span="24"><el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item></el-col>
      </el-row>
      <el-form-item>
        <el-button type="primary" :loading="saving" @click="save">保存进货</el-button>
        <el-button @click="reset">重置</el-button>
      </el-form-item>
    </el-form>

    <div v-else>
      <el-table :data="rows" size="small">
        <el-table-column label="款号" width="150"><template #default="{ row }"><el-input v-model="row.style_code" size="small" placeholder="款号" /></template></el-table-column>
        <el-table-column label="尺码" width="100"><template #default="{ row }"><el-select v-model="row.size" size="small" filterable allow-create><el-option v-for="s in dicts.size" :key="s.id" :label="s.name" :value="s.name" /></el-select></template></el-table-column>
        <el-table-column label="数量" width="110"><template #default="{ row }"><el-input-number v-model="row.quantity" size="small" :min="1" controls-position="right" style="width: 100px" /></template></el-table-column>
        <el-table-column label="进货价" width="120"><template #default="{ row }"><el-input-number v-model="row.cost_price" size="small" :min="0" :precision="2" controls-position="right" style="width: 110px" /></template></el-table-column>
        <el-table-column label="分类" width="130"><template #default="{ row }"><el-select v-model="row.category" size="small" filterable allow-create><el-option v-for="c in dicts.category" :key="c.id" :label="c.name" :value="c.name" /></el-select></template></el-table-column>
        <el-table-column label="厂家" width="160"><template #default="{ row }"><el-select v-model="row.supplier" size="small" filterable allow-create><el-option v-for="s in dicts.supplier" :key="s.id" :label="s.name" :value="s.name" /></el-select></template></el-table-column>
        <el-table-column label="日期" width="150"><template #default="{ row }"><el-date-picker v-model="row.purchase_date" type="date" size="small" value-format="YYYY-MM-DD" style="width: 140px" /></template></el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ $index }">
            <el-button link type="primary" size="small" @click="copyRow($index)">复制</el-button>
            <el-button link type="danger" size="small" @click="rows.splice($index, 1)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 12px">
        <el-button @click="rows.push(blank())">+ 添加一行</el-button>
        <el-button type="primary" :loading="saving" style="margin-left: 8px" @click="saveBatch">批量保存（{{ rows.length }} 条）</el-button>
      </div>
    </div>

    <ScanDialog v-model="scanOpen" @detected="applyScannedCode" />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { dictApi, productApi, purchaseApi, uploadApi } from '../api'
import { imgUrl, today } from '../utils'
import ScanDialog from '../components/ScanDialog.vue'

const dicts = reactive({ category: [], supplier: [], size: [] })
const products = ref([])
const scanOpen = ref(false)
const batch = ref(false)
const saving = ref(false)
const fileInput = ref(null)

const blank = () => ({
  style_code: '', size: '', quantity: 1, cost_price: 0, purchase_date: today(),
  category: '', supplier: '', main_image: '', remark: '',
})
const form = reactive(blank())
const rows = ref([blank()])

async function loadDicts() {
  const [c, s, z] = await Promise.all([dictApi.list('category'), dictApi.list('supplier'), dictApi.list('size')])
  dicts.category = c
  dicts.supplier = s
  dicts.size = z
}
async function loadProducts() {
  products.value = (await productApi.list({ page: 1, page_size: 500 })).items
}

function onStyleChange(code) {
  const p = products.value.find((x) => x.style_code === code)
  if (p) {
    form.category = p.category_name || ''
    form.supplier = p.supplier_name || ''
    if (p.main_image) form.main_image = p.main_image
  }
}

function applyScannedCode(code) {
  form.style_code = code
  onStyleChange(code)
  ElMessage.success(`已扫入款号：${code}`)
}

function reset() {
  Object.assign(form, blank())
}
function copyRow(i) {
  rows.value.splice(i + 1, 0, { ...rows.value[i] })
}

function pickImage() {
  fileInput.value?.click()
}
async function onFile(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const res = await uploadApi.image(file)
  form.main_image = res.path
  ElMessage.success('图片已上传')
  e.target.value = ''
}

async function save() {
  if (!form.style_code) {
    ElMessage.error('请填写款号')
    return
  }
  if (!form.quantity) {
    ElMessage.error('请填写数量')
    return
  }
  saving.value = true
  try {
    await purchaseApi.create({ ...form })
    ElMessage.success('进货已保存')
    reset()
    await loadProducts()
  } catch (e) {
    /* handled */
  } finally {
    saving.value = false
  }
}

async function saveBatch() {
  const items = rows.value.filter((r) => r.style_code && r.quantity)
  if (!items.length) {
    ElMessage.error('请至少填写一行有效数据')
    return
  }
  saving.value = true
  try {
    const res = await purchaseApi.batch(items)
    ElMessage.success(`已保存 ${res.created} 条进货`)
    rows.value = [blank()]
    await loadProducts()
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

<style scoped>
.upload-box {
  width: 120px; height: 120px; border: 1px dashed #c8cede; border-radius: 10px; display: flex;
  flex-direction: column; align-items: center; justify-content: center; color: #98a0b3; cursor: pointer; background: #fafbff;
}
.upload-box:hover { border-color: var(--brand); color: var(--brand); }
.style-picker { display: flex; gap: 8px; width: 100%; }
.scan-btn { flex: none; }
@media (max-width: 480px) {
  .scan-label { display: none; }
}
</style>
