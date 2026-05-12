# Desktop AI Companion - 新架构版本

> 🚧 迁移中 - Tauri + Web 前端 + Live2D Cubism

> 注意：仓库仍保留 `app/` 下的 PyQt6 原型代码，仅用于历史参考与资源复用，不再作为主启动方式维护。

## 架构对比

| 维度 | 旧架构 (PyQt6) | 新架构 (Tauri) |
|------|---------------|---------------|
| 渲染引擎 | PyQt6 QLabel | PixiJS + Live2D Cubism |
| UI 开发 | Python + Qt 样式表 | HTML/CSS/JS |
| Live2D 支持 | 简化版 (纹理贴图) | 完整版 (Cubism SDK) |
| 透明窗口 | Qt 原生 | Tauri 配置 |
| 生态 | 较小众 | 大量桌面宠物项目参考 |

## 快速开始

### 前端 (Tauri + Live2D)

```bash
cd tauri-app
npm install
npm run tauri:dev
```

### 后端 (Python FastAPI)

```bash
cd backend
pip install -r requirements.txt
python server.py
```

## 项目结构

```
desktop-ai-companion/
├── tauri-app/              # Tauri + Web 前端
│   ├── src/               # TypeScript 源码
│   ├── index.html         # 主页面
│   └── src-tauri/         # Rust 后端
├── backend/               # Python 后端服务
│   ├── server.py         # FastAPI 接口
│   └── requirements.txt
├── assets/                # Live2D 模型/角色图片
└── data/                  # 本地数据 (配置/数据库)
```

## 核心功能

### 已实现
- [x] Tauri 项目骨架
- [x] Live2D 模型加载 (Kei)
- [x] 聊天窗口 UI
- [x] Python 后端 API
- [x] 右键菜单

### 待实现
- [ ] 接入真实 AI 接口
- [ ] SQLite 本地存储
- [ ] 系统托盘集成
- [ ] 开机自启
- [ ] TTS 语音

## 开发计划

### Phase 1 (MVP)
- [ ] Live2D 模型完整渲染
- [ ] 基础聊天功能
- [ ] 位置持久化

### Phase 2 (增强)
- [ ] 记忆系统
- [ ] 免打扰模式
- [ ] 多角色切换

### Phase 3 (商业化)
- [ ] 高级角色付费
- [ ] 云同步 (可选)
- [ ] 打包发布

## 参考资源

- [Tauri 官方文档](https://tauri.app/)
- [Live2D Cubism SDK](https://docs.live2d.com/)
- [pixi-live2d-display](https://github.com/guansss/pixi-live2d-display)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
