# JBOOK API 参考

基础 URL：`http://127.0.0.1:8000`  
除标注外，JSON 接口返回 `application/json`。页面路由返回 HTML。

## 业务页面

| 路径 | 说明 |
|------|------|
| `/` | 首页 |
| `/books/` | 图书列表（筛选、搜索、分页） |
| `/books/<sell_id>/` | 图书详情 |
| `/sell/new/` | 发布二手书 |
| `/accounts/login/` | 登录 |
| `/accounts/profile/` | 个人中心 |
| `/trade/orders/` | 订单列表 |
| `/trade/messages/` | 私信 |
| `/analytics/dashboard/` | 公开数据看板 |
| `/analytics/admin/` | 运营看板（管理员） |
| `/analytics/ml/` | 模型分析 |

## JSON API

### 搜索联想

`GET /api/search-suggest/?q=关键词`

```json
{ "items": [{ "book_name": "...", "author": "...", "isbn": "..." }] }
```

### ISBN 补全

`GET /api/isbn/?isbn=9787111213826`

```json
{ "success": true, "data": { "book_name": "...", "author": "...", "cat_id": 1 } }
```

### 智能定价

`GET /api/suggest-price/?original_price=50&pub_year=2020&cat_id=1&quality=3`

```json
{ "success": true, "suggested_price": 28.5, "hint": "..." }
```

### 看板数据

`GET /analytics/api/data/?days=30&cat_id=`

管理员：`GET /analytics/api/data/?admin=1&days=30`

### 模型分析

`GET /analytics/api/ml/?view=standard`

专业视图需管理员 session。

### 私信轮询

`GET /trade/messages/poll/?with=<user_id>`

```json
{ "messages": [{ "id": 1, "from_me": true, "content": "...", "time": "14:30" }] }
```

## 认证

Session Cookie。登录后 `session` 含 `user_id`、`username`、`role`（0 用户 / 1 管理员）。

## 管理命令

| 命令 | 说明 |
|------|------|
| `seed_demo --force` | 导入 Book-Crossing 子集 |
| `train_ml` | 训练定价/热度模型 |
| `daily_report` | 生成运营日报 |
