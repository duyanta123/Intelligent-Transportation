# Git 提交命令清单 —— 五人可执行版

> 配套《00-分工总览.md》第 6.5 节。远端：`https://github.com/duyanta123/Intelligent-Transportation.git`，长期分支 `main`。
> 每人只执行 **"自己那一节"** 的命令；每批提交前先跑本批验证，绿了再 commit/push，最后提 PR 请陈硕合并。
> 全程使用**自己的 GitHub 账号与邮箱**（提交作者由本地 `user.name/user.email` 决定）。

**填写占位符（每人先做这一步，只改自己这一行）**

| 占位符（命令里原样出现） | 替换成什么 | 示例 | 到哪里找 |
|---|---|---|---|
| `你的姓名` | 自己的真实姓名（建议与 GitHub 用户名一致，方便核对） | `郭佳豪` | —— |
| `你的GitHub邮箱` | **自己账号已验证的邮箱**；开了邮箱隐私就用 noreply 地址 | `12345678+guojiahao@users.noreply.github.com` | GitHub → Settings → Emails（可见主邮箱与 noreply 地址） |
| `你的分支名`（如有） | 本批次对应的 `feature/p{N}-{模块}` | `feature/p2-traffic` | 本文对应批次小节 |
| `本批提交信息`（如有） | 照抄本文对应批次的 `git commit -m` | `feat(算法): Webster 配时…` | 本文对应批次小节 |

> 校验方式：配完后执行 `git config user.name` 与 `git config user.email`，输出必须与上面填写的一致；提交后在 GitHub 点自己的 commit，作者头像能跳转到自己主页即正确。
**每批次都适用的三条铁律**

1. 开工前：`git checkout main` && `git pull origin main`，再从最新 main 切分支（不要基于旧地基写代码）；
2. 提交前：先跑该批验收命令，全绿再 `git add` + `git commit`；
3. **提 PR 前**：先把自己的分支同步到最新 main（见下方《提 PR 前必做：同步 main》），再 push；
4. 提交后：`git push -u origin 分支名`，到 GitHub 提 PR → 陈硕 review 合并 → 你把本地 main 同步下来。

---

## 0. 提 PR 前必做：同步 main（分支保护要求）

仓库开了分支保护（`Require branches to be up to date before merging`）——main 有新提交后，**落后的分支无法合并**，必须先同步。两种方式任选：

```powershell
# 方式 A：merge 同步（推荐，新手友好，不会 force push）
git checkout main; git pull origin main
git checkout feature/p2-traffic      # 换成自己的分支
git merge main                       # 有冲突在本机解决，解决后 git add + git commit
git push                             # 普通 push，PR 会自动变绿可合并

# 方式 B：rebase 同步（历史更线性，但要 force push 自己的分支）
git fetch origin
git rebase origin/main
git push --force-with-lease          # 只能对自己 feature 分支用，禁止对 main 用
```

> 冲突处理原则：共享文件（schemas/main.py/router、test_service.py、test_export_upload.py 等）**保留双方内容**；谁的分支谁负责在本机解冲突，解完重跑本批验收命令再推送。

---

## 1. 通用准备（每台机器一次）

```powershell
git clone https://github.com/duyanta123/Intelligent-Transportation.git smart-traffic
cd smart-traffic

git config user.name  "你的姓名"                 # ← 把 你的姓名 换成自己的真实姓名（例：郭佳豪）
git config user.email "你的GitHub邮箱"           # ← 把 你的GitHub邮箱 换成自己账号已验证邮箱或 noreply 地址

# 后端虚拟环境 + 依赖
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env            # 填 DB_PASSWORD、JWT_SECRET
cd ..

# 前端依赖
cd frontend
npm install
cd ..

# 数据库（本机 MySQL/Redis 已启动）
mysql -uroot -p < sql/init.sql
mysql -uroot -p smart_traffic < sql/seed.sql
```

---

## 2. 陈硕（组长）—— 批次 ①②⑧⑨

### 批次 ① 基建（分支 `feature/p1-scaffold`）

```powershell
# 首次推送（仓库还没有 main 时，由你做初始化提交）
git checkout -b feature/p1-scaffold
git add backend/app/core backend/app/utils backend/app/models backend/app/schemas backend/app/main.py `
        backend/requirements.txt backend/tests/conftest.py `
        sql/init.sql scripts/gen_seed.py `
        docs/PROGRESS.md AGENTS.md .gitignore
