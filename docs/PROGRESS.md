# PROGRESS.md —— 工程进度台账

> 每个 Phase 结束必须更新本文件（见 AGENTS.md 第 8 节「完成定义」第 6 条）。
> 跨会话续作时，AI 助手先读本文件恢复上下文，再决定下一步动作。

## 当前状态

- **当前 Phase**：全部 7 个 Phase 完成（可交付 / 可答辩）
- **最近更新**：2026-09-20
- **服务状态**：后端 8000 / 前端 5173，可用 `start.bat` 一键拉起

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
backend : pytest -v                       → 85 passed（覆盖算法/认证/业务/权限/缓存）
backend : ruff check app tests            → All checks passed!
frontend: npm run test                    → Test Files 2 passed (2), Tests 14 passed (14)
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
