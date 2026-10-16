# 服装店进销存管理系统 — 产品需求分析（PRD）

| 项目 | 内容 |
|---|---|
| 文档版本 | v0.3（全部决策已确认，待开发） |
| 日期 | 2026-10-17 |
| 产品名称 | 服装店进销存管理系统（进货 + 销售 + 库存） |
| 技术栈 | 后端 Python · 前端 Vue · 数据库 SQLite |
| 目标用户 | 服装店店主（主）、店员（可选） |
| 状态 | 🟢 需求已确认，**未开始编码** |

> **v0.2 变更说明**：根据店主确认（第 11 节），本期同时包含**进货**与**销售出库**，系统定位由"进货管理"升级为完整的**进销存**；新增销售表、售价字段，库存改为「进货 − 销售」净库存。
>
> **v0.3 变更说明**：Q10–Q13 采用默认值并固化——库存不足**允许负库存但强提示**；本期不做退货；分类**单级**；每日销售趋势列为 P1。

---

## 1. 项目背景与目标

### 1.1 背景
店主经营一家实体服装店，目前进货与销售信息依赖纸质账本或 Excel 记录，存在以下痛点：

- 记录容易丢失、字迹/格式不统一
- 想查"某个款号还有没有某个尺码"时无法快速检索
- 无法自动统计进货/销售数量与金额
- 商品图片无处结构化存放，靠手机相册翻找

### 1.2 产品目标
用一套**轻量、易用、可自托管**的系统，覆盖「进货 → 库存 → 销售」闭环：

1. 完整保存每条**进货**信息：款号、厂家、日期、进货价、数量、分类、尺码、主图、备注
2. 登记**销售出库**（款号、尺码、数量、售价、日期、备注），自动扣减库存
3. 自动汇总**实时净库存**（进货 − 销售，按款号×尺码）与**进销金额/利润统计**
4. 支持快速录入（批量进货、快速开单）与多条件查询
5. 电脑、手机浏览器均可使用（同一局域网访问）

### 1.3 非目标（本期明确不做）
- ❌ 在线电商 / 平台对接
- ❌ **收银/支付/会员/发票**（销售出库只登记"卖了什么、多少钱"，不涉及收款、支付通道）
- ❌ 多门店、多仓库调拨
- ❌ 复杂角色权限 / 审批流
- ❌ 库存批次/串号追溯

> 说明：明确非目标是防止需求从"进销存"膨胀为完整"商业 ERP"，这是此类项目最常见的失控点。

---

## 2. 目标用户与使用场景

| 角色 | 描述 | 核心诉求 |
|---|---|---|
| 店主 | 主要使用者，负责进货、定价与决策 | 快速录入、随时查库存、看进销统计 |
| 店员（可选） | 协助录入/开单/查询 | 简单操作，不涉及敏感配置 |

**典型场景**

- S1 **当天进货录入**：进了一批货，按款号逐条录入款号 / 尺码 / 数量 / 进货价，上传主图。
- S2 **现场销售开单**：卖出一件，选款号 / 尺码 / 数量 / 售价，系统自动扣减库存。
- S3 **现场查询**：顾客询问"XX 款有没有 L 码"，店员快速搜索款号查看**净库存**与图片。
- S4 **进销统计**：店主查看某时间段进货总额、销售总额、毛利、各分类占比、各厂家采购量。

---

## 3. 核心业务流程

```
                          ┌─────────────────────────────┐
 进货到店 ─► 录入进货 ───►│  库存 = Σ进货数量 − Σ销售数量 │◄─── 销售开单 ◄─ 卖出
 (款号/尺码/数量/进货价)   │      （按 款号 × 尺码）      │    (款号/尺码/数量/售价)
                          └─────────────────────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     ▼                             ▼
              多条件查询/展示                 进销统计报表
                                          (金额/数量/毛利/趋势)
```

---

## 4. 术语与字段定义

### 4.1 业务术语

