<template>
  <div class="page-card">
    <div class="card-title">单据中心 <el-button type="primary" @click="newOrder()">新建单据</el-button></div>
    <div class="filter-bar">
      <el-select v-model="filters.kind" clearable placeholder="全部类型"><el-option v-for="(name,key) in kinds" :key="key" :label="name" :value="key" /></el-select>
      <el-select v-model="filters.status" clearable placeholder="全部状态"><el-option label="有效" value="posted" /><el-option label="已作废" value="void" /></el-select>
      <el-select v-model="filters.category_id" clearable placeholder="分类"><el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" /></el-select>
      <el-select v-model="filters.supplier_id" clearable placeholder="厂家"><el-option v-for="s in suppliers" :key="s.id" :label="s.name" :value="s.id" /></el-select>
      <el-select v-model="filters.size_id" clearable placeholder="尺码"><el-option v-for="s in sizes" :key="s.id" :label="s.name" :value="s.id" /></el-select>
      <el-date-picker v-model="range" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始" end-placeholder="结束" />
      <el-button @click="page=1;load()">查询</el-button>
      <el-input v-model="styleFilter" placeholder="款号筛选" style="width:160px" /><el-button @click="exportCurrent">导出匹配明细</el-button>
      <el-button @click="showCosts">成本重算</el-button><el-button @click="showAudit">操作日志</el-button>
    </div>
    <el-table :data="items" v-loading="loading" border>
      <el-table-column prop="id" label="单据号" width="85" />
      <el-table-column label="类型" width="100"><template #default="{row}">{{ kinds[row.kind] }}</template></el-table-column>
      <el-table-column prop="date" label="业务日期" width="110" />
      <el-table-column label="商品"><template #default="{row}">{{ row.lines.map(x=>`${x.style_code}/${x.size_text} ×${x.quantity}`).join('；') }}</template></el-table-column>
      <el-table-column label="状态" width="85"><template #default="{row}">{{ row.status==='void'?'已作废':'有效' }}</template></el-table-column>
      <el-table-column label="操作" width="210"><template #default="{row}">
        <el-button link @click="detail=row">详情</el-button><el-button link @click="copyOrder(row)">复制重开</el-button>
        <el-button v-if="row.status==='posted'" link type="danger" @click="cancel(row)">作废</el-button>
      </template></el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="prev,pager,next,total" @current-change="load" />
  </div>
  <el-dialog v-model="editing" title="新建单据" width="min(1100px,96vw)" :close-on-click-modal="false">
    <el-form label-width="80px">
      <el-form-item label="类型"><el-select v-model="form.kind" @change="resetLines"><el-option v-for="(name,key) in kinds" :key="key" :label="name" :value="key" /></el-select></el-form-item>
      <el-form-item label="日期"><el-date-picker v-model="form.date" value-format="YYYY-MM-DD" /></el-form-item>
      <el-form-item label="原因备注"><el-input v-model="form.remark" maxlength="2000" placeholder="退货、作废、盘点和调整需说明原因" /></el-form-item>
    </el-form>
    <el-alert v-if="isReturn" title="请先打开有效采购或销售原单详情，点击“退货”建立关联；已关联明细不能更换商品尺码。" type="info" :closable="false" />
    <div v-for="(line,index) in form.lines" :key="line.key" class="line-card">
      <div class="line-grid">
        <ProductPicker v-model="line.style_code" :allow-create="form.kind==='purchase'" :disabled="isReturn" @resolved="p=>resolved(line,p)" />
        <el-button :disabled="isReturn" @click="scanLine=line;scanOpen=true">扫码</el-button>
        <el-select v-model="line.size" filterable :allow-create="form.kind==='purchase'" :disabled="isReturn" placeholder="尺码" @change="refresh(line)"><el-option v-for="s in sizes" :key="s.id" :label="s.name" :value="s.name" /></el-select>
        <el-input-number v-if="form.kind==='count'" v-model="line.counted" :min="0" placeholder="实盘数量" />
        <el-input-number v-else v-model="line.quantity" :min="1" :max="line.return_max || 1000000" />
        <el-input-number v-model="line.price" :min="0" :precision="2" :disabled="isReturn" />
        <el-button type="danger" plain @click="form.lines.splice(index,1)">移除</el-button>
      </div>
      <div class="muted">{{ form.kind==='count'?'数量为实盘数量':'数量为本单件数' }} · 单价{{ ['count','adjustment'].includes(form.kind)?'为调增成本（无历史成本时必填）':'' }} · 当前库存 {{ line.stock }} 件 <span v-if="line.costWarning"> · {{line.costWarning}}</span></div>
      <el-alert v-if="form.kind==='sale' && line.quantity>line.stock" :title="`库存不足：当前 ${line.stock} 件，本次销售 ${line.quantity} 件，允许继续但将产生负库存。`" type="warning" :closable="false" />
      <div v-if="form.kind==='purchase'"><img v-if="line.main_image" :src="imgUrl(line.main_image)" style="width:48px;height:48px;object-fit:cover" /><label class="muted">上传主图 <input type="file" accept="image/*" @change="uploadImage($event,line)" /></label></div>
      <div v-if="form.kind==='purchase'" class="line-grid"><el-input v-model="line.category" placeholder="分类（可自动建档）" /><el-input v-model="line.supplier" placeholder="厂家（可自动建档）" /></div>
      <el-radio-group v-if="form.kind==='adjustment'" v-model="line.adjustment_sign"><el-radio :value="1">调增</el-radio><el-radio :value="-1">调减</el-radio></el-radio-group>
      <div v-if="isReturn" class="muted">原单明细 #{{line.original_line_id}}，原数量 {{line.return_max}}；服务端校验剩余可退数量。</div>
    </div>
    <el-button v-if="!isReturn" @click="form.lines.push(blank())">添加商品</el-button>
    <template #footer><el-button @click="editing=false">取消</el-button><el-button type="primary" :loading="saving" @click="save">整单确认</el-button></template>
  </el-dialog>
  <el-dialog :model-value="!!detail" title="单据详情" width="min(900px,96vw)" @close="detail=null">
    <template v-if="detail"><p>#{{detail.id}} {{ kinds[detail.kind] }} · {{detail.date}} · {{detail.status}} · {{detail.remark}}</p>
      <el-table :data="detail.lines"><el-table-column prop="id" label="明细号" /><el-table-column prop="style_code" label="当前款号" /><el-table-column prop="style_snapshot" label="开单款号" /><el-table-column prop="size_text" label="尺码" /><el-table-column prop="quantity" label="数量" /><el-table-column prop="unit_price" label="单价" /><el-table-column label="成本"><template #default="{row}">{{row.cost===null?'待核算':fmtMoney(row.cost)}} / {{row.cost_dirty?'待重算':row.cost_status}}</template></el-table-column></el-table>
      <el-button v-if="detail.status==='posted' && ['purchase','sale'].includes(detail.kind)" @click="returnOrder(detail)">关联原单退货</el-button>
    </template>
  </el-dialog>
  <el-dialog v-model="costOpen" title="成本重算预览" width="min(900px,96vw)"><p>确认后按历史业务日期重放有效流水，并更新以下成本快照。单位为百万分之一元。</p><el-table :data="preview?.changes || []"><el-table-column prop="document_id" label="单据号" /><el-table-column prop="line_id" label="明细号" /><el-table-column prop="before" label="原单位成本" /><el-table-column prop="after" label="新单位成本" /><el-table-column prop="status" label="状态" /></el-table><template #footer><el-button type="primary" :loading="saving" @click="recompute">确认重算</el-button></template></el-dialog>
  <el-dialog v-model="auditOpen" title="操作日志" width="min(1000px,96vw)"><el-table :data="audits"><el-table-column prop="actor" label="操作人" width="90" /><el-table-column prop="action" label="操作" width="150" /><el-table-column prop="document_id" label="单据号" width="80" /><el-table-column prop="detail" label="内容" /><el-table-column prop="created_at" label="时间" width="180" /></el-table><el-pagination v-model:current-page="auditPage" :total="auditTotal" :page-size="20" @current-change="showAudit" /></el-dialog>
  <ScanDialog v-model="scanOpen" @detected="code=>{if(scanLine)scanLine.style_code=code}" />
