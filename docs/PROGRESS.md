# PROGRESS.md —— 工程进度台账

> 每个 Phase 结束必须更新本文件（见 AGENTS.md 第 8 节「完成定义」第 6 条）。
> 跨会话续作时，AI 助手先读本文件恢复上下文，再决定下一步动作。

## 当前状态

- **当前 Phase**：全部 7 个 Phase 完成（可交付 / 可答辩）；2026-09-20 完成一轮「安全 + Bug」专项审查与修复（见下方「安全审查修复记录」）
- **最近更新**：2026-09-23（① 新增「五人分工与协作」：docs/分工 六份文档 + 10 批次 Git 交付方案；② 新增「自动化检查与 CI 门禁」：`.github` 流水线 + `scripts` 本地/远程同口径自检）
- **服务状态**：后端 8000 / 前端 5173，可用 `start.bat` 一键拉起

## 安全审查修复记录（2026-09-20，全量回归通过）

后端（12 项关键修复 + 若干加固）：
- **P0 车牌唯一键 × 软删除冲突**：删除车辆后同车牌重新登记必撞唯一索引报 500。软删除时对 plate_no 写入 `*{id}` 墓碑后缀；create/update 增加查重与 IntegrityError 兜底（新错误码 20005）
- **P1 停车并发**：入场/出场对停车场行 `with_for_update()` 行锁，防满位超卖、同车牌重复入场、used_slots 丢失更新、出场双击双结算；入场端点 async→sync
- **P1 时区归一化**：流量历史/停车记录/违章录入的时间入参统一 `to_local_naive()`（带时区按 UTC+8 转本地 naive），防止前端 toISOString 造成 8 小时偏移
- **P1 Excel 公式注入**：build_xlsx 对 `=`/`+`/`-`/`@`/Tab 开头的字符串前置 `'`
- **P1 JWT_SECRET 兜底**：正式启动时密钥缺失/为默认值直接拒绝启动（TESTING 除外）
- **P1 改密吊销**：改密写 Redis `token:pwd_floor:{uid}`，get_current_user 拒绝 iat 早于改密时间的 token
- **P2**：验证码改 Lua 原子取出即销毁（防重放）；登录失败计数无条件续 TTL（防键永存）；注册查重纳入软删用户（防唯一键 500）；LPR/上传端点 async→sync 不再阻塞事件循环；Redis 连接池加 socket 超时；验证码改 secrets 随机；上传按 magic bytes 二次校验；信号方案支持 is_active=false 停用 + 更新校验路口存在；Webster 不可行输入（12 相位）显式报错（20006）；flow/fine 等数值上界与列宽对齐；管理端改用户信息的操作日志记到管理员名下；大屏 realtime 在 Redis 故障时降级直查 DB
- 前端（6 项关键修复）：查询条件变更统一重置页码；删除当前页最后一条自动回退页码；默认时间/导出文件名改本地时间（toISOString 是 UTC）；路由守卫按已授权菜单拦直达 URL（user 角色落点改为首个授权页，修复落 dashboard 连弹 403）；http 拦截器 401 防抖 + 携 redirect 回跳、blob 响应透传，下载改走统一实例（401 可跳登录）；信号方案「启用」改 PUT（原来 POST 重复建方案）+ 轮询/初始化容错；出入场按钮防重复提交 + 车牌格式校验；lpr 预览 Blob 释放；接通「记住用户名」
- 回归证据：`pytest` **119 passed**（新增 14 个回归用例，覆盖车牌复用/验证码一次性/改密吊销/公式注入/图片嗅探/时区/Webster 不可行）、`ruff check` 通过、`npm run test` 14 passed、`eslint` 0 问题、`npm run build` ✓；真实服务冒烟：health up、三角色登录成功、user 访问 admin 接口 403、无 token 401、大屏 200
- 注意：错误码 20005（车牌重复）为新增；前端 signal-plans「启用」行为已从"新建"改为"更新"，不再产生重复方案

## 第二轮收尾（2026-09-20 08:15-08:40，清掉全部遗留）

