# 终稿整合报告 · 2026-10-16

本报告保留CP-020分支融合时的测试与政策结果；后续口头同意判断、Ryde品牌适配及当前发布凭据见[CP-021补充报告](CONSENT-RYDE.md)。

用户明确授权协调助手判断分支取舍、合并GitHub分支并交付终稿。交付入口为main；本轮通过[PR #5](https://github.com/luoziming49-ops/ryde-hackathon/pull/5)整合。正式赛事提交、真实工具证明、视频及公网部署另计。

## 分支取舍

| 来源 | 终稿处理 |
|---|---|
| main / feat/S0-import-v2 | S0已在main历史中，不重复导入 |
| feat/mvp-simulation-workbench · 2b29f82 | 保留完整工作台、确定性保护、显式Live模式、模拟场景、美化UI与当前提交材料，作为内容基线 |
| feat/S1-robustness-official · 51c901f | 保留S1历史与已吸收的可靠性修复。S1b/S1c原始要求已被当前实现覆盖；原始S1c 15项测试全部通过。不以更弱的旧金额/时序校验或旧UI覆盖现有实现 |
| docs/workbuddy-structure-plan · 545cb3e | 4份新增文档均已包含；保留后续已实施版本，不回退STATUS/TASKS |
| docs/public-main-protection · 8ff121c | 纳入公开仓库、成员权限和2026-10-07保护设置的历史记录；更新协作说明的产品阶段。CP-009/010已归档，不重复添加 |

不采用旧SUBMISSION/DEVELOPMENT_PROCESS中的未核实工具归属、使用证明资格、业务量和收益宣传。沿用唯一的FORM-COPY终稿文案；不把未执行S2-lite方案引入当前范围。分支及原提交保留，未删除分支、强推或更改保护设置。

本机从远端成果分支创建release/final-submission；原开发分支267d581保留。使用经审查的当前内容作为合并基线，再选择性纳入上表有效文档；合并提交同时保留三个待整合分支的父提交，因此不是只复制文件而丢弃分支历史。

## 文件变化

生产代码与既有测试保持内容一致。改动包括README、CONTRIBUTING、提交导览/文案/脚本、要求清单、证据目录说明、T010/T011历史交接、当前任务/状态/历史记录和本报告。审查原始输出另存[附件](assets/final-release/s1c-integration-review.txt)。默认本机入口统一为http://127.0.0.1:8766。

## 实际验证

命令（在仓库根目录执行，禁用收费调用）：

```bash
OPENAI_API_KEY= LLM_API_KEY= LLM_LIVE_ENABLED=false .venv/bin/python -m pytest -o addopts= -q
```

```text
........................................................................ [ 19%]
........................................................................ [ 39%]
........................................................................ [ 59%]
........................................................................ [ 79%]
........................................................................ [ 99%]
..                                                                       [100%]
362 passed in 1.93s
```

```bash
OPENAI_API_KEY= LLM_API_KEY= LLM_LIVE_ENABLED=false .venv/bin/python -m backend.evaluate --output /tmp/ryde-final-evaluation.json
```

```text
PASS RYDE-2026-0001-success
PASS RYDE-2026-0001-rider_rejected
PASS RYDE-2026-0001-retry_success
PASS RYDE-2026-0001-provider_error
PASS RYDE-2026-0002-success
PASS RYDE-2026-0002-rider_rejected
PASS RYDE-2026-0002-retry_success
PASS RYDE-2026-0002-provider_error
PASS RYDE-2026-0003-success
PASS RYDE-2026-0003-rider_rejected
PASS RYDE-2026-0003-retry_success
PASS RYDE-2026-0003-provider_error
PASS DISP-002-success
PASS DISP-002-rider_rejected
PASS DISP-002-retry_success
PASS DISP-002-provider_error
PASS missing-base-fare
PASS missing-refund-fee
PASS unknown-arrival
PASS missing-lateness
PASS conflicting-arrival-clocks
PASS policy-missing
PASS invalid-nonfinite-fare
PASS untrusted-party-instruction
PASS gps-departure-interrupts-wait
25/25 passed; 0 failed. SIMULATION ONLY.
```

原始S1c测试在内存中以当前FastAPI TestClient执行，测试函数未改写，15 passed、0 failed。完整命令与逐项输出见附件。

本轮还用项目虚拟环境中的FastAPI TestClient检查根路由，断言HTTP 200、响应与frontend/index.html逐字节相同、包含Dispute workbench / Run simulation，且health.live_enabled为false。实际输出：

```text
Application route /: 200; exact polished frontend bytes; Simulation-only health
```

材料链接检查实际输出：

```text
{'checked_local_links': 66, 'missing': []}
```

git diff --check与git diff --exit-code 267d581 -- backend frontend tests均退出0、无输出；新整合未改变已验证的生产代码。

## 成品服务与未验证项

检查发现8766原来是本项目docs/submission的临时材料服务器，已停止该进程并在同一地址启动实际FastAPI工作台，启动输出为Application startup complete / Uvicorn running on http://127.0.0.1:8766。只开启Simulation，未调用收费模型。

浏览器此前对同一地址的已保存拒绝持续生效，页面未加载；没有使用其他地址、端口或控制方式绕过。新UI桌面/窄屏真实渲染、交互彩排与新截图仍未完成，自动回归不代替视觉验收。

至少3张真实CodeBuddy/WorkBuddy对话、团队资料、上传限制与赛事回执仍待补；不将提示词或本报告视为使用证明。本版本为终稿产品及材料，尚未正式提交比赛。

## 发布回执

远端整合提交：d9e8a8ff202cbacac0989aa2da7d64fcfe3692e0。其父提交为2b29f82（成果快照）、51c901f（S1）、545cb3e（结构计划）、8ff121c（公开/保护记录）。本机本轮合并为e753172，因GitHub对象发布方式不同而提交SHA不同，完整文件树相同。

PR #5通过正常GitHub合并接口合入main；实际返回：

```json
{"sha":"3746227d0b2473535612d38fb8c5b518705fbe68","merged":true,"message":"Pull Request successfully merged"}
```

随后实际执行：

```bash
git fetch origin
git diff --exit-code HEAD origin/main
git show -s --format='%H%n%T%n%P' origin/main
```

完整文件差异退出0、无输出。主线输出：

```text
3746227d0b2473535612d38fb8c5b518705fbe68
b95d2807f9b205fec343c439fa93ae2c215cee21
36d127da432309bec93cc9929f10ec8102dbd482 d9e8a8ff202cbacac0989aa2da7d64fcfe3692e0
```

三个来源分支对整合提交的git merge-base --is-ancestor均退出0。GitHub PR回读：#1、#3、#4、#5均为closed / merged=true；未删除其分支。

本机main已从origin/main建立跟踪，原开发分支与本轮release分支保留。后续仅追加修订20及本次已验证发布回执；最终交付ZIP从远端main生成，使用说明记录实际最终commit与SHA256。记录同步完成不表示工具证明、浏览器验收或赛事提交完成。
