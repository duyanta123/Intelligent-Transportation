# AGENTS.md —— AI 编程助手工作须知

本文件供 AI 编程助手（ZCode / Claude Code / Cursor 等）在本仓库工作时自动读取并严格遵守。
配套的完整需求与开发流程见仓库根目录的 `docs/` 与任务下达时的《智慧交通-项目开发Prompt.md》。

## 1. 项目概述

- **名称**：智慧交通综合管理服务平台（Smart Traffic Management & Service Platform）
- **性质**：软件工程课程作业，B/S 架构单体应用，三层分离（router → service → model），禁止引入微服务
- **角色**：`admin`（管理员）/ `officer`（交警运营）/ `user`（普通用户），RBAC + JWT 认证
- **业务模块**：用户权限、路口与信号灯配时（Webster 公式）、路况监测、车辆违章、智慧停车计费、车牌识别（HyperLPR3，CPU）、公告反馈、可视化大屏、系统仪表盘

## 2. 目录结构（固定，不得擅改）

```
smart-traffic/
├── backend/            # FastAPI 后端（app/main.py 为入口，app/routers|services|models 分层）
│   └── uploads/        # 上传图片（入场拍照/车牌识别），以 /static/uploads 静态回显，不入库
├── frontend/           # Vue3 + Vite + TS 前端（src/views|api|stores|components）
├── docs/               # 课程文档：01需求 02设计 03数据库 04测试报告 05部署手册 + demo.md 答辩动线；另含 PROGRESS.md 进度台账
├── sql/                # init.sql（建库建表）+ seed.sql（种子数据）
├── .github/            # CI 门禁/安全扫描/PR 模板/CODEOWNERS（详见 docs/分工/06-自动化检查与CI门禁.md）
├── scripts/            # 工具脚本：ci_check.py（仓库自检）、precheck.py（一键自检）、gen_seed.py
├── logs/               # 运行日志（手动重定向输出时才生成，不入库，可整目录删除）
├── .env.example        # 配置模板（键名固定，以《智慧交通-项目开发Prompt.md》附录 E 为准；真实 .env 不入库）
├── .gitignore          # 忽略 .env / venv / node_modules / dist / uploads / logs / 模型缓存等
├── start.bat / stop.bat# 一键启停脚本
├── reset-db.bat        # 一键还原种子数据（重导 init.sql + seed.sql，答辩演示前用）
└── AGENTS.md           # 本文件
```

## 3. 本机环境事实（2026-09 实测核验，写死使用）

| 项 | 值 |
|---|---|
| 系统 | Windows 11 x64；Shell 以 **Git Bash** 为主（`D:\AI\Git\bin\bash.exe`，不在 PATH），Git Bash 解决不了的 Windows 专属操作改用 **pwsh 7.6.6**（命令名 `pwsh`） |
| Node | v22.21.0（npm 10.9.4 / pnpm 11.8.0 可用） |
| Python | 3.13.9（命令名就是 `python`，不是 `python3`） |
| MySQL 8.0 | 服务名 `MySQL80`，正在运行；客户端**不在 PATH**，完整路径：`"C:/Program Files/MySQL/MySQL Server 8.0/bin/mysql.exe"` |
| Redis 5.0.14 | 服务名 `Redis`，正在运行；客户端完整路径：`"C:/Program Files/Redis/redis-cli.exe"` |
| 端口 | 前端 5173 / 后端 8000 / MySQL 3306 / Redis 6379 |
| 明确没有 | Docker、Maven/Gradle、IntelliJ、NVIDIA GPU |

## 4. 常用命令

```bash
# pip 镜像（首次配置一次，加速依赖安装）
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 后端（首次）
cd backend && python -m venv venv && source venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000        # 启动，/docs 为接口文档
pytest -v                                        # 测试（使用独立库 smart_traffic_test，禁止打正式库）
ruff check .                                     # 静态检查

# 前端（首次）
cd frontend && npm install
npm run dev                                      # 启动
npm run test                                     # vitest
npm run build                                    # 构建验证

# 数据库初始化（密码从 .env 读取，勿写死在命令文档中）
"C:/Program Files/MySQL/MySQL Server 8.0/bin/mysql.exe" -uroot -p -e "source sql/init.sql"
"C:/Program Files/MySQL/MySQL Server 8.0/bin/mysql.exe" -uroot -p smart_traffic -e "source sql/seed.sql"

# Redis 连通性
"C:/Program Files/Redis/redis-cli.exe" ping      # 期望 PONG

# 提交前自检（与 GitHub Actions 门禁同口径，五人均可执行）
python scripts/precheck.py --guard-only   # 秒级：仓库卫生 + 提交信息格式
python scripts/precheck.py                # 全量：仓库自检 + ruff + pytest + eslint + vitest + build
```

## 5. 编码规范

