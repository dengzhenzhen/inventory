<template>
  <el-dialog
    v-model="visible"
    :title="title"
    width="440px"
    append-to-body
    destroy-on-close
    class="scan-dialog"
    @opened="startCamera"
    @closed="stopCamera"
  >
    <div class="scan-body">
      <div v-show="!error" :id="readerId" class="scan-reader"></div>
      <div v-if="error" class="scan-error">{{ error }}</div>
      <div v-else class="scan-hint">将条形码或二维码放入取景框内，识别成功后自动填入款号</div>
      <div class="scan-actions">
        <el-button size="small" :loading="starting" @click="startCamera">重新开启摄像头</el-button>
        <el-button size="small" @click="pickFile">拍照 / 选择图片识别</el-button>
      </div>
      <input
        ref="fileInput"
        type="file"
        accept="image/*"
        capture="environment"
        class="scan-file"
        @change="onFile"
      />
    </div>
  </el-dialog>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '扫码录入款号' },
})
const emit = defineEmits(['update:modelValue', 'detected'])

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const fileInput = ref(null)
const starting = ref(false)
const error = ref('')
const readerId = `scan-reader-${Math.random().toString(36).slice(2)}`

let scanner = null
let startToken = 0
let handled = false

function scanConfig() {
  return {
    fps: 10,
    qrbox: (viewfinderWidth, viewfinderHeight) => ({
      width: Math.floor(Math.min(viewfinderWidth * 0.9, 320)),
      height: Math.floor(Math.min(viewfinderHeight * 0.45, 180)),
    }),
  }
}

function cameraErrorMessage(err) {
  const text = `${err?.name || ''} ${err?.message || err || ''}`.toLowerCase()
  if (text.includes('notallowederror') || text.includes('permission') || text.includes('denied')) {
    return '未获得摄像头权限，请在浏览器中允许访问摄像头后重试，或使用“拍照 / 选择图片识别”。'
  }
  if (text.includes('notfounderror') || text.includes('no camera') || text.includes('requested device not found')) {
    return '未检测到可用摄像头，请使用“拍照 / 选择图片识别”。'
  }
  if (text.includes('notreadableerror') || text.includes('could not start video source') || text.includes('in use')) {
    return '摄像头被其他程序占用，请关闭占用程序后重试。'
  }
  if (text.includes('overconstrainederror')) {
    return '摄像头不支持请求的采集参数，请尝试重新开启或使用“拍照 / 选择图片识别”。'
  }
  return `无法启动摄像头：${err?.message || err || '未知错误'}。可尝试“拍照 / 选择图片识别”。`
}

function onDetected(rawText) {
  if (handled) return
  const text = String(rawText || '').trim()
  if (!text) return
  handled = true
  emit('detected', text)
  visible.value = false
}

async function stopCamera() {
  startToken += 1
  const instance = scanner
  scanner = null
  if (!instance) return
  try {
    await instance.stop()
  } catch (e) {
    /* 已停止或尚未启动 */
  }
  try {
    instance.clear()
  } catch (e) {
    /* 忽略清理异常 */
  }
}

async function startCamera() {
  if (starting.value || scanner) return
  error.value = ''
  handled = false

  if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
    error.value = '当前页面不是安全环境（需 HTTPS 或 localhost），浏览器禁止直接调用摄像头。请使用“拍照 / 选择图片识别”。'
    return
  }

  const token = ++startToken
  starting.value = true
  try {
    const { Html5Qrcode, Html5QrcodeSupportedFormats } = await import('html5-qrcode')
    const cameras = await Html5Qrcode.getCameras()
    if (!cameras.length) throw new Error('NO_CAMERA')

    const backCamera = cameras.find((camera) => /back|rear|environment|后置/i.test(camera.label || ''))
    const cameraId = (backCamera || cameras[0]).id
    const formats = [
      Html5QrcodeSupportedFormats.QR_CODE,
      Html5QrcodeSupportedFormats.CODE_128,
      Html5QrcodeSupportedFormats.CODE_39,
      Html5QrcodeSupportedFormats.CODE_93,
      Html5QrcodeSupportedFormats.EAN_13,
      Html5QrcodeSupportedFormats.EAN_8,
      Html5QrcodeSupportedFormats.UPC_A,
      Html5QrcodeSupportedFormats.UPC_E,
      Html5QrcodeSupportedFormats.ITF,
      Html5QrcodeSupportedFormats.CODABAR,
      Html5QrcodeSupportedFormats.DATA_MATRIX,
      Html5QrcodeSupportedFormats.AZTEC,
      Html5QrcodeSupportedFormats.PDF_417,
    ]

    const instance = new Html5Qrcode(readerId, { verbose: false, formatsToSupport: formats })
    scanner = instance
    await instance.start(cameraId, scanConfig(), onDetected, () => {})
    if (token !== startToken) await stopCamera()
  } catch (err) {
    await stopCamera()
    handled = false
    error.value = err?.message === 'NO_CAMERA' ? '未检测到可用摄像头，请使用“拍照 / 选择图片识别”。' : cameraErrorMessage(err)
  } finally {
    starting.value = false
  }
}

function pickFile() {
  fileInput.value?.click()
}

async function onFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return

  error.value = ''
  await stopCamera()
  starting.value = true
  const holderId = `scan-file-${Math.random().toString(36).slice(2)}`
  const holder = document.createElement('div')
  holder.id = holderId
  holder.style.cssText = 'position:fixed;left:-10000px;top:0;width:1px;height:1px;overflow:hidden;'
  document.body.appendChild(holder)

  try {
    const { Html5Qrcode } = await import('html5-qrcode')
    const instance = new Html5Qrcode(holderId, false)
    try {
      const text = await instance.scanFile(file, true)
      onDetected(text)
    } finally {
      try {
        instance.clear()
      } catch (e) {
        /* 忽略清理异常 */
      }
    }
  } catch (err) {
    error.value = '未能识别图片中的条形码或二维码，请对准后重拍或换一张图片重试。'
  } finally {
    holder.remove()
    starting.value = false
  }
}

onBeforeUnmount(stopCamera)
</script>

<style scoped>
.scan-body { display: flex; flex-direction: column; gap: 10px; }
.scan-reader {
  width: 100%; min-height: 220px; overflow: hidden; border-radius: 10px; background: #111528;
}
.scan-reader :deep(video) { width: 100% !important; height: auto !important; border-radius: 10px; }
.scan-hint { color: #8a91a8; font-size: 13px; text-align: center; }
.scan-error { color: #f56c6c; font-size: 13px; line-height: 1.6; text-align: center; }
.scan-actions { display: flex; justify-content: center; flex-wrap: wrap; gap: 8px; }
.scan-actions .el-button + .el-button { margin-left: 0; }
.scan-file { display: none; }
</style>