- **请求竞态防护**：新增 `utils/async.ts` sequenceGuard，应用到 10 个列表/查询页（users/vehicles/violations/records/logs/feedback/notices/flow/intersections/sections）——快速切换筛选/翻页时旧响应不再覆盖新结果
- **剩余页面 UX**：intersections/sections/fee-rules/menus/notices 的确认框取消不再产生未处理 rejection，保存按钮加 `:loading` 防重复提交（roles 页为只读，无需处理）
- **浏览器 GUI 端到端实测**（真实前后端 + 内置浏览器）：
  - admin 登录（含验证码识别）→ 仪表盘 KPI/图表/日志全渲染
  - 信号配时页「启用」实测：方案总数保持 11 不变（修复前 POST 会重复建方案），同路口旧方案自动停用 ✓
  - 车辆管理实测 P0 修复：登记京B8Z888 → 删除 → 同车牌重新登记成功（修复前 500），测试数据已清理 ✓
  - user 角色实测路由守卫：登录后落 `/big-screen`（首个授权页，修复前落 dashboard 连弹 403）；直达 `/system/users` 被重定向；授权页 `/service/feedback` 正常进入 ✓
  - 数据大屏 7 组件全部渲染 ✓；会话期间前后端日志零异常
- **新增前端单测**：`tests/utils.spec.ts`（datetime 本地时间/async 竞态防护），`npm run test` **18 passed**、eslint 0、build ✓；后端最终 `pytest` 119 passed + ruff 通过
- **导出下载 GUI 实测**：违章页「导出 Excel」点击后浏览器 download 事件正常触发（重写后的 download.ts 走统一 http 实例 + blob 透传链路可用）；登录后按 `?redirect=` 参数自动回到原页面也已实测 ✓（注：验证码 OCR 两次失败恰好验证了登录失败计数与表单自动刷新验证码行为，未触发锁定）
- **第三轮清扫（08:37-08:42）**：LEVEL_NAMES 索引越界防御（traffic/dashboard 加 `_level_name` 钳位）；大屏 10s 轮询加序号竞态防护（旧响应不覆盖新数据）；01-需求文档同步 20005 错误码与车牌墓碑规则。最终全量回归：pytest **119 passed**、ruff ✓、eslint 0、vitest **18 passed**、build ✓


## Phase 进度总览

| Phase | 内容 | 状态 |
|---|---|---|
| Phase 0 | 环境自检 | ✅ 完成 |
| Phase 1 | 工程初始化与数据库 | ✅ 完成 |
| Phase 2 | 后端开发 | ✅ 完成 |
| Phase 3 | 前端开发 | ✅ 完成 |
| Phase 4 | 联调与端到端验证 | ✅ 完成 |
| Phase 5 | 课程文档 | ✅ 完成 |
| Phase 6 | 一键演示 | ✅ 完成 |

## 五人分工与协作（2026-09-23）

- **分工文档（新增，README 已挂链接）**：`docs/分工/00-分工总览.md`（五人分工总表/模块-人员映射/54 接口契约/18 表归属/统一规范/Git 协作与分批次方案）+ 五份成员文档 `01-陈硕-项目基建与认证权限.md`、`02-郭佳豪-路口信号与路况监测.md`、`03-程靖超-车辆与违章管理.md`、`04-李嘉诚-智慧停车与车牌识别.md`、`05-左栋升-公众服务与数据大屏及交付.md`；
- **远端仓库**：<https://github.com/duyanta123/Intelligent-Transportation>（本地 `.git` 已建、`origin` 已配置；推送需在能访问 github.com 的网络环境执行）；
- **命令清单**：`docs/分工/Git提交命令清单.md`（五人各自的分支+提交+验收+PR 全流程，含 10 批次逐批 `git add` 清单）；
- **提交策略**：五名成员各用自己的 GitHub 账号提交（author 由本地 `user.name/user.email` 决定，需匹配账号邮箱）；按 **10 个批次**分阶段推送，每批一个可运行状态：①基建(陈硕) ②认证权限(陈硕) ③交通(郭佳豪) ④违章(程靖超) ⑤停车+LPR(李嘉诚) ⑥公众服务(左栋升) ⑦大屏(左栋升) ⑧测试(全组) ⑨文档(陈硕统稿) ⑩一键交付(左栋升)；
- **联动关系**：③④⑤⑥ 依赖 ①② 已合入 `main`；⑦ 依赖 ③（流量数据）与 ⑤（停车占用）；⑧⑨⑩ 在各业务批次合并后收口；共用文件（`utils/validators.py` 等）改动先后见各成员文档"分批次提交清单"；
- **本轮验证**：`pytest` **119 passed**（实测 32.59s）；vitest 18 例静态核对通过（本次审查环境 spawn 受限，未现场复跑）；6 份分工文档代码块全部配平、36 处行数标注与实现一致、数字与代码逐项对账。

