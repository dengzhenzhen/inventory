<template>
  <div class="page-card">
    <div class="card-title">
      商品档案
      <el-button type="primary" @click="openDialog()">+ 新建款式</el-button>
    </div>

    <div class="filter-bar"><el-input v-model="keyword" placeholder="款号 / 品名" clearable /><el-button @click="page=1;load()">查询</el-button></div>
    <el-table :data="rows" border stripe v-loading="loading">
      <el-table-column label="主图" width="80">
        <template #default="{ row }">
          <div class="img-box" style="width: 44px; height: 44px; font-size: 11px">
            <img v-if="row.main_image" :src="imgUrl(row.main_image)" alt="" />
            <span v-else>{{ row.style_code.slice(-3) }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="style_code" label="款号" width="130" />
      <el-table-column prop="name" label="品名" />
      <el-table-column prop="category_name" label="分类" width="100" />
      <el-table-column prop="supplier_name" label="厂家" width="170" />
      <el-table-column label="零售价" width="100"><template #default="{ row }">￥{{ fmtMoney(row.retail_price) }}</template></el-table-column>
      <el-table-column label="操作" width="130" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
          <el-button link type="danger" size="small" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="prev,pager,next,total" @current-change="load" />
  </div>

  <el-dialog v-model="dialog" :title="edit.id ? '编辑款式' : '新建款式'" width="560px">
    <el-form :model="edit" label-width="80px">
      <el-form-item label="款号" required><el-input v-model="edit.style_code" placeholder="唯一款号" /></el-form-item>
      <el-form-item label="品名"><el-input v-model="edit.name" /></el-form-item>
      <el-form-item label="分类">
        <el-select v-model="edit.category_name" filterable allow-create style="width: 100%">
          <el-option v-for="c in dicts.category" :key="c.id" :label="c.name" :value="c.name" />
        </el-select>
      </el-form-item>
      <el-form-item label="厂家">
        <el-select v-model="edit.supplier_name" filterable allow-create style="width: 100%">
          <el-option v-for="s in dicts.supplier" :key="s.id" :label="s.name" :value="s.name" />
        </el-select>
      </el-form-item>
      <el-form-item label="零售价"><el-input-number v-model="edit.retail_price" :min="0" :precision="2" style="width: 100%" /></el-form-item>
      <el-form-item label="主图">
        <div class="upload-box" @click="pickImage">
          <img v-if="edit.main_image" :src="imgUrl(edit.main_image)" style="width: 100%; height: 100%; object-fit: cover; border-radius: 10px" />
          <template v-else><div style="font-size: 24px">+</div><div style="font-size: 12px">上传图片</div></template>
        </div>
        <input ref="fileInput" type="file" accept="image/*" style="display: none" @change="onFile" />
      </el-form-item>
      <el-form-item label="备注"><el-input v-model="edit.remark" type="textarea" :rows="2" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialog = false">取消</el-button>
      <el-button type="primary" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { dictApi, productApi, uploadApi } from '../api'
import { fmtMoney, imgUrl } from '../utils'

const dicts = reactive({ category: [], supplier: [] })
const rows = ref([])
const loading = ref(false)
const page=ref(1),total=ref(0),keyword=ref('')
const dialog = ref(false)
const fileInput = ref(null)

const blank = () => ({ id: null, style_code: '', name: '', category_name: '', supplier_name: '', retail_price: 0, main_image: '', remark: '' })
const edit = reactive(blank())

async function loadDicts() {
  const [c, s] = await Promise.all([dictApi.list('category'), dictApi.list('supplier')])
  dicts.category = c
  dicts.supplier = s
}
async function load() {
  loading.value = true
  try {
    const result=await productApi.list({page:page.value,page_size:20,keyword:keyword.value})
    rows.value=result.items;total.value=result.total
  } finally {
    loading.value = false
  }
}

function openDialog(row) {
  Object.assign(edit, row ? { ...row } : blank())
  dialog.value = true
}

function pickImage() {
  fileInput.value?.click()
}
async function onFile(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const res = await uploadApi.image(file)
  edit.main_image = res.path
  ElMessage.success('图片已上传')
  e.target.value = ''
}

async function save() {
  if (!edit.style_code) {
    ElMessage.error('请填写款号')
    return
  }
  if (edit.id) {
    await productApi.update(edit.id, {
      style_code: edit.style_code, name: edit.name, category_name: edit.category_name,
      supplier_name: edit.supplier_name, retail_price: edit.retail_price, main_image: edit.main_image, remark: edit.remark,
    })
  } else {
    await productApi.create({
      style_code: edit.style_code, name: edit.name, category_name: edit.category_name,
      supplier_name: edit.supplier_name, retail_price: edit.retail_price, main_image: edit.main_image, remark: edit.remark,
    })
  }
  ElMessage.success('已保存')
  dialog.value = false
  load()
}

async function onDelete(row) {
  await ElMessageBox.confirm(`确定删除款号 ${row.style_code}？`, '提示', { type: 'warning' })
  await productApi.remove(row.id)
  ElMessage.success('已删除')
  load()
}

onMounted(async () => {
  await loadDicts()
  await load()
})
</script>

<style scoped>
.upload-box {
  width: 120px; height: 120px; border: 1px dashed #c8cede; border-radius: 10px; display: flex;
  flex-direction: column; align-items: center; justify-content: center; color: #98a0b3; cursor: pointer; background: #fafbff;
}
.upload-box:hover { border-color: var(--brand); color: var(--brand); }
</style>