git commit -m "chore: 工程骨架（core/公共工具/ORM 模型/统一响应与错误码/建表脚本）"
# 可再拆第二条：git commit -m "chore: 配置与安全基线（.env.example/JWT 兜底/Redis RESP2）"
git push -u origin feature/p1-scaffold
```

验收（必须全绿再 push）：

```powershell
cd backend
.\venv\Scripts\python.exe -c "from app.main import app"
.\venv\Scripts\python.exe -m uvicorn app.main:app --port 8000   # 访问 /api/v1/health 应返回 status=up
.\venv\Scripts\python.exe -m ruff check app
```

### 批次 ② 认证权限（分支 `feature/p1-auth`，基于①已合并的 main）

```powershell
git checkout main; git pull origin main
git checkout -b feature/p1-auth
git add backend/app/routers/auth.py backend/app/routers/system.py backend/app/routers/admin.py `
        backend/app/services/auth_service.py backend/app/services/oplog.py `
        backend/app/schemas/__init__.py `
        backend/tests/test_auth.py backend/tests/test_service.py `
        frontend/src/stores frontend/src/api/http.ts frontend/src/router `
        frontend/src/views/login frontend/src/views/layout frontend/src/views/system
git commit -m "feat(认证): 验证码+注册+登录（失败锁定）+JWT 黑名单与改密吊销"
git commit -m "feat(权限): 用户/角色/菜单/操作日志 + 前端登录页/主布局/路由守卫"
# 提 PR 前：按第 0 节同步最新 main（分支保护要求，防止落后分支被拒合）
git push -u origin feature/p1-auth
```

> 注意：`backend/tests/test_service.py` 里有 3 例 `TestAdminStats`（你的），其余公告/反馈/大屏用例属左栋升——你提交文件骨架时带上这 3 例即可，左栋升后续追加。

验收：

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_auth.py tests/test_service.py -v
.\venv\Scripts\python.exe -m ruff check app tests
cd ..\frontend; npm run test; npx eslint src tests
```

### 批次 ⑧⑨（你牵头，其他成员先各提各的）

```powershell
# 测试汇总（各人已在 feature/p{N}-tests 提交自己用例后）
git checkout main; git pull origin main
git checkout -b feature/p1-test-hardening
git add backend/tests frontend/tests
git commit -m "test: 全量回归（119 后端 + 18 前端）与权限矩阵核对"
git push -u origin feature/p1-test-hardening

# 文档统稿
git checkout main; git pull origin main
git checkout -b feature/p1-docs
git add docs README.md
git commit -m "docs(01-05): 课程文档与分工文档定稿（119/18 口径一致）"
git push -u origin feature/p1-docs
```

---

## 3. 郭佳豪 —— 批次 ③⑧

### 批次 ③ 交通（分支 `feature/p2-traffic`）

```powershell
git checkout main; git pull origin main
git checkout -b feature/p2-traffic
git add backend/app/routers/signal.py backend/app/routers/traffic.py `
        backend/app/services/algorithms.py backend/app/tasks backend/app/main.py `
        backend/app/schemas/__init__.py `
        backend/tests/test_algorithms.py backend/tests/test_traffic.py `
        sql/seed.sql `
        frontend/src/views/traffic frontend/src/api/traffic.ts `
        frontend/src/router frontend/src/styles/global.css
git commit -m "feat(算法): Webster 配时/拥堵分级/车速模型/流量形态纯函数"
git commit -m "feat(信号): 路口与配时方案 CRUD+计算接口+信号状态"
git commit -m "feat(路况): 路段/流量上报/拥堵榜 + 模拟任务（流量+信号+保留清理）"
git commit -m "feat(前端): 交通 4 页（路口/配时/路段/流量与拥堵）"
# 提 PR 前：按第 0 节同步最新 main（分支保护要求，防止落后分支被拒合）
git push -u origin feature/p2-traffic
```

> 与李嘉诚的分工：`services/algorithms.py` 中计费函数（`calc_parking_fee*`）与 `TestParkingFee` 归他；你提交时文件会带上，属正常共文件。

验收：

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_algorithms.py tests/test_traffic.py -v
.\venv\Scripts\python.exe -m ruff check app tests
cd ..\frontend; npm run test; npx eslint src tests
```

### 批次 ⑧ 测试补漏（分支 `feature/p2-tests`）

```powershell
git checkout main; git pull origin main
git checkout -b feature/p2-tests
git add backend/tests/test_export_upload.py backend/tests/test_algorithms.py
git commit -m "test(交通): 补流量保留策略与算法边界用例"
git push -u origin feature/p2-tests
```

> 共享文件规则：`test_export_upload.py` 你只补 `TestFlowRetention` 两个用例，其余类归程靖超/李嘉诚。

---

## 4. 程靖超 —— 批次 ④⑧

### 批次 ④ 违章（分支 `feature/p3-violation`）

```powershell
git checkout main; git pull origin main
git checkout -b feature/p3-violation
git add backend/app/routers/violation.py backend/app/routers/export.py `
        backend/app/services/excel_service.py backend/app/utils/validators.py `
        backend/app/schemas/__init__.py `
        backend/tests/test_violation.py backend/tests/test_pure_utils.py backend/tests/test_export_upload.py `
        frontend/src/views/vehicle frontend/src/api/vehicle.ts frontend/src/api/download.ts `
        frontend/src/router