## 自动化检查与 CI 门禁（2026-09-23）

- **目标**：五人在线协作时，把《00-分工总览》第 6.5 节的"每批必过门槛"从"各自跑一遍"变成**远程强制关口**——PR 不全绿不许合入 `main`。
- **新增文件**：
  - `.github/workflows/ci.yml`：`repo-guard`（仓库卫生 + 提交信息）、`backend`（ruff + pytest；CI 内起 MySQL 8.0 / Redis 5 服务容器，独立测试库 `smart_traffic_test`）、`frontend`（npm ci + eslint + vitest + build）、`ci-gate`（汇总为唯一必选检查「CI 全部通过」）；
  - `.github/workflows/security.yml`：gitleaks 密钥扫描（阻断；另含每周一 06:00 定时全量）+ pip-audit / npm audit（仅提示不阻断）；
  - `.gitleaks.toml`：放行模板与课程文档中的示例值（真实密钥仍会拦下）；
  - `.github/PULL_REQUEST_TEMPLATE.md`：PR 必填自检证据 / 影响面 / 回滚方式（对齐 AGENTS.md 第 8 节）；
  - `.github/CODEOWNERS`：共享文件、`sql/`、`docs/`、`.github/`、`scripts/` 自动指派组长评审；
  - `.github/dependabot.yml`：pip / npm 每周一 09:30、GitHub Actions 每月自动提升级 PR（提交信息 `chore(deps)`，同样过门禁）；
  - `scripts/ci_check.py`：本地与 CI 共用的仓库卫生规则（禁止入库路径 / 单文件 5MB / 硬编码密钥 / `.bat` 编码 CRLF+无 BOM+`chcp 65001` / 配置项与 `.env.example` 对账 / 提交信息格式），带 `--self-test` 规则自测；
  - `scripts/precheck.py`：一键自检（`--guard-only` 秒级；全量 = 仓库自检 + ruff + pytest + eslint + vitest + build）；
  - `scripts/remote-branch-protection.json`：`main` 分支保护的 `gh api` 载荷（Require PR 1 人评审 + 必选检查「CI 全部通过」）；
  - `.gitattributes`：显式行尾策略（文本一律 LF、`*.bat`/`*.cmd` 强制 CRLF），并顺带修掉历史遗留——`stop.bat` 在仓库中的行尾是 **CR CR LF（重复回车）**，`start.bat`/`reset-db.bat` 则是"存储 LF、靠本机 `autocrlf` 才在 Windows 上变成 CRLF"，三者现已统一为"仓库内 LF、任何平台检出均为 CRLF"；
  - `docs/分工/06-自动化检查与CI门禁.md`：检查项总览 / 本地与远端用法 / 一次性配置步骤 / 常见红灯自救 / 扩展方式。
