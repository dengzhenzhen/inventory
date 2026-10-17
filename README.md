# 服装店进销存管理系统

面向小型实体服装店的轻量级 **进货 / 销售 / 库存** 管理系统。覆盖「进货录入 → 库存 → 销售出库 → 统计报表」闭环，可自托管、零运维。

## 功能

- **商品档案**：款号（唯一）、品名、分类、厂家、零售价、主图
- **进货管理**：单条 + 批量录入；输入新款号自动建档；字典（分类/厂家/尺码）自动新增；多条件查询
- **销售管理**：销售开单，自动带出分类/零售价/当前库存；库存不足强提示但允许负库存
- **库存查询**：按「款号 × 尺码」实时净库存（进货 − 销售），负库存标红
- **统计报表**：进货/销售金额、毛利（估算）、每日销售趋势、分类占比
- **图片**：上传压缩 + JPG 存储 + 静态托管
- **导出**：进货明细 / 销售明细 / 库存 Excel
- **登录**：单账号鉴权（JWT）

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python · FastAPI · SQLAlchemy 2.0 · PyJWT · Pillow · openpyxl |
| 数据库 | SQLite（WAL 模式） |
| 前端 | Vue 3 · Vite · Element Plus · Pinia · Vue Router · Axios |
| 部署 | 单机 uvicorn + 前端构建为静态文件 |

## 目录结构

```
.
├── backend/             # FastAPI 后端
│   ├── app/
│   │   ├── routers/     # auth / dicts / products / purchases / sales / stock / stats / upload / exports
│   │   ├── models.py    # 数据模型
│   │   ├── crud.py      # 领域辅助（自动建档 / 序列化 / 库存聚合）
│   │   ├── security.py  # 密码哈希 + JWT
│   │   ├── seed.py      # 初始化账号、字典与演示数据
│   │   └── main.py      # 应用入口
│   ├── requirements.txt
│   └── .env.example
├── frontend/            # Vue 3 前端
│   └── src/{api,stores,router,layout,views}
├── docs/PRD.md          # 产品需求分析
├── prototype/index.html # 可点击原型（设计稿）
├── dev.sh               # 一键启动脚本
└── README.md
```

## 快速开始

### 依赖
- Python 3.10+ 与 [uv](https://github.com/astral-sh/uv)
- Node.js 18+ 与 npm

### 一键启动
```bash
bash dev.sh
```
- 后端：http://localhost:8000 （API 文档 http://localhost:8000/docs）
- 前端：http://localhost:5173

### 手动启动

后端：
```bash
cd backend
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

前端：
```bash
cd frontend
npm install
npm run dev
```

### 默认账号
`admin / admin123`（可用环境变量 `DEFAULT_USERNAME` / `DEFAULT_PASSWORD` 修改）

## 配置

后端环境变量见 `backend/.env.example`：`SECRET_KEY`、`DEFAULT_USERNAME`、`DEFAULT_PASSWORD`、`TOKEN_EXPIRE_MINUTES`、`CORS_ORIGINS`、`MAX_UPLOAD_MB`。

## API 概览（前缀 `/api`）

| 模块 | 端点 |
|---|---|
| 认证 | `POST /auth/login` · `POST /auth/logout` · `GET /auth/me` · `PUT /auth/password` |
| 字典 | `GET/POST /dict/{category\|supplier\|size}` · `PUT/DELETE /dict/{type}/{id}` |
| 商品 | `GET/POST /products` · `GET/PUT/DELETE /products/{id}` · `GET /products/by-code/{code}` |
| 进货 | `GET/POST /purchases` · `POST /purchases/batch` · `PUT/DELETE /purchases/{id}` |
| 销售 | `GET/POST /sales` · `PUT/DELETE /sales/{id}` |
| 库存 | `GET /stock` · `GET /stock/current` |
| 统计 | `GET /stats/summary` · `GET /stats/daily-sales` · `GET /stats/category-rank` |
| 上传 | `POST /upload/image` |
| 导出 | `GET /export/{purchases\|sales\|stock}.xlsx` |

除登录外，所有接口需请求头 `Authorization: Bearer <token>`。

## 数据与备份

- 数据库：`backend/data/inventory.db`（SQLite）
- 图片：`backend/static/images/`
- 备份：将以上两者复制到外部存储即可

## 说明与限制

- 毛利为**估算**（加权平均成本，未启用批次）
- 允许负库存（强提示，不拦截）
- 本期不含：退货、分类多级、Excel 导入（P1）
- 建表使用 SQLAlchemy `create_all`，暂未接入 Alembic 迁移

## Windows 打包与使用

Windows 版为单文件 `Inventory.exe`，使用者无需安装 Python。

- 构建与 CI：[docs/BUILD-WINDOWS.md](docs/BUILD-WINDOWS.md)
- 使用说明（SmartScreen、防火墙、局域网访问、备份）：[docs/USER-GUIDE-WINDOWS.md](docs/USER-GUIDE-WINDOWS.md)

## 相关文档

- 产品需求分析：`docs/PRD.md`
- 交互原型：`prototype/index.html`（浏览器直接打开）