| 术语 | 含义 |
|---|---|
| 款号 | 商品的**款式编码**，是同一款式在全店的唯一标识 |
| 尺码 | 同一款式的规格，如 S / M / L / XL / 均码 |
| 分类 | 商品类别，如 上衣 / 裤装 / 裙装 / 外套 / 配饰 |
| 厂家 | 供货商 / 生产厂家 |
| 进货价 | 单件采购成本 |
| 零售价 | 商品**标价**（吊牌价，选填，挂在款式档案上） |
| 售价 | 单件**实际成交价**（销售时填写） |
| 进货记录 | 一行 = 某款号某尺码在某日期的一次进货 |
| 销售记录 | 一行 = 某款号某尺码在某日期的一次销售 |
| 净库存 | 进货数量合计 − 销售数量合计 |

### 4.2 字段规格

**进货记录**

| 字段 | 名称 | 类型 | 必填 | 说明 / 校验 |
|---|---|---|---|---|
| 款号 | style_code | string | ✅ | 全局唯一；建议字母数字，去空格 |
| 厂家 | supplier | 关联/文本 | ⬜ | 字典可选可新增 |
| 日期 | purchase_date | date | ✅ | 默认今天；YYYY-MM-DD |
| 进货价 | cost_price | decimal | ✅ | 单价，≥ 0，2 位小数 |
| 数量 | quantity | integer | ✅ | ≥ 1 |
| 分类 | category | 关联/文本 | ⬜ | 字典可选可新增 |
| 尺码 | size | 关联/文本 | ⬜ | 字典可选可新增 |
| 主图 | main_image | 文件/路径 | ⬜ | 挂在款式档案上；jpg/png/webp，≤ 5MB |
| 备注 | remark | text | ⬜ | ≤ 500 字 |

**销售记录**

| 字段 | 名称 | 类型 | 必填 | 说明 / 校验 |
|---|---|---|---|---|
| 款号 | style_code | string | ✅ | 必须已建档 |
| 尺码 | size | 关联 | ✅ | 字典 |
| 数量 | quantity | integer | ✅ | ≥ 1；建议提示不得超过当前净库存 |
| 售价 | unit_price | decimal | ✅ | 单件实际成交价，≥ 0，2 位小数 |
| 日期 | sale_date | date | ✅ | 默认今天 |
| 备注 | remark | text | ⬜ | ≤ 500 字 |

**款式档案（商品）**

| 字段 | 名称 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| 款号 | style_code | string | ✅ | 唯一 |
| 品名 | name | string | ⬜ | 可选 |
| 分类 | category | 关联 | ⬜ | 字典 |
| 厂家 | supplier | 关联 | ⬜ | 字典 |
| 零售价 | retail_price | decimal | ⬜ | 标价，用于开单时自动带出建议售价 |
| 主图 | main_image | 路径 | ⬜ | 1 张（多图见 P2） |
| 备注 | remark | text | ⬜ | |

---

## 5. 数据模型设计（核心决策）

### 5.1 关键问题：款号 vs 尺码 vs 主图 的关系

一个**款号**对应**多个尺码**，且同一款式**共用一张主图**。已确认采用**方案 B**：

| 方案 | 说明 | 结论 |
|---|---|---|
| A. 扁平单表 | 每行 = 款号+尺码+记录，主图/分类/厂家在每行重复 | 冗余、改主图要改多行，弃 |
| **B. 商品档案 + 进货/销售明细** ✅ | 款号建档（存主图/分类/厂家/零售价），进货与销售记录各存明细 | **已确认采用** |
| C. 完整 SPU/SKU/单据三层 | 商品/规格/单据+明细 | 对单店主过重，弃 |

> 录入时支持"输入新款号**自动建档**"，让店主无感，兼顾简洁与规范。

### 5.2 表结构（SQLite 建议稿）

