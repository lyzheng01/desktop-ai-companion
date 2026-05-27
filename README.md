# Desktop AI Companion - 桌面 AI 伙伴

一个住在桌面上的 AI 小伙伴，提供聊天、提问和轻陪伴体验。

## 当前正式架构

- 桌面壳: Tauri
- 前端渲染: Vite + TypeScript + PixiJS + Live2D
- 后端服务: FastAPI
- 本地存储: SQLite + JSON 配置
- 账号/会员/支付: MySQL

## 当前仓库状态

- `tauri-app/` 是主前端与桌面入口
- `backend/server.py` 是主 API 服务入口
- `app/` 目录中的 PyQt6 代码当前仅保留为早期原型参考，不作为正式运行链路

## 核心功能

1. 桌面常驻角色窗口
2. Live2D 角色渲染与基础交互
3. 聊天窗口与 AI 回复
4. 本地聊天记录存储
5. 本地配置持久化

## 项目结构

```text
desktop-ai-companion/
├── tauri-app/                 # Tauri + Web 前端
│   ├── src/                   # TypeScript 源码
│   ├── index.html             # 主页面
│   └── src-tauri/             # Tauri Rust 代码
├── backend/                   # Python FastAPI 后端
│   ├── server.py              # API 入口
│   └── requirements.txt
├── app/                       # 早期 PyQt 原型与可复用持久化模块
│   ├── config.py              # JSON 配置读写
│   ├── db.py                  # SQLite 读写
│   └── ui/                    # 原型界面组件
├── assets/                    # Live2D 模型与角色资源
├── data/                      # 本地配置和数据库
├── tests/                     # 自动化测试
└── docs/                      # 设计与实施文档
```

## 开发启动

## 业务后端环境变量

账号、会员、支付接口依赖 MySQL，至少需要配置：

```bash
DESKTOP_AI_COMPANION_MYSQL_HOST=127.0.0.1
DESKTOP_AI_COMPANION_MYSQL_PORT=3306
DESKTOP_AI_COMPANION_MYSQL_USER=root
DESKTOP_AI_COMPANION_MYSQL_PASSWORD=your-password
DESKTOP_AI_COMPANION_MYSQL_DATABASE=desktop_ai_companion
DESKTOP_AI_COMPANION_AUTH_SECRET=change-me
```

当前短信和微信支付先提供 `mock` provider 骨架，后续可替换成腾讯短信和微信支付正式接入：

```bash
DESKTOP_AI_COMPANION_SMS_PROVIDER=mock
DESKTOP_AI_COMPANION_WECHAT_PAY_PROVIDER=mock
DESKTOP_AI_COMPANION_FIXED_SMS_CODE=123456
```

腾讯短信正式接入所需环境变量：

```bash
DESKTOP_AI_COMPANION_SMS_PROVIDER=tencent
TENCENTCLOUD_SECRET_ID=xxx
TENCENTCLOUD_SECRET_KEY=xxx
TENCENTCLOUD_SMS_APP_ID=xxx
TENCENTCLOUD_SMS_SIGN_NAME=你的签名
TENCENTCLOUD_SMS_TEMPLATE_ID=xxx
TENCENTCLOUD_SMS_REGION=ap-guangzhou
```

微信支付 Native 正式接入所需环境变量：

```bash
DESKTOP_AI_COMPANION_WECHAT_PAY_PROVIDER=wechat
WECHAT_PAY_MCH_ID=xxx
WECHAT_PAY_APP_ID=xxx
WECHAT_PAY_SERIAL_NO=xxx
WECHAT_PAY_PRIVATE_KEY_PEM="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
WECHAT_PAY_NOTIFY_URL=https://your-domain.example/payments/wechat/notify
WECHAT_PAY_API_V3_KEY=32byteskey
WECHAT_PAY_PLATFORM_PUBLIC_KEY_PEM="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
```

说明：

1. 本地开发可以继续用 `mock` 模式联调。
2. 生产接入微信支付时，`/payments/wechat/notify` 会做回调验签和资源解密。
3. 现在支付成功后会自动把对应订单开通或续期到 `user_memberships`。

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
python server.py
```

### 2. 启动桌面前端

```bash
cd tauri-app
npm install
npm run tauri:dev
```

## 原型说明

- `run.py` 和 `app/main.py` 仍可用于查看旧版 PyQt 原型
- 原型代码不再作为正式产品启动方式维护
- 后续主线开发应只修改 `tauri-app/`、`backend/`、`app/config.py`、`app/db.py`

## 参考资源

- [Tauri 官方文档](https://tauri.app/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [pixi-live2d-display](https://github.com/guansss/pixi-live2d-display)
- [Live2D Cubism SDK](https://docs.live2d.com/)
