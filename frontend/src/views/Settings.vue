<template>
  <div class="page-card">
    <el-tabs v-model="tab">
      <el-tab-pane label="字典管理" name="dict">
        <el-row :gutter="20">
          <el-col :xs="24" :md="8" v-for="grp in groups" :key="grp.kind">
            <div style="font-weight: 600; margin-bottom: 10px">{{ grp.label }}</div>
            <el-tag
              v-for="item in dicts[grp.kind]"
              :key="item.id"
              closable
              style="margin: 0 8px 8px 0"
              @close="removeDict(grp.kind, item.id)"
            >{{ item.name }}</el-tag>
            <el-input
              v-model="newName[grp.kind]"
              size="small"
              class="dict-input"
              :placeholder="'新增' + grp.label"
              @keyup.enter="addDict(grp.kind)"
            >
              <template #append><el-button @click="addDict(grp.kind)">添加</el-button></template>
            </el-input>
          </el-col>
        </el-row>
      </el-tab-pane>

      <el-tab-pane label="账号设置" name="account">
        <el-form label-width="100px" style="max-width: 420px">
          <el-form-item label="账号"><el-input v-model="auth.username" disabled /></el-form-item>
          <el-form-item label="原密码"><el-input v-model="pwd.old_password" type="password" show-password /></el-form-item>
          <el-form-item label="新密码"><el-input v-model="pwd.new_password" type="password" show-password /></el-form-item>
          <el-form-item><el-button type="primary" @click="changePwd">保存</el-button></el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="数据备份 / 导入导出" name="backup">
        <el-space wrap>
          <el-button type="primary" @click="exportFile('/export/purchases.xlsx', 'purchases.xlsx')">导出进货明细</el-button>
          <el-button @click="exportFile('/export/sales.xlsx', 'sales.xlsx')">导出销售明细</el-button>
          <el-button @click="exportFile('/export/stock.xlsx', 'stock.xlsx')">导出库存</el-button>
          <el-button type="success" plain @click="importTip">导入历史 Excel</el-button>
        </el-space>
        <div class="muted" style="margin-top: 12px">
          数据库文件位于后端 <code>backend/data/inventory.db</code>（SQLite）。建议定期将 <code>data/</code> 与 <code>static/images/</code> 一并复制到外部存储备份。
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi, dictApi, downloadFile } from '../api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const tab = ref('dict')
const groups = [
  { kind: 'category', label: '分类' },
  { kind: 'supplier', label: '厂家' },
  { kind: 'size', label: '尺码' },
]
const dicts = reactive({ category: [], supplier: [], size: [] })
const newName = reactive({ category: '', supplier: '', size: '' })
const pwd = reactive({ old_password: '', new_password: '' })

async function loadDict(kind) {
  dicts[kind] = await dictApi.list(kind)
}
async function addDict(kind) {
  const name = (newName[kind] || '').trim()
  if (!name) return
  await dictApi.create(kind, { name })
  newName[kind] = ''
  await loadDict(kind)
  ElMessage.success('已添加')
}
async function removeDict(kind, id) {
  await dictApi.remove(kind, id)
  await loadDict(kind)
  ElMessage.success('已删除')
}

async function changePwd() {
  if (!pwd.old_password || !pwd.new_password) {
    ElMessage.warning('请填写原密码与新密码')
    return
  }
  await authApi.changePassword({ ...pwd })
  pwd.old_password = ''
  pwd.new_password = ''
  ElMessage.success('密码已更新')
}

async function exportFile(path, filename) {
  await downloadFile(path, filename)
  ElMessage.success('已开始下载')
}
function importTip() {
  ElMessage.info('导入功能将在 P1 版本提供（需先下载模板）')
}

onMounted(() => {
  groups.forEach((g) => loadDict(g.kind))
})
</script>

<style scoped>
.dict-input { width: 170px; }
@media (max-width: 768px) {
  .dict-input { width: 100% !important; }
}
</style>