```sql
PRAGMA journal_mode = WAL;          -- 提升并发读写

-- 分类字典
CREATE TABLE category (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  name       TEXT NOT NULL UNIQUE,
  sort_order INTEGER DEFAULT 0
);

-- 厂家字典
CREATE TABLE supplier (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  name    TEXT NOT NULL UNIQUE,
  contact TEXT,
  phone   TEXT,
  remark  TEXT
);

-- 尺码字典
CREATE TABLE size (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  name       TEXT NOT NULL UNIQUE,      -- S/M/L/XL/均码
  sort_order INTEGER DEFAULT 0
);

-- 商品档案：以款号为核心，款号唯一
CREATE TABLE product (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  style_code   TEXT NOT NULL UNIQUE,                    -- 款号
  name         TEXT,                                    -- 品名（可选）
  category_id  INTEGER REFERENCES category(id),
  supplier_id  INTEGER REFERENCES supplier(id),
  retail_price REAL,                                    -- 零售价/标价（选填）
  main_image   TEXT,                                    -- 主图相对路径，如 images/ab12.jpg
  remark       TEXT,
  created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at   TEXT
);

-- 进货记录：一行 = 某款某码的一次进货
CREATE TABLE purchase (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id    INTEGER NOT NULL REFERENCES product(id),
  style_code    TEXT NOT NULL,                          -- 冗余款号，便于直接查询/导出
  size_id       INTEGER REFERENCES size(id),
  size_text     TEXT,                                   -- 冗余尺码文本
  quantity      INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
  cost_price    REAL    NOT NULL DEFAULT 0 CHECK (cost_price >= 0),  -- 单件进货价
  purchase_date TEXT    NOT NULL,                       -- YYYY-MM-DD
  supplier_id   INTEGER REFERENCES supplier(id),        -- 该次进货厂家（可覆盖档案默认值）
  remark        TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 销售记录：一行 = 某款某码的一次销售/出库
CREATE TABLE sale (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id  INTEGER NOT NULL REFERENCES product(id),
  style_code  TEXT NOT NULL,                            -- 冗余款号
  size_id     INTEGER REFERENCES size(id),
  size_text   TEXT,
  quantity    INTEGER NOT NULL DEFAULT 0 CHECK (quantity > 0),
  unit_price  REAL    NOT NULL DEFAULT 0 CHECK (unit_price >= 0),   -- 单件实际售价
  sale_date   TEXT    NOT NULL,                         -- YYYY-MM-DD
  remark      TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 索引（查询性能）
CREATE INDEX idx_purchase_style  ON purchase(style_code);
CREATE INDEX idx_purchase_date   ON purchase(purchase_date);
CREATE INDEX idx_purchase_size   ON purchase(size_id);
CREATE INDEX idx_sale_style      ON sale(style_code);
CREATE INDEX idx_sale_date       ON sale(sale_date);
CREATE INDEX idx_sale_size       ON sale(size_id);
CREATE INDEX idx_product_cat     ON product(category_id);
CREATE INDEX idx_product_supplier ON product(supplier_id);
```

### 5.3 净库存计算
**不建库存表**，实时按「进货 − 销售」汇总，避免冗余不一致：

```sql
SELECT style_code, size_id, size_text, SUM(delta) AS stock
FROM (
    SELECT style_code, size_id, size_text,  quantity AS delta FROM purchase
    UNION ALL
    SELECT style_code, size_id, size_text, -quantity AS delta FROM sale
) t
GROUP BY style_code, size_id;
```

> 销售开单时校验"本次数量 ≤ 当前净库存"并给出提示（是否强制拦截见 §11-Q）。
> 数据量达到瓶颈时再引入库存快照表（P2）。

---

## 6. 功能需求（按模块 + 优先级）

优先级：**P0 = MVP 必须** · P1 = 重要增强 · P2 = 未来

| 编号 | 模块 | 功能 | 优先级 |
|---|---|---|---|
| F1 | 商品档案 | 增删改查款式（款号唯一）；上传/替换主图；分类、厂家、零售价 | P0 |
| F2 | 进货录入 | 单条 & **批量录入**（同一日期多款多码）；自动补全款号/分类/厂家/尺码；新值自动入字典 | P0 |
| F3 | 进货查询 | 关键词 + 分类 + 厂家 + 尺码 + 日期区间筛选；分页 | P0 |
| F4 | **销售出库** | 销售开单（选款/码/数量/售价，自动带出零售价）；扣减库存；库存不足提示 | P0 |
| F5 | 销售查询 | 关键词 + 分类 + 尺码 + 日期区间筛选；分页 | P0 |
| F6 | 库存汇总 | 按款号×尺码显示**净库存**（含进货/销售/结存三列）；带主图 | P0 |
| F7 | 字典维护 | 分类 / 厂家 / 尺码 的维护 | P0 |
| F8 | 图片管理 | 上传、压缩、生成缩略图、查看大图 | P0 |
| F9 | 用户登录 | 单账号登录（账密），会话保持 | P0 |
| F10 | 统计报表 | 进货/销售金额与数量、**毛利**，按时间/分类/厂家维度汇总 | P1 |
| F11 | 数据导入导出 | 导出 Excel（进货明细、销售明细、库存）；导入历史 Excel 模板 | P1 |
| F12 | 多用户/权限 | 多账号、角色权限 | P2 |
| F13 | 多图 / 批次 | 一个款多张图；批次成本 | P2 |

