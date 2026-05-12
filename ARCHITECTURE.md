# Desktop AI Companion - 新架构说明

## 架构概述

```
┌─────────────────────────────────────────────────────────┐
│                    Tauri 桌面壳                          │
│  ┌─────────────────────────────────────────────────────┐│
│  │              Web 前端 (HTML/CSS/JS)                 ││
│  │  ┌──────────────┐  ┌─────────────────────────────┐  ││
│  │  │  Live2D SDK  │  │   UI 组件 (聊天/菜单/设置)   │  ││
│  │  │  (PixiJS)    │  │   (TypeScript + Vite)        │  ││
│  │  └──────────────┘  └─────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
                            ↕ HTTP / IPC
┌─────────────────────────────────────────────────────────┐
│              Python 后端服务 (FastAPI)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │  AI 对话接口  │  │  本地数据库  │  │  配置管理     │ │
│  │  (LLM API)   │  │  (SQLite)    │  │  (JSON)       │ │
│  └──────────────┘  └──────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 技术选型

### 前端 (Tauri + Web)

| 模块 | 技术 | 说明 |
|------|------|------|
| 构建工具 | Vite | 快速开发 + 热更新 |
| 框架 | 原生 TS | 轻量级，无框架依赖 |
| Live2D 渲染 | pixi-live2d-display | 基于 PixiJS 的 Live2D 渲染器 |
| 2D 引擎 | PixiJS v7 | WebGL 渲染 |
| 桌面壳 | Tauri v2 | Rust 原生窗口 |

### 后端 (Python)

| 模块 | 技术 | 说明 |
|------|------|------|
| Web 框架 | FastAPI | 高性能异步 API |
| AI 接口 | 硅基流动/DeepSeek | 托管模型，开箱即用 |
| 数据库 | SQLite | 本地存储 |
| HTTP 客户端 | httpx | 调用第三方 API |

## 目录结构

```
desktop-ai-companion/
├── tauri-app/                 # Tauri + Web 前端
│   ├── src/
│   │   ├── main.ts           # 主入口 (Live2D 初始化)
│   │   ├── chat-client.ts    # 聊天客户端
│   │   └── ui.ts             # UI 组件
│   ├── index.html
│   ├── package.json
│   ├── tauri.conf.json
│   └── src-tauri/            # Tauri Rust 代码
│       ├── src/main.rs
│       ├── Cargo.toml
│       └── tauri.conf.json
│
├── backend/                   # Python 后端服务
│   ├── server.py             # FastAPI 服务
│   └── requirements.txt
│
├── assets/                    # 资源文件
│   ├── live2d/               # Live2D 模型
│   └── characters/           # 角色图片
│
└── data/                      # 本地数据
    ├── config.json
    └── companion.db
```

## 通信流程

### 1. 前端 → 后端 (AI 对话)

```
用户输入 → Tauri 前端 → HTTP POST /chat → Python FastAPI
                                              ↓
                                         调用 AI API
                                              ↓
                                          返回回复
                                              ↓
前端渲染 ←──────────────────────────── JSON Response
```

### 2. Tauri IPC (原生能力)

```
前端 TypeScript          Rust 后端
       │                    │
       │  invoke('cmd')     │
       ├───────────────────>│
       │                    │
       │  Result<T>         │
       │<───────────────────┤
```

## 单一职责边界

- Tauri/Web: 负责窗口、交互、Live2D 渲染、聊天 UI
- FastAPI: 负责聊天 API、配置 API、聊天历史 API
- SQLite/JSON: 由 Python 后端统一读写
- Rust IPC: 只负责窗口级命令，例如退出、托盘、窗口控制

## 当前仓库状态

- `tauri-app/` 是正式桌面前端
- `backend/server.py` 是正式服务入口
- `app/` 下的 PyQt6 代码保留为历史原型，不再作为主启动链路维护

## 启动顺序

1. **启动 Python 后端**: `python backend/server.py` (端口 8080)
2. **启动 Tauri 开发环境**: `npm run tauri:dev`
3. **Tauri 窗口加载前端资源**
4. **前端通过 HTTP 调用后端**: `http://localhost:8080/chat`

## 迁移计划

### Phase 1 (当前)
- [x] 创建 Tauri 项目骨架
- [x] 集成 Live2D Cubism SDK
- [x] Python 后端基础 API
- [ ] Live2D 模型加载 (Kei)
- [ ] 聊天窗口 UI

### Phase 2
- [ ] 接入真实 AI 接口
- [ ] SQLite 本地存储
- [ ] 配置持久化
- [ ] 系统托盘集成

### Phase 3
- [ ] 开机自启
- [ ] 打包发布
- [ ] 多角色支持
- [ ] TTS 语音

## 开发命令

### 前端开发
```bash
cd tauri-app
npm install
npm run dev        # Vite 开发服务器
npm run tauri:dev  # Tauri 开发模式
```

### 后端开发
```bash
cd backend
pip install -r requirements.txt
python server.py
```

### 生产构建
```bash
cd tauri-app
npm run build
npm run tauri:build
```

## 参考资源

- Tauri 文档：https://tauri.app/
- Live2D Cubism SDK: https://docs.live2d.com/
- pixi-live2d-display: https://github.com/guansss/pixi-live2d-display
- FastAPI 文档：https://fastapi.tiangolo.com/
