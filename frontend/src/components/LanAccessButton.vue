<template>
  <button class="lan-fab" type="button" aria-label="手机扫码访问" title="手机扫码访问" @click="visible = true">
    <el-icon :size="22"><Iphone /></el-icon>
  </button>

  <el-dialog
    v-model="visible"
    title="手机扫码访问"
    width="420px"
    append-to-body
    class="lan-dialog"
    @opened="load"
  >
    <div v-loading="loading" class="lan-body">
      <p class="lan-tip">请确保手机与电脑连接同一 WiFi，然后用手机相机或微信扫描下方二维码：</p>
      <div class="lan-qr">
        <img v-if="qrDataUrl" :src="qrDataUrl" alt="手机访问二维码" />
        <el-empty v-else-if="!loading" :image-size="72" description="暂无二维码" />
      </div>
      <div v-if="url" class="lan-url">
        <span class="lan-url-text">{{ url }}</span>
        <el-button link type="primary" @click="copyUrl">
          <el-icon><CopyDocument /></el-icon>复制
        </el-button>
      </div>
      <el-alert v-if="warning" :title="warning" type="warning" :closable="false" show-icon />
      <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
      <div class="muted lan-hint">扫码后手机浏览器将打开本系统，操作数据与电脑端实时同步。</div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { systemApi } from '../api'

const visible = ref(false)
const loading = ref(false)
const qrDataUrl = ref('')
const url = ref('')
const error = ref('')
const warning = ref('')

async function load() {
  loading.value = true
  error.value = ''
  warning.value = ''
  qrDataUrl.value = ''
  url.value = ''
  try {
    const currentPort = window.location.port ? Number(window.location.port) : undefined
    const res = await systemApi.lanUrl(currentPort ? { port: currentPort } : undefined)
    url.value = res?.url || ''
    if (!url.value) {
      error.value = '未能获取局域网 IP，请确认电脑已连接 WiFi 或网线后重试。'
      return
    }

    if (res?.reachable === false) {
      warning.value = '当前服务可能只监听了本机地址，手机将无法访问。'
    }

    const QRCode = (await import('qrcode')).default
    qrDataUrl.value = await QRCode.toDataURL(url.value, {
      width: Math.round(240 * Math.min(window.devicePixelRatio || 1, 3)),
      margin: 2,
      errorCorrectionLevel: 'M',
      color: { dark: '#1f2544', light: '#ffffff' },
    })
  } catch (e) {
    error.value = `获取局域网地址失败：${e?.message || '请稍后重试'}`
  } finally {
    loading.value = false
  }
}

async function copyUrl() {
  if (!url.value) return
  try {
    await navigator.clipboard.writeText(url.value)
    ElMessage.success('地址已复制')
  } catch (e) {
    const textarea = document.createElement('textarea')
    textarea.value = url.value
    textarea.style.cssText = 'position:fixed;left:-10000px;top:0;'
    document.body.appendChild(textarea)
    textarea.select()
    try {
      document.execCommand('copy')
      ElMessage.success('地址已复制')
    } catch (err) {
      ElMessage.error('复制失败，请手动选择地址复制')
    } finally {
      textarea.remove()
    }
  }
}
</script>

<style scoped>
.lan-fab {
  position: fixed; right: 20px; bottom: 20px; z-index: 1800;
  width: 52px; height: 52px; border: none; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: #fff; cursor: pointer;
  background: linear-gradient(135deg, var(--brand), #b06ab3);
  box-shadow: 0 8px 24px rgba(91, 110, 245, 0.4);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.lan-fab:hover { transform: translateY(-2px); box-shadow: 0 12px 28px rgba(91, 110, 245, 0.5); }
.lan-fab:active { transform: translateY(0); }
.lan-body { display: flex; flex-direction: column; gap: 12px; }
.lan-tip { margin: 0; color: #5a6178; font-size: 14px; line-height: 1.6; }
.lan-qr {
  display: flex; align-items: center; justify-content: center;
  min-height: 240px; padding: 8px; background: #fafbff; border-radius: 12px;
}
.lan-qr img { width: 240px; height: 240px; max-width: 100%; border-radius: 8px; }
.lan-url {
  display: flex; align-items: center; gap: 8px; padding: 8px 10px;
  background: #f4f6ff; border-radius: 8px; font-size: 13px;
}
.lan-url-text { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #3f4fd6; }
.lan-hint { font-size: 12px; }
@media (max-width: 480px) {
  .lan-fab {
    right: 14px; bottom: calc(14px + env(safe-area-inset-bottom));
    width: 48px; height: 48px;
  }
  .lan-qr { min-height: 200px; }
  .lan-qr img { width: 200px; height: 200px; }
}
</style>
