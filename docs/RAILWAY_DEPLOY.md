# JBOOK Railway 全流程部署

## 架构说明

| 层级 | 表/数据 | 谁写入 | 谁读取 |
|------|---------|--------|--------|
| 原始层 | `book`, `users`, `ratings` | `load_bx.py` | `bootstrap_jbook --source pg` |
| 业务层 | `book_base`, `sell_book`, `category`, `user`… | `bootstrap_jbook` | **网站首页/书市** |

只跑 `load_bx.py` 网站仍是空的；必须再跑 `bootstrap_jbook` 把数据同步到业务表。

---

## 一、Railway 控制台配置

### 1. PostgreSQL 插件

添加 **PostgreSQL**，记下连接信息。

### 2. Web 服务（Django）

- **Root Directory**：`backend`
- **Build Command**（若不用 `railway.toml`）：
  ```bash
  pip install -r requirements.txt && python manage.py collectstatic --noinput
  ```
- **Start Command**（若不用 `railway.toml`）：
  ```bash
  bash scripts/railway_start.sh
  ```

### 3. Web 服务 Variables（必填）

在 PostgreSQL 服务中复制 **`DATABASE_URL`**，粘贴到 Web 服务：

```env
DATABASE_URL=postgresql://postgres:xxx@xxx.railway.app:port/railway
DJANGO_SECRET_KEY=随机长字符串
DEBUG=False
ALLOWED_HOSTS=.railway.app,jbook.up.railway.app
CSRF_TRUSTED_ORIGINS=https://jbook.up.railway.app
JBOOK_BOOTSTRAP=1
```

`JBOOK_BOOTSTRAP=1`：每次部署若无在售书则自动 `bootstrap_jbook`（已有数据则跳过）。

---

## 二、本地：CSV → PostgreSQL（你已完成可跳过）

```powershell
cd data\book_crossing\raw
$env:BX_PG_PASSWORD="你的密码"
$env:BX_PG_HOST="turntable.proxy.rlwy.net"
$env:BX_PG_PORT="28777"
python load_bx.py
```

---

## 三、同步到网站业务表（关键一步）

### 方式 A：Railway Web Shell（推荐）

```bash
cd backend   # 若 Root 已是 backend 则省略
python manage.py migrate
python manage.py bootstrap_jbook --source pg --force
```

### 方式 B：本地连同一 DATABASE_URL

```powershell
cd backend
$env:DATABASE_URL="postgresql://..."
python manage.py migrate
python manage.py bootstrap_jbook --source pg --force
```

成功输出示例：`在售(已审核) 1800` → 刷新首页可见图书。

### 方式 C：无 PG 原始表时从 CSV 导入

```bash
python manage.py bootstrap_jbook --source csv --force
```

（需 `data/book_crossing/raw/*.csv` 或自动下载）

---

## 四、重新部署 Web 服务

推送代码后 Railway 自动：

1. `migrate`
2. `bootstrap_jbook --source auto`（有 PG BX 表则用 pg）
3. 启动 Gunicorn

---

## 五、演示账号

| 账号 | 密码 |
|------|------|
| admin | admin123 |
| seller1 | 123456 |
| buyer1 | 123456 |

---

## 六、常见问题

**Q：load_bx 成功但首页仍「暂无图书」？**  
A：未执行 `bootstrap_jbook`，或 Django 未配置 `DATABASE_URL`（仍用 SQLite）。

**Q：bootstrap 很慢？**  
A：正常。可缩小规模：`--max-books 800 --max-users 150 --max-ratings 5000`。

**Q：重复部署会清空数据吗？**  
A：默认不会。仅 `--force` 或 `bootstrap_jbook --force` 会清空业务表重导。