> **毛利说明**：因确定"不做批次"（Q6），无法精确匹配每件的进货成本。毛利按**加权平均成本**估算：`毛估 = Σ(售价×数量) − Σ(平均进货价×销售量)`，并在报表标注为"估算"。若需精确成本，后续引入批次（P2）。

---

## 7. 页面 / 信息架构

```
登录页
└── 主布局（侧边导航 + 顶栏搜索）
    ├── 工作台/概览（今日进销、库存概览、金额卡片）
    ├── 进货管理
    │   ├── 进货录入（表单 + 批量模式）
    │   └── 进货记录（列表 + 筛选 + 编辑）
    ├── 销售管理
    │   ├── 销售开单（快速开单，库存实时校验）
    │   └── 销售记录（列表 + 筛选 + 编辑）
    ├── 库存查询（款号×尺码：进货/销售/结存，带主图）
    ├── 商品档案（款式列表 + 详情/编辑）
    ├── 统计报表（趋势 / 分类占比 / 厂家排行 / 毛利）
    └── 系统设置
        ├── 字典管理（分类/厂家/尺码）
        ├── 账号设置
        └── 数据备份 / 导入导出
```

---

## 8. API 设计（REST）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/logout` | 登出 |
| GET | `/api/products` | 商品列表（`keyword/category_id/supplier_id/page/page_size`） |
| POST | `/api/products` | 新建款式 |
| GET | `/api/products/{id}` | 款式详情 |
| PUT | `/api/products/{id}` | 更新款式 |
| DELETE | `/api/products/{id}` | 删除款式 |
| POST | `/api/products/{id}/image` | 上传/替换主图（multipart） |
| GET | `/api/purchases` | 进货记录（`style_code/category_id/supplier_id/size_id/date_from/date_to/page`） |
| POST | `/api/purchases` | 新增进货（支持数组批量） |
| PUT | `/api/purchases/{id}` | 更新 |
| DELETE | `/api/purchases/{id}` | 删除 |
| GET | `/api/sales` | 销售记录（同上筛选） |
| POST | `/api/sales` | 新增销售（出库，校验净库存） |
| PUT | `/api/sales/{id}` | 更新 |
| DELETE | `/api/sales/{id}` | 删除 |
| GET | `/api/stock` | 净库存汇总（进货/销售/结存，按款号×尺码） |
| GET | `/api/stock/{style_code}/{size_id}` | 单款单码当前库存（开单用） |
| GET | `/api/stats/summary` | 统计汇总（`from/to/group_by`） |
| GET | `/api/stats/profit` | 毛利估算 |
| GET | `/api/dict/categories` `/suppliers` `/sizes` | 字典查询 |
| POST/PUT/DELETE | `/api/dict/{type}[/{id}]` | 字典维护 |
| GET | `/api/export/purchases.xlsx` | 导出进货明细 |
| GET | `/api/export/sales.xlsx` | 导出销售明细 |
| GET | `/api/export/stock.xlsx` | 导出库存 |

---

## 9. 技术架构建议

| 层 | 选型 | 理由 |
|---|---|---|
| 后端框架 | **FastAPI** | 异步、自动生成 API 文档、Pydantic 校验强、CRUD + 文件上传开发快 |
| ORM / 迁移 | **SQLAlchemy 2.0 + Alembic** | 成熟稳定，迁移可控 |
| 图片处理 | **Pillow** | 压缩 + 生成缩略图 |
| Excel | **openpyxl / pandas** | 导入导出 |
| 数据库 | **SQLite（WAL 模式）** | 单店低并发场景完全够用，零运维 |
| 前端 | **Vue 3 + Vite** | 现代组合式 API，构建快 |
| UI 组件库 | **Element Plus** | 中文文档与社区最好，后台表格/表单开箱即用 |
| 状态/路由/请求 | **Pinia + Vue Router + Axios** | Vue 3 标准组合 |
| 部署 | 单机 uvicorn 或 Docker；前端构建为静态文件由后端/Nginx 托管 | 简单，便于店主自托管 |