- **注释与所有面向用户的文案：简体中文**；标识符用英文（Python `snake_case`，TS `camelCase`，Vue 组件文件 `PascalCase.vue`）
- Python 遵守 ruff 默认规则；TypeScript strict 模式；SQL 关键字大写
- API 统一前缀 `/api/v1`，响应统一 `{code: int, message: str, data: any}`；错误用有意义的 HTTP 状态码 + code 码；业务 code 段位：`0` 成功、`1xxxx` 用户权限、`2xxxx` 交通业务、`3xxxx` 停车计费、`4xxxx` 公共服务、`9xxxx` 系统错误
- 接口清单与角色-菜单权限矩阵以《智慧交通-项目开发Prompt.md》附录 C 为准，不得擅自增删改；路口坐标、Webster 参数、流量形态参数以附录 D 为准
- 所有表带 `id`/`created_at`/`updated_at`，删除一律软删除 `is_deleted`，禁止物理 DELETE 业务数据
- **时区**：全链路 Asia/Shanghai 本地时间，数据库一律 DATETIME，禁止 UTC 与本地时间混用（防止 8 小时偏差）
- 计费、配时（Webster）、拥堵分级三个核心算法必须配单元测试且为纯函数（输入输出明确，不碰数据库）
- **Git**：提交信息格式 `type(scope): 简体中文描述`（type ∈ feat/fix/docs/test/chore/refactor）；禁止提交 `.env`、`venv/`、`node_modules/`、`uploads/`、模型缓存；格式与入库路径由 CI 自动校验（见第 8 节第 8 条）

## 6. 安全与配置红线

1. 任何密钥/密码只从 `.env` 读取（python-dotenv / Vite `import.meta.env`），仓库只提交 `.env.example`
2. 密码一律 bcrypt 存储；JWT 2 小时过期，登出 token 进 Redis 黑名单
3. Redis 只用 5.x 支持的命令（禁 ACL/Function 等 6.0+ 特性）；验证码 TTL 300s，大屏聚合缓存 TTL 8s
4. AI 推理仅限 onnxruntime CPU 版；模型下载前告知体积，失败时走"手动录入"降级路径并在文档注明
5. 禁止整段复制 GPL 协议代码；借鉴开源片段须在文件头注明出处
6. 登录限流：同一账号或同一 IP 连续失败 5 次锁定 10 分钟，失败计数与锁定状态存 Redis
7. 上传图片限制 5MB、仅 jpg/png/webp；存储目录 `backend/uploads/`，通过 `/static/uploads` 回显

## 7. 已知陷阱（Windows + Git Bash）

- **Shell 分工**：命令一律优先用 Git Bash 语法（第 4 节命令均按此编写）；`bash` 不在 PATH，AI 助手须显式调用 `"D:\AI\Git\bin\bash.exe" -c "..."`。仅当 Git Bash 解决不了时（启停 `MySQL80`/`Redis` 服务、运行验证 .bat、查端口占用/进程等 Windows 专属操作）改用 pwsh 7；注意 pwsh 下激活 venv 是 `.\venv\Scripts\Activate.ps1`，与 Git Bash 的 `source venv/Scripts/activate` 不同
- `mysql`/`redis-cli` 直接敲命令会报 command not found —— 必须用第 3 节的完整路径，或先提示用户加入 PATH
- venv 激活路径是 `venv/Scripts/activate`（不是 Linux 的 `bin/`）
- 路径拼接统一用正斜杠；写 .bat 脚本时才用反斜杠
- **.bat 文件必须保存为 CRLF 行尾 + UTF-8 无 BOM**（2026-09-20 实测修正：带 BOM 时 cmd 会把首行 `@echo off` 读成 `锘緻echo` 而报错；中文乱码靠第二行 `chcp 65001 >nul` 解决，无 BOM + CRLF 实测三种 bat 均正常）；生成 .bat 后务必实际运行一次验证；.bat 内 for 循环变量必须写 `%%P`（不能 `%P`）
- PyMySQL 连 MySQL 8 需同时安装 `cryptography`（caching_sha2_password 认证）
- **passlib 必须搭配 `bcrypt<4.1`**（bcrypt 4.1+ 与 passlib 不兼容，会在 Python 3.13 下报错），requirements.txt 中钉死版本
- python-jose 若在 Python 3.13 下出现兼容问题，允许替换为 PyJWT（需在文档中注明）
- 长时间占用端口的命令（uvicorn/npm dev）用后台方式启动，验证后提示用户如何停止

## 8. 完成定义（Definition of Done）

改动"完成"前必须逐项自检并给出真实执行证据：

1. `pytest` 全绿（累计 ≥30 用例）、`npm run test` 通过、`ruff check` 无报错
2. 后端 8000 与前端 5173 可同时启动，登录页可用三个种子账号（admin/officer/user，密码 123456）登录
3. 新增接口在 `/docs` 可见且试通；新页面无控制台 error
4. 涉及表结构变更时同步更新 `sql/init.sql`、`sql/seed.sql` 与 `docs/03-数据库设计说明书.md`
5. 阶段性任务结束输出：做了什么、验证结果、遗留问题
6. 每个 Phase 结束必须更新 `docs/PROGRESS.md`（当前 Phase / 完成项 / 验证证据 / 遗留问题 / 下一步），供跨会话续作恢复上下文
7. 提交前 `git status` 确认无 `.env`、`venv/`、`node_modules/` 等误入仓库
8. 推分支/开 PR 后确认 GitHub Actions 的两个分支保护必选检查全绿：CI 门禁汇总的「CI 全部通过」（其上游四项：仓库卫生与提交规范 / 后端 lint + 测试 / 前端 lint + 测试 + 构建 / 检测）与安全扫描的「密钥泄露扫描」；PR 描述按 `.github/PULL_REQUEST_TEMPLATE.md` 填自检证据；合入 `main` 前必须有 1 人评审（详见 `docs/分工/06-自动化检查与CI门禁.md`）