</template>
<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { documentApi, dictApi, stockApi, downloadFile, uploadApi } from '../api'
import { today, fmtMoney, imgUrl } from '../utils'
import ProductPicker from '../components/ProductPicker.vue'
import ScanDialog from '../components/ScanDialog.vue'
const props=defineProps({initialKind:{type:String,default:''},openOnMount:Boolean})
const kinds={purchase:'进货',sale:'销售',purchase_return:'采购退货',sale_return:'销售退货',count:'盘点',adjustment:'库存调整'}
const items=ref([]),total=ref(0),page=ref(1),loading=ref(false),sizes=ref([]),range=ref(null)
const styleFilter=ref('')
const categories=ref([]),suppliers=ref([])
const filters=reactive({kind:props.initialKind,status:'',category_id:null,supplier_id:null,size_id:null})
const editing=ref(false),saving=ref(false),detail=ref(null),scanOpen=ref(false),scanLine=ref(null)
const costOpen=ref(false),preview=ref(null),auditOpen=ref(false),audits=ref([]),auditTotal=ref(0),auditPage=ref(1)
const blank=()=>({key:Math.random().toString(36),style_code:'',size:'',quantity:1,price:0,stock:0,stock_version:null,counted:0,adjustment_sign:1,category:'',supplier:'',main_image:''})
const form=reactive({kind:props.initialKind||'sale',date:today(),remark:'',lines:[blank()]})
const isReturn=computed(()=>['sale_return','purchase_return'].includes(form.kind))
let requestKey='',requestBody=''
function newOrder(){form.kind=props.initialKind||'sale';form.date=today();form.remark='';resetLines();editing.value=true;requestKey='';requestBody=''}
function resetLines(){form.lines=[blank()]}
async function load(){loading.value=true;try{const d=await documentApi.list({...filters,kind:filters.kind||undefined,status:filters.status||undefined,date_from:range.value?.[0],date_to:range.value?.[1],style_code:styleFilter.value||undefined,page:page.value});items.value=d.items;total.value=d.total}finally{loading.value=false}}
function resolved(line,p){if(!isReturn.value) {line.price=form.kind==='sale'&&!line.preservePrice?(p?.retail_price||0):line.price;line.category=p?.category_name||'';line.supplier=p?.supplier_name||'';line.main_image=p?.main_image||''}refresh(line)}
async function uploadImage(event,line){const file=event.target.files?.[0];event.target.value='';if(!file)return;line.main_image=(await uploadApi.image(file)).path}
async function refresh(line){line.stock=0;line.stock_version=null;if(!line.style_code||!line.size)return;const code=line.style_code,size=line.size;const s=await stockApi.current(code,size);if(code===line.style_code&&size===line.size){line.stock=s.stock;line.stock_version=s.stock_version}}
function copyOrder(doc){form.kind=doc.kind;form.date=today();form.remark=doc.remark||'';form.lines=doc.lines.map(x=>({...blank(),style_code:x.style_code,size:x.size_text,quantity:x.quantity,price:x.unit_price,preservePrice:true,original_line_id:x.original_line_id}));editing.value=true;requestKey='';requestBody='';form.lines.forEach(refresh)}
function returnOrder(doc){copyOrder(doc);form.kind=doc.kind==='sale'?'sale_return':'purchase_return';form.remark='关联原单退货';form.lines=doc.lines.map(x=>({...blank(),style_code:x.style_code,size:x.size_text,quantity:x.quantity,price:x.unit_price,original_line_id:x.id,return_max:x.quantity}));detail.value=null}
async function save(){
 if(!form.date||!form.lines.length||form.lines.some(x=>!x.style_code||(!x.size&&form.kind!=='purchase'))){ElMessage.warning('请填写日期、商品和尺码');return}
 if((isReturn.value||['count','adjustment'].includes(form.kind))&&!form.remark.trim()){ElMessage.warning('请填写原因');return}
 const data={kind:form.kind,date:form.date,remark:form.remark,lines:form.lines.map(x=>({style_code:x.style_code,size:x.size||'未指定',quantity:x.quantity,price:x.price,category:x.category||null,supplier:x.supplier||null,main_image:x.main_image||null,original_line_id:x.original_line_id||null,stock_version:x.stock_version,counted:x.counted,adjustment_sign:x.adjustment_sign}))}
 const body=JSON.stringify(data);if(body!==requestBody){requestKey=`order-${Date.now()}-${Math.random().toString(36).slice(2)}`;requestBody=body}
 saving.value=true;try{const d=await documentApi.create(data,requestKey);editing.value=false;ElMessage.success(`单据 #${d.id} 已保存`);await load()}finally{saving.value=false}
}
async function cancel(doc){const {value}=await ElMessageBox.prompt('请输入作废原因；有关联退货时需先作废退货单','作废单据',{inputValidator:v=>!!v?.trim()||'必须填写原因'});await documentApi.void(doc.id,value);ElMessage.success('已作废');await load()}
async function exportCurrent(){await downloadFile('/export/documents.xlsx','documents.xlsx',{...filters,kind:filters.kind||undefined,status:filters.status||'all',date_from:range.value?.[0],date_to:range.value?.[1],style_code:styleFilter.value||undefined})}
async function showCosts(){preview.value=await documentApi.preview();costOpen.value=true}
async function recompute(){saving.value=true;try{await documentApi.recompute(preview.value.fingerprint);costOpen.value=false;ElMessage.success('成本已重算');await load()}finally{saving.value=false}}
async function showAudit(){const d=await documentApi.audit({page:auditPage.value});audits.value=d.items;auditTotal.value=d.total;auditOpen.value=true}
onMounted(async()=>{[sizes.value,categories.value,suppliers.value]=await Promise.all(['size','category','supplier'].map(k=>dictApi.list(k)));await load();if(props.openOnMount)newOrder()})
</script>
<style scoped>
.line-card{border:1px solid #e4e7ed;border-radius:8px;padding:12px;margin:12px 0}.line-grid{display:grid;grid-template-columns:minmax(150px,2fr) auto minmax(100px,1fr) 150px 150px auto;gap:8px;margin-bottom:8px}.el-pagination{margin-top:14px}@media(max-width:800px){.line-grid{grid-template-columns:1fr 1fr}}
</style>
