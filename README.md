# JBOOK

校园二手书交易平台。基于 **Django** 全栈与 **Book-Crossing** 真实数据集，集成智能定价、协同推荐与 ECharts 数据看板。

---

## 特性概览

| 模块 | 能力 |
|------|------|
| 交易业务 | 注册登录、发布/编辑、多条件筛选、收藏、私信、订单流转 |
| 数据工程 | Book-Crossing 导入、行为日志、清洗报告、每日运营报表 |
| 机器学习 | 二手价预测、热度三分类、混合推荐（CF + 内容） |
| 可视化 | 公开看板、管理员运营看板、模型分析（轻量/标准/专业三视图） |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.10+ · Django 5 |
| 前端 | Bootstrap 5 · Font Awesome · ECharts · 原生 JS |
| 数据库 | SQLite（默认）/ MySQL 8 |
| 数据科学 | Pandas · NumPy · Scikit-learn · Joblib |

---

## 快速开始

### 环境要求

- Python 3.10 及以上
- Windows / macOS / Linux

### 一键启动

**PowerShell（推荐）：**

```powershell
cd backend\scripts
.\run.ps1
```

**CMD：**

```bat
cd backend\scripts
run.bat
```

**Linux / macOS：**

```bash
cd backend/scripts
chmod +x run.sh build.sh
./run.sh
```

浏览器访问：**http://127.0.0.1:8000/**

> 首次启动会自动：创建虚拟环境 → 安装依赖 → 迁移数据库 → 下载 Book-Crossing CSV → 导入示例子集 → 启动服务。  
> 若端口 8000 被占用，请先 `Ctrl+C` 停止旧进程。

### 演示账号

| 账号 | 密码 | 角色 |
|------|------|------|
| `admin` | `admin123` | 管理员（运营看板、后台管理） |
| `seller1` | `123456` | 卖家 |
| `buyer1` | `123456` | 买家 |
| `bx_*` | `123456` | Book-Crossing 映射用户 |

---

## 常用命令

在 `backend/` 目录下执行（需先激活 `venv`）：

```bash
# 数据库迁移
python manage.py migrate

# 重新导入 Book-Crossing 数据（清空后重建）
python manage.py seed_demo --force

# 可选：限制导入规模
python manage.py seed_demo --force --max-books 1800 --max-users 280 --max-ratings 12000

# 训练 ML 模型
python manage.py train_ml

# 生成运营日报 + 异常标记
python manage.py daily_report

# 生成数据清洗报告
python ../data/cleaning/clean_books.py

# 特征统计报告
python ../data/ml/feature_engineering.py

# 项目健康检查
python manage.py check
```

单独下载数据集：

```bash
python data/book_crossing/download.py
```

---

## 主要页面

| 路径 | 说明 |
|------|------|
| `/` | 首页（推荐、最新、低价专区） |
| `/books/` | 书市列表（价格滑块、成色、排序） |
| `/books/<id>/` | 详情（智能估价、猜你喜欢） |
| `/analytics/dashboard/` | 公开数据看板 |
| `/analytics/admin/` | 运营看板（管理员） |
| `/analytics/ml/` | 模型分析模块 |
| `/analytics/manage/` | 后台管理 |

API 说明见 [docs/API.md](docs/API.md)。

---

## 项目结构

```
JBOOK/
├── backend/                 # Django 主工程
│   ├── accounts/            # 用户、登录、个人中心
│   ├── catalog/             # 图书类目与基础信息
│   ├── marketplace/         # 在售、收藏、筛选、API
│   ├── trade/               # 订单、私信
│   ├── analytics/           # 看板、报表、后台
│   ├── mlapp/               # 模型训练与推理
│   ├── templates/           # 页面模板
│   ├── static/              # CSS / JS
│   ├── scripts/             # run.bat / run.ps1 / run.sh
│   └── manage.py
├── data/
│   ├── book_crossing/       # 数据集下载与说明
│   ├── cleaning/            # 数据质量报告脚本
│   └── ml/                  # 特征工程脚本
├── docs/
│   ├── API.md
│   ├── 数据库设计说明书.md
│   ├── 项目策划说明.txt
│   ├── 前端优化说明.txt
│   └── reports/             # 自动生成的分析报告
└── README.md
```

---

## 数据来源

平台使用 **[Book-Crossing Dataset](https://grouplens.org/datasets/book-crossing/)**（Ziegler et al., WWW 2005）：

- 约 27 万图书、28 万用户、115 万条评分
- 导入时按评分数取 Top-N 子集，映射为 JBOOK 用户、在售商品与行为日志
- 原始 CSV 约 115MB，存放于 `data/book_crossing/raw/`（已在 `.gitignore` 中排除）

引用：

> Cai-Nicolas Ziegler et al. *Improving Recommendation Lists Through Topic Diversification.* WWW 2005.

---

## MySQL 部署（可选）

1. 复制 `backend/.env.example` 为 `backend/.env`：

```env
USE_SQLITE=False
DB_NAME=booktrade
DB_USER=root
DB_PASSWORD=你的密码
DB_HOST=127.0.0.1
DB_PORT=3306
```

2. 执行 `backend/sql/init.sql` 创建库表前缀（如需要）
3. `python manage.py migrate && python manage.py seed_demo --force`

---

## 开发与质量

```bat
cd backend\scripts
build.bat      :: Windows：manage.py check + 迁移检查
```

```bash
./build.sh     # Linux/macOS 同等检查
```

**代码组织原则：**

- 业务逻辑放在各 app 的 `services.py` / `views.py`
- 数据导入集中在 `marketplace/data/book_crossing.py`
- 前端交互在 `static/js/site.js`、`dashboard.js`、`ml_analysis.js`
- 模板按模块划分于 `templates/`

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [docs/API.md](docs/API.md) | JSON 接口与路由 |
| [docs/数据库设计说明书.md](docs/数据库设计说明书.md) | 表结构 |
| [docs/reports/机器学习模型报告.md](docs/reports/机器学习模型报告.md) | 模型指标（`train_ml` 生成） |
| [docs/reports/数据清洗报告.md](docs/reports/数据清洗报告.md) | 数据质量（`clean_books.py` 生成） |
| [data/book_crossing/README.md](data/book_crossing/README.md) | 数据集下载说明 |

---

## 许可证与免责

本项目为课程/学习用途。Book-Crossing 数据请遵循原数据集使用约定；平台模型分析结果仅供参考，不构成交易建议。

---

**JBOOK** — 让每一本二手书找到下一位读者。