> **FastAPI vs Flask vs Django**：本项目是小型 CRUD + 图片上传 + Excel 导出，Django 全家桶偏重，Flask 需自行拼装；**FastAPI** 在开发效率与文档化上最优。

---

## 10. 非功能需求

| 类别 | 要求 |
|---|---|
| 性能 | 支持 10 万级进销记录；列表查询响应 < 1s（配合索引） |
| 并发 | 1–3 用户，SQLite WAL 模式足够 |
| 备份 | 每日自动备份 `.db` 文件 + 图片目录；提供手动导出 |
| 数据一致性 | 销售出库需校验库存；关键写操作使用事务 |
| 安全 | 登录鉴权（JWT / Session）；上传文件类型与大小校验；图片路径防目录穿越 |
| 兼容 | 桌面 + 移动端浏览器自适应 |
| 语言 | 全中文界面 |
| 易用性 | 录入支持回车连录、复制上一行、款号检索；开单自动带出零售价 |

---

## 11. 关键决策点（已确认）

| # | 问题 | 确认结果 |
|---|---|---|
| 1 | 只做进货还是也做销售出库/库存扣减？ | ✅ **都要做**（本期含销售出库） |
| 2 | 一个款号对应多个尺码、共用一张主图？ | ✅ **是**，采用方案 B（档案 + 明细） |
| 3 | 主图一张还是多张？ | ✅ 本期 **1 张**，多图 P2 |
| 4 | 分类/厂家/尺码固定还是自由输入？ | ✅ **字典表 + 可维护 + 录入自动新增** |
| 5 | 多账号与权限？ | ✅ **单账号登录** |
| 6 | 同款不同批次进货价如何处理？ | ✅ 进货记录级**保存实际进货价**，不做批次（毛利按加权平均估算） |
| 7 | 导入历史 Excel？ | ✅ P1 提供导入模板 |
| 8 | 库存预警阈值？ | ✅ **不需要** |
| 9 | 零售价/售价是否要记？ | ✅ **需要记**（档案存零售价，销售记录存实际售价） |

### 补充决策（已确认采用默认）

| # | 问题 | 确认结果 |
|---|---|---|
| Q10 | 销售时库存不足（净库存 < 销售数量）如何处理？ | ✅ **允许负库存但强提示**（急单不拦死；开单时高亮警告） |
| Q11 | 是否需要"退货/进货退回"？ | ✅ **本期不做**（可用编辑/负数记录变通） |
| Q12 | 分类是否可以多级（如 上衣 > T恤）？ | ✅ 本期 **单级分类** |
| Q13 | 报表是否需要每日销售趋势折线？ | ✅ **P1 提供** |

---

## 12. 迭代计划（建议）

| 里程碑 | 范围 | 预估 |
|---|---|---|
| **M1 · MVP** | F1 档案、F2 进货录入、F3 进货查询、F4 销售开单、F5 销售查询、F6 净库存、F7 字典、F8 图片、F9 登录 | ~1.5 周 |
| **M2 · 增强** | F10 统计报表（含毛利）、F11 导入导出 | ~4–5 天 |
| **M3 · 远期** | F12 多用户、F13 多图/批次、退货 | 待定 |

---

## 13. 风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| 录入/开单效率低，店主不愿用 | 系统闲置 | 批量录入、回车连录、款号自动补全、开单自动带价 |
| 图片存储膨胀 | 磁盘占用大 | 上传压缩 + 缩略图 |
| SQLite 未备份导致数据丢失 | 数据不可恢复 | 每日自动备份 + 手动导出 |
| 无批次 → 毛利不精确 | 报表失真 | 明确标注"估算"；精确需求走 P2 批次 |
| 库存负值/超卖 | 数据失真 | 开单库存校验 + 提示（见 Q10） |
| 需求膨胀为完整 ERP | 工期失控 | 明确非目标，严格优先级 |

---

## 14. 待办（下一步）

1. ~~店主回答第 11 节补充问题 Q10–Q13~~ ✅ 已完成（采用默认值）。
2. 输出 **技术设计文档（TDD）**：数据库迁移脚本、接口详细定义（请求/响应体）、页面原型。
3. 进入 M1 开发。
