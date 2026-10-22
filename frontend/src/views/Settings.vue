<template>
  <div class="page-card">
    <el-alert v-if="session.mustChange" title="请先修改初始密码（至少 8 位），完成后重新登录。" type="warning" :closable="false" />
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
          <el-form-item label="账号"><el-input :model-value="auth.username" disabled /></el-form-item>
          <el-form-item label="原密码"><el-input v-model="pwd.old_password" type="password" show-password /></el-form-item>
          <el-form-item label="新密码"><el-input v-model="pwd.new_password" type="password" show-password /></el-form-item>
          <el-form-item><el-button type="primary" @click="changePwd">保存</el-button></el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="备份 / 恢复 / 导出" name="backup">
        <el-space wrap>
          <el-button type="primary" @click="exportFile('/backups', 'inventory-backup.zip')">下载完整备份</el-button>
          <el-button @click="backupInput.click()">上传并校验备份</el-button>
          <el-button @click="loadBackupStatus">刷新维护状态</el-button>
          <input ref="backupInput" type="file" accept=".zip" style="display:none" @change="validateBackup" />
        </el-space>
        <el-alert v-if="backupStatus.maintenance" :title="backupStatus.failure || '已进入维护模式，请关闭并重启程序完成恢复；或取消任务。'" type="warning" :closable="false" />
        <el-button v-if="backupStatus.maintenance" @click="cancelRestore">取消维护 / 恢复任务</el-button>
        <div v-if="validated" style="margin-top:16px">
          <p>备份版本 {{validated.manifest.app_version}} · 时间 {{validated.manifest.created_at}} · {{Object.keys(validated.manifest.files).length}} 个文件</p>
          <el-button type="danger" @click="restoreBackup">确认恢复并进入维护模式</el-button>
        </div>
        <p class="muted">完整备份包含数据库、商品图片和校验清单。恢复前会保存当前数据副本，重启时执行恢复；成功后所有设备须重新登录。配置密钥不包含在备份内。</p>
        <el-divider />
        <el-space wrap>
          <el-button @click="exportFile('/export/purchases.xlsx','purchases.xlsx')">全部进货 Excel</el-button>
          <el-button @click="exportFile('/export/sales.xlsx','sales.xlsx')">全部销售 Excel</el-button>
          <el-button @click="exportFile('/export/stock.xlsx','stock.xlsx')">全部库存 Excel</el-button>
        </el-space>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { authApi, dictApi, downloadFile, backupApi } from '../api'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'
import { session, clearSession } from '../session'

const auth = useAuthStore()
const tab = ref(session.mustChange ? 'account' : 'dict')
const router=useRouter()
const backupInput=ref(null),backupStatus=ref({}),validated=ref(null)
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
  clearSession();ElMessage.success('密码已更新，请重新登录');router.replace('/login')
}

async function exportFile(path, filename) {
  await downloadFile(path, filename)
  ElMessage.success('已开始下载')
}
async function loadBackupStatus(){backupStatus.value=await backupApi.status()}
async function validateBackup(event){const file=event.target.files?.[0];event.target.value='';if(!file)return;validated.value=null;validated.value=await backupApi.validate(file);ElMessage.success('备份校验通过')}
async function restoreBackup(){await ElMessageBox.confirm('恢复将替换当前数据库及图片，程序重启后执行。恢复前会保留副本。确定继续？','恢复备份',{type:'warning'});await backupApi.restore(validated.value.token);validated.value=null;await loadBackupStatus()}
async function cancelRestore(){await backupApi.cancel();await loadBackupStatus()}


onMounted(async () => {
  if(!session.mustChange){await loadBackupStatus();if(backupStatus.value.maintenance)tab.value='backup';else await Promise.all(groups.map(g=>loadDict(g.kind)))}
})
</script>

<style scoped>
.dict-input { width: 170px; }
@media (max-width: 768px) {
  .dict-input { width: 100% !important; }
}
</style>