git commit -m "feat(车辆): 车牌校验/车辆 CRUD/软删墓碑复用"
git commit -m "feat(违章): 录入/审核/处理状态机 + 类型字典 + 取证上传"
git commit -m "feat(导出): 三类 Excel 报表（表头冻结/自动列宽/公式注入防护）"
git commit -m "feat(前端): 车辆与违章两页（审核弹窗/导出按钮）"
# 提 PR 前：按第 0 节同步最新 main（分支保护要求，防止落后分支被拒合）
git push -u origin feature/p3-violation
```

> 你负责 `test_export_upload.py` 的骨架 + `TestExcelExport`（4 例）+ `TestExcelFormulaSanitize`（1 例）；`TestImageUpload` 由李嘉诚后续追加、`TestFlowRetention` 由郭佳豪后续追加。

验收：

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_violation.py tests/test_pure_utils.py -v
.\venv\Scripts\python.exe -m pytest tests/test_export_upload.py -v -k "Excel"
.\venv\Scripts\python.exe -m ruff check app tests
cd ..\frontend; npm run test; npx eslint src tests
```

### 批次 ⑧ 测试补漏（分支 `feature/p3-tests`）

```powershell
git checkout main; git pull origin main
git checkout -b feature/p3-tests
git add backend/tests/test_violation.py backend/tests/test_export_upload.py
git commit -m "test(违章): 补车牌墓碑复用与导出列位断言"
git push -u origin feature/p3-tests
```

---

## 5. 李嘉诚 —— 批次 ⑤⑧

### 批次 ⑤ 停车+LPR（分支 `feature/p4-parking`）

```powershell
git checkout main; git pull origin main
git checkout -b feature/p4-parking
git add backend/app/routers/parking.py backend/app/routers/lpr.py backend/app/routers/files.py `
        backend/app/services/lpr_service.py backend/app/services/algorithms.py `
        backend/app/utils/upload.py backend/app/utils/validators.py `
        backend/app/schemas/__init__.py `
        backend/tests/test_parking.py backend/tests/test_export_upload.py backend/tests/test_algorithms.py `
        frontend/src/views/parking frontend/src/views/tools frontend/src/api/parking.ts `
        frontend/src/api/dashboard.ts frontend/src/router
git commit -m "feat(计费): 分时段计费纯函数（免费/首小时/每小时/单日封顶）"
git commit -m "feat(停车): 停车场与计费规则 CRUD + 入场/出场结算（行锁防超卖）"
git commit -m "feat(识别): HyperLPR3 预热与识别接口 + 通用上传（magic bytes 校验）"
git commit -m "feat(前端): 停车场/出入场/计费规则/车牌识别四页"
# 提 PR 前：按第 0 节同步最新 main（分支保护要求，防止落后分支被拒合）
git push -u origin feature/p4-parking
```

> 共文件规则：`utils/validators.py` 你只用到车牌函数（程靖超先提交）；`test_algorithms.py` 你追加 `TestParkingFee` 8 例；`test_export_upload.py` 你追加 `TestImageUpload` 3 例。

验收：

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_parking.py -v
.\venv\Scripts\python.exe -m pytest tests/test_algorithms.py -v -k ParkingFee
.\venv\Scripts\python.exe -m pytest tests/test_export_upload.py -v -k Upload
.\venv\Scripts\python.exe -m ruff check app tests
cd ..\frontend; npm run test; npx eslint src tests
```

### 批次 ⑧ 测试补漏（分支 `feature/p4-tests`）

```powershell
git checkout main; git pull origin main
git checkout -b feature/p4-tests
git add backend/tests/test_parking.py backend/tests/test_export_upload.py
git commit -m "test(停车): 补时间筛选与上传失败路径用例"
git push -u origin feature/p4-tests
```

---

## 6. 左栋升 —— 批次 ⑥⑦⑩

### 批次 ⑥ 公众服务（分支 `feature/p5-service`）

```powershell
git checkout main; git pull origin main
git checkout -b feature/p5-service
git add backend/app/routers/service.py backend/tests/test_service.py `
        frontend/src/views/service frontend/src/api/service.ts frontend/src/router
git commit -m "feat(公告): 发布/编辑/下架（user 只见已发布）"
git commit -m "feat(反馈): 提交/受理/办结状态机 + 前端两页"
# 提 PR 前：按第 0 节同步最新 main（分支保护要求，防止落后分支被拒合）
git push -u origin feature/p5-service
```

### 批次 ⑦ 大屏（分支 `feature/p5-dashboard`，等③⑤⑥合并后）