- **本轮验证（2026-09-23 实测）**：
  - `python scripts/ci_check.py` → 120 个已跟踪文件全量扫描：0 阻断、0 提示（含 3 个 `.bat` 编码合规）；
  - `python scripts/ci_check.py --self-test` → **33 个样本全部符合预期**（违规样本被抓、正常写法不误伤）；
  - 失败路径实测：`--max-file-mb 0.05` 命中 2 个超大文件并返回**退出码 1**（证明检查并非"永远绿灯"）；
  - `python scripts/precheck.py` → 6 项全绿：仓库自检 1.2s / ruff 通过 / pytest **119 passed** 27.6s / eslint 0 问题 / vitest **18 passed** / build ✓（总耗时 52.5s）；
  - 行尾问题实测：`stop.bat` 修复前后 680B（CR CR LF×17）→ 663B（CRLF×17），三个 `.bat` 现均为 `i/lf + w/crlf + attr/text eol=crlf`（`git ls-files --eol` 核验）；
  - `.github` 三份 YAML 经 PyYAML 解析通过，作业结构核对无误：`repo-guard`、`backend`（services: mysql + redis）、`frontend`、`ci-gate`（needs 前三者）。
- **推送准备（2026-09-23 已完成，等网络可用时执行）**：
  - 骨架提交已备好：分支 `chore/ci-bootstrap` → commit `845f1eb`（**根提交**，仅 12 个自动化文件：`.github/`、`.gitattributes`、`.gitleaks.toml`、`scripts/ci_check.py`、`scripts/precheck.py`、`scripts/setup_remote.sh`、`scripts/remote-branch-protection.json`、`docs/分工/06-自动化检查与CI门禁.md`），**不含** `backend/`、`frontend/`、`sql/`、课程文档等项目主体；
  - 一键推送脚本 `scripts/setup_remote.sh`：两道安全阀（远端 `main` 已有提交则拒绝推送、网络不通给出明确报错），**从不使用 `--force`**；
  - 完整项目历史保留在本地 `main` 与 `archive/full-project-2026-09-23`：**不要**直接 `git push origin main`，那会把项目主体一起推上去（远端会拒绝非快进推送，属预期保护）。
- **待办（组长执行，需能访问 github.com 的网络环境）**：
  1. `bash scripts/setup_remote.sh`（等价 `git push -u origin chore/ci-bootstrap:main`）推送自动化骨架；
  2. 首次 CI 跑完后执行 `bash scripts/setup_remote.sh --protect`，或按 06 文档第 5.3 节在 Settings → Branches 勾选必选检查「CI 全部通过」+ Require PR（1 人评审）；
  3. 拿到各成员 GitHub 账号后补全 `.github/CODEOWNERS` 的模块负责人，并考虑开启 "Require review from Code Owners"；
  4. 此后每批提交：成员各自 `git clone` 远端 → 开 `feature/p{N}-{模块}` 分支 → PR 到 `main`（CI 全绿 + 1 人评审后合并）。
- **骨架态验证（2026-09-23 实测）**：把 `chore/ci-bootstrap` 克隆到临时目录（模拟"远端只有自动化文件"）→ `ci_check` 12 个文件全绿；`ci.yml` 新增 `detect` 作业，缺 `backend/requirements.txt` / `frontend/package.json` 时对应作业按 `skipped` 处理，「CI 全部通过」仍为绿；`setup_remote.sh` 三场景符合预期（远端已有提交时拒绝、URL 不可达时报网络问题、正常时先打印待推文件清单）。
- **注意**：GitHub 免费账号的**私有**仓库不支持分支保护规则（需 Pro/Team），课程作业建议仓库设为 public；若坚持私有，则说明"检查项已就绪、由 `ci-gate` 汇总"。

## 完成项

