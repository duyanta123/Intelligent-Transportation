# PROGRESS.md —— 工程进度台账

> 每个 Phase 结束必须更新本文件（见 AGENTS.md 第 8 节「完成定义」第 6 条）。
> 字段固定：当前 Phase、完成项、验证证据（命令 + 关键输出）、遗留问题、下一步。
> 跨会话续作时，AI 助手先读本文件恢复上下文，再决定下一步动作。

## 当前状态

- **当前 Phase**：Phase 3 前端开发（进行中）
- **最近更新**：2026-09-20

## Phase 进度总览

| Phase | 内容 | 状态 |
|---|---|---|
| Phase 0 | 环境自检 | ✅ 完成 |
| Phase 1 | 工程初始化与数据库 | ✅ 完成 |
| Phase 2 | 后端开发 | ✅ 完成 |
| Phase 3 | 前端开发 | 进行中 |
| Phase 4 | 联调与端到端验证 | 未开始 |
| Phase 5 | 课程文档 | 未开始 |
| Phase 6 | 一键演示 | 未开始 |

## 完成项

- 三份指导文档已审查并补全：《智慧交通-项目开发Prompt.md》（新增附录 C 接口清单与权限矩阵、附录 D 固定模拟参数、附录 E 配置与错误码约定；修正附录 A 为 Spring Boot 4.x）、`smart-traffic/AGENTS.md`（补 Git 规范、依赖钉版、时区约定等）
- 两份 AGENTS.md 补充 Shell 分工约定（2026-09-20 实测）：Git Bash 为主（`D:\AI\Git\bin\bash.exe`，不在 PATH），Windows 专属操作兜底用 pwsh 7（7.6.6）
- 已创建 `docs/PROGRESS.md`（本文件）与 `reset-db.bat`（数据一键还原脚本，待 Phase 1 产出 sql 文件后可用）

## 验证证据

（暂无。格式：命令 + 关键输出摘录）

## 遗留问题

- MySQL root 密码尚未提供，Phase 0 数据库连通性验证前需填写到 `backend/.env`
- `sql/init.sql`、`sql/seed.sql`、`backend/.env` 均未生成，属 Phase 1 工作

## 下一步

1. 提供 MySQL root 密码，按《智慧交通-项目开发Prompt.md》附录 E 模板创建 `backend/.env`
2. 执行 Phase 0 环境自检并粘贴真实输出