```powershell
git checkout main; git pull origin main
git checkout -b feature/p5-dashboard
git add backend/app/routers/dashboard.py backend/app/main.py `
        backend/tests/test_service.py `
        frontend/src/views/bigscreen frontend/src/views/dashboard `
        frontend/src/api/dashboard.ts frontend/src/stores frontend/src/router `
        frontend/tests/utils.spec.ts
git commit -m "feat(大屏): realtime 聚合（趋势/散点/路网/信号/TOP5/占用/KPI）"
git commit -m "perf(大屏): Redis 缓存 TTL8s + 故障降级直查 DB"
git commit -m "feat(前端): 大屏 scale 自适应 + 10s 轮询 + 断连提示"
# 提 PR 前：按第 0 节同步最新 main（分支保护要求，防止落后分支被拒合）
git push -u origin feature/p5-dashboard
```

> `test_service.py` 里 `TestAdminStats` 3 例是陈硕的，你只追加 `TestNotice`/`TestFeedback`/`TestDashboard` 用例。

验收：

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_service.py -v
.\venv\Scripts\python.exe -m ruff check app tests
cd ..\frontend; npm run test; npx eslint src tests; npm run build
```

### 批次 ⑩ 一键交付（分支 `feature/p5-delivery`，最后做）

```powershell
git checkout main; git pull origin main
git checkout -b feature/p5-delivery
git add start.bat stop.bat reset-db.bat demo.md sql/seed.sql scripts/gen_seed.py README.md
git commit -m "chore(交付): 一键启停/重置脚本 + 演示动线与种子刷新"
git push -u origin feature/p5-delivery
```

验收：

```powershell
.\start.bat                 # 浏览器自动打开登录页
.\reset-db.bat              # 要 data 还原到种子状态
# 按 demo.md 走一遍 8 分钟动线
```

---

## 7. 进度跟踪表（打印出来贴墙上）

| 批次 | 负责人 | 分支 | 状态 | PR 链接 | 合并时间 |
|---|---|---|---|---|---|
| ① 基建 | 陈硕 | feature/p1-scaffold | ☐ | | |
| ② 认证权限 | 陈硕 | feature/p1-auth | ☐ | | |
| ③ 交通 | 郭佳豪 | feature/p2-traffic | ☐ | | |
| ④ 违章 | 程靖超 | feature/p3-violation | ☐ | | |
| ⑤ 停车+LPR | 李嘉诚 | feature/p4-parking | ☐ | | |
| ⑥ 公众服务 | 左栋升 | feature/p5-service | ☐ | | |
| ⑦ 大屏 | 左栋升 | feature/p5-dashboard | ☐ | | |
| ⑧ 测试 | 全组 | feature/p{N}-tests → p1-test-hardening | ☐ | | |
| ⑨ 文档 | 陈硕 | feature/p1-docs | ☐ | | |
| ⑩ 一键交付 | 左栋升 | feature/p5-delivery | ☐ | | |

---

## 8. 红线与常见问题

- **绝不 force push `main`**；`main` 只通过 PR 合入；
- **GitHub 分支保护（陈硕配置一次）**：仓库 → Settings → Branches → Add branch protection rule → 分支名填 `main` → 勾选：**Require a pull request before merging**（Approvals 建议 1）、**Require branches to be up to date before merging**（重要）、可选 **Do not allow bypassing the above settings** → 保存。新版界面在 Settings → Rules → Rulesets 同义配置。
- **为什么必须勾 up to date**：并行批次改共享文件时，若分支落后于 main 仍允许合并，Git 不报冲突但后合者会**覆盖**先合者的改动（静默丢代码）。勾上后分支必须先同步 main 才可合并，配合第 0 节《提 PR 前必做：同步 main》操作使用。
- **注意**：免费私有仓库可能不提供分支保护，此时把仓库设为 Public，或用"口头约定 + 每次 push 前 `git pull`"兜底；Approvals=1 时陈硕自己的 PR 无法自批，需组员互批或临时取消该勾选。
- 提交前 `git status` 检查，**不要把 `backend/.env`、`backend/uploads/*`、`node_modules`、`venv` 提交进去**（`.gitignore` 已挡，但 `git add -A` 前仍确认一次）；
- 共享文件（`schemas/__init__.py`、`test_service.py`、`test_algorithms.py`、`test_export_upload.py`、`views/*` 的路由配置等）：后提交的人先 `git pull origin main` 再追加，冲突时保留双方内容；
- 每批验收命令必须全绿才提 PR；PR 描述里写上"本批验收命令 + 输出摘要"；
- 如果 push 报 403：确认自己已被加为仓库 Collaborator（Write）且已登录正确账号；如果作者头像没挂上：检查 `git config user.email` 是否与账号邮箱一致。







