<!--
提交 PR 前请把下面内容填完整。CI 门禁（ci-gate「CI 全部通过」）必须全绿才能合并 main。
规范出处：docs/分工/00-分工总览.md 第 6.5 节「每批必过门槛」+ AGENTS.md 第 8 节「完成定义」。
-->

## 变更内容

- 批次/模块：
- 一句话说明：
- 关联成员文档（docs/分工/0N-*.md）：

## 自检证据（必填：贴命令与真实结果）

- [ ] 后端 `pytest -q` → 通过 __ / __
- [ ] 后端 `ruff check .` → 无报错
- [ ] 前端 `npm run test` → 通过 __ / __
- [ ] 前端 `npm run lint`、`npm run build` → 通过
- [ ] 本地一键自检 `python scripts/precheck.py` → 全部通过

## 影响面确认

- [ ] 未改共享文件；或已改共享文件（`main.py` / `models` / `schemas` / `router/index.ts` / `api/http.ts` / `global.css`）并已请组长评审
- [ ] 接口契约未变更；或已在《00-分工总览》第 6 节同步（接口发布后只加字段不改字段）
- [ ] 未提交 `.env` / `venv/` / `node_modules/` / `dist/` / `backend/uploads/` / 模型缓存
- [ ] 涉及表结构：已同步 `sql/init.sql`、`sql/seed.sql`、`docs/03-数据库设计说明书.md`
- [ ] 已更新 `docs/PROGRESS.md`（完成项 / 验证命令 / 遗留问题 / 下一步）

## 页面/接口截图（涉及前端或接口时必填）

## 回滚方式

-
