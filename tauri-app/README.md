# Tauri + Live2D 前端

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 开发模式

```bash
# 启动 Vite 开发服务器 + Tauri 窗口
npm run tauri:dev
```

### 3. 生产构建

```bash
npm run build
npm run tauri:build
```

## 项目结构

```
tauri-app/
├── src/
│   ├── main.ts           # Live2D 渲染入口
│   ├── chat-client.ts    # 聊天客户端
│   └── ui.ts             # UI 组件
├── index.html
├── package.json
├── tauri.conf.json       # Tauri 配置
└── src-tauri/            # Rust 后端
    ├── src/main.rs
    ├── Cargo.toml
    └── tauri.conf.json
```

## 技术栈

- **Tauri v2** - 桌面壳
- **PixiJS v7** - 2D 渲染引擎
- **pixi-live2d-display** - Live2D 渲染器
- **Vite** - 构建工具
- **TypeScript** - 类型安全

## 添加新角色

1. 下载 Live2D 模型到 `assets/live2d/`
2. 在 `main.ts` 中调用 `loadLive2DModel('新路径')`
3. 在右键菜单添加切换选项

## 调试技巧

- Live2D 模型加载失败会降级显示占位图形
- 按 F12 打开开发者工具 (需要在 `tauri.conf.json` 启用 devtools)
- 查看控制台日志排查模型路径问题
