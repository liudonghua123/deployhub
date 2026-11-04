# DeployHub · 自动部署平台

前后端分离的一站式应用部署与运维平台：连接 GitHub 仓库自动拉取部署，管理应用进程与端口，在线查看实时日志与 Shell 终端，在线编辑 Nginx 站点配置并 test / reload / restart，内置简单 RBAC 三级用户权限。

## 功能模块

| 模块 | 说明 |
|------|------|
| 仪表盘 | 应用运行状态、监听端口、Nginx 配置数、最近部署概览，5s 自动刷新 |
| 应用管理 | 创建/编辑/删除应用；绑定 GitHub 仓库与分支、部署目录、**初始运行命令**（如 `npm install`）、**启动命令**、环境变量；一键 部署/启动/停止/重启 |
| 应用详情 | 运行信息（PID/端口/时长/Webhook URL）、部署历史（可展开查看完整部署日志）、**WebSocket 实时日志** |
| 端口监听 | 列出系统所有 TCP 监听端口，标注属于哪个托管应用，支持筛选 |
| 在线终端 | 基于 xterm.js 的服务器 Shell（WebSocket + PTY），运维及以上可用 |
| Nginx 管理 | 站点配置文件列表/新建/编辑（CodeMirror nginx 语法高亮）/删除，配置检查 `nginx -t`、平滑 `reload`、`restart` |
| 用户权限 | RBAC 三级角色：**admin**（全部，含用户管理/删除应用/nginx restart）、**operator**（应用增改/启停/部署/nginx 编辑/终端）、**viewer**（只读） |
| 设置 | 修改密码、系统信息 |

## 自动部署流程

```
手动点击"部署" 或 GitHub push → Webhook 触发
  → git clone / git pull（部署目录）
  → 执行初始运行命令（init_command）
  → 停止旧进程 → 以启动命令拉起新进程
  → 部署日志落库，应用详情页可查看
```

Webhook 地址：`http://<host>/api/deploy/webhook/{应用名}`（在应用详情页可一键复制），支持 `X-Hub-Signature-256` 签名校验（设置环境变量 `DEPLOYHUB_GITHUB_SECRET` 开启）。

## 技术栈

- **后端**：Python 3.13 · FastAPI · SQLAlchemy(SQLite) · JWT(bcrypt) · psutil · WebSocket
- **前端**：Vue 3 · Vite · Pinia · Vue Router · xterm.js · CodeMirror 5
- **部署**：git · 任意可通过 shell 启动的应用

## 快速开始

### 后端（端口 8310）

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8310
```

首次启动自动建库并创建三个默认账号：

| 账号 | 密码 | 角色 |
|------|------|------|
| admin | admin123 | 管理员 |
| operator | operator123 | 运维 |
| viewer | viewer123 | 访客 |

### 前端（端口 5180，代理 /api → 8310）

```bash
cd frontend
npm install
npm run dev        # http://localhost:5180
npm run build      # 产物在 dist/，可由 nginx 托管
```

## 环境变量（可选）

| 变量 | 默认 | 说明 |
|------|------|------|
| `DEPLOYHUB_SECRET` | 随机默认值 | JWT 密钥，**生产必须修改** |
| `DEPLOYHUB_DB` | `sqlite:///./deployhub.db` | 数据库连接 |
| `DEPLOYHUB_WORKSPACES` | `./workspaces` | 应用部署工作区 |
| `DEPLOYHUB_LOGS` | `./logs` | 应用运行日志目录 |
| `DEPLOYHUB_NGINX_CONF` | `/etc/nginx/conf.d` | nginx 站点配置目录（Windows 填实际目录） |
| `DEPLOYHUB_NGINX_BIN` | `nginx` | nginx 可执行文件路径 |
| `DEPLOYHUB_GITHUB_SECRET` | 空 | Webhook 签名密钥 |

## 生产建议

- 由 nginx 托管 `frontend/dist` 并反向代理 `/api`（含 WebSocket upgrade）到 8310
- 修改 `DEPLOYHUB_SECRET` 与默认账号密码
- Windows 下进程以 shell 模式启动；Linux 下使用进程组信号，`stop` 先 SIGTERM 后 SIGKILL

## 目录结构

```
deployhub/
├── backend/
│   ├── app/
│   │   ├── core/         # 配置、JWT/RBAC
│   │   ├── models.py     # User / App / Deployment / Setting
│   │   ├── routers/      # auth / apps / deploy / logs / ports / nginx / users
│   │   ├── services/     # 进程管理、部署流水线、nginx、端口扫描
│   │   └── main.py
│   └── requirements.txt
└── frontend/
    └── src/
        ├── api.js / toast.js / router.js
        ├── stores/auth.js
        ├── styles/main.css
        └── views/        # 8 个业务页面
```