- **Phase 0**：Node 22.21 / Python 3.13.9 / MySQL 8（root 密码实测 `123456`）/ Redis 5.0.14（PONG）全部核验；`backend/.env`、`frontend/.env` 按附录 E 生成（真实 .env 不入库）。
- **Phase 1**：git 仓库初始化（main 分支）+ .gitignore；`sql/init.sql`（18 张表）与 `sql/seed.sql`（`scripts/gen_seed.py` 确定性生成，1.4 万行流量 / 520 违章 / 300 出入场 / 3 账号 bcrypt）导入并逐表计数验证。
- **Phase 2**：FastAPI 后端全模块（认证/RBAC/路口/信号/路况/车辆违章/停车/车牌识别/公共服务/大屏聚合/管理仪表盘，统一 `{code,message,data}` 响应与错误码分段）；核心算法纯函数（Webster/拥堵分级/停车计费）；APScheduler 模拟任务（MOCK_DATA_ENABLED 开关）；requirements.txt 锁版（bcrypt==4.0.1）。
- **Phase 3**：Vue3 + Vite + TS 前端全部页面（登录/布局/仪表盘/系统管理 4 页/交通 4 页/车辆违章 2 页/停车 3 页/车牌识别/公告/反馈）+ 数据可视化大屏（6 图表 + 1 地图、scale 自适应、10s 轮询、降级提示）。
- **Phase 4**：验收清单 7 项全部通过（见 docs/04-测试报告 第 5 节）；浏览器 GUI 实测三角色登录、菜单按权限渲染、大屏渲染与降级恢复。
- **Phase 5**：docs/01-05 五份课程文档（含用例图/E-R/类图/时序图 Mermaid 图，与实现一致）+ README。
- **Phase 6**：`start.bat`（双服务 + 自动开浏览器）、`stop.bat`（按端口清理）、`reset-db.bat`（还原种子）、`demo.md` 演示动线。

## 验证证据（命令 + 关键输出）

```
backend : pytest -v                       → 119 passed（覆盖算法/认证/业务/权限/缓存/大屏/导出）
backend : ruff check app tests            → All checks passed!
frontend: npm run test                    → Test Files 3 passed (3), Tests 18 passed (18)
frontend: npx eslint src tests            → 0 problems
frontend: npm run build                   → ✓ built in 12.5s
DB      : seed 导入后 16 表计数验证        → traffic_flow 13960 / violation 520 / parking_record 300 …
DB      : 早高峰形态                      → 08 时均值 1814 pcu/h、18 时 1849、凌晨 ~90
LPR     : POST /lpr/recognize（合成车牌） → {'plate_no': '鲁A12345', 'confidence': 0.9651}
大屏    : 浏览器实测 7 组件渲染 + 后端宕机降级卡片 + 恢复自动回填（截图留档会话）
Redis   : captcha:{uuid}→"SKY6"(TTL 278)、token:blacklist:{jwt}、dashboard:realtime(TTL≤8s) 均可观察
脚本    : stop.bat 实测停掉 8000/5173；start.bat 实测双服务拉起并打开浏览器
```

## 遗留问题

- 无阻塞遗留。注意事项：
  - 本机 Redis db 0 与另一套系统（若干 sys_config/sys_dict 键）共用，本项目键名均为独立前缀暂无冲突；如需彻底隔离可把 `REDIS_DB` 改为 1-15；
  - 合成车牌图片识别为「鲁A12345」（字体与真牌有差异），真实车牌照片识别效果更好；
  - HyperLPR3 模型缓存位于 `D:\Users\duyan\.hyperlpr3`（HOMEPATH 相对当前盘符，Windows 平台特性）。

## 实测经验修正（供后续会话）

- **.bat 编码**：Windows 11 (26200) 实测 cmd **不支持 UTF-8 BOM**（首行 `@echo off` 被读成 `锘緻echo` 报错）；正确做法为 **UTF-8 无 BOM + CRLF + 第二行 `chcp 65001 >nul`**。已修正 AGENTS.md 与三个 bat；bat 内 for 循环变量必须写 `%%P`。
- **MySQL DATETIME 秒级竞态**：DATETIME 写入对小数秒四舍五入，查询 `end=now()` 可能排除刚写入的行——时间上界查询预留 1 秒缓冲。
- **JWT 同秒重复**：iat 秒级精度会让同秒多次签发的 token 完全相同，payload 必须带唯一 `jti`。
- **Redis 5 + redis-py 8**：客户端默认 RESP3（HELLO 命令）不被支持，连接池需 `protocol=2`。
- **HyperLPR3**：返回格式 `[车牌, 置信度, 类型, 框]`；模型约 12MB，应在应用启动时后台预热，勿在首个请求内同步加载。

## 下一步（可选增强，非必需）

1. 大屏地图可替换为真实 GeoJSON 路网以增强视觉效果；
2. 信号配时方案可增加「方案对比」图表；
3. 可增加导出报表（Excel）功能。



