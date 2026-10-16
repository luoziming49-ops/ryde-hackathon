# T012 进度核验与结构优化交接

2026-10-07 · 基线：本地修订 10；远端 main 36d127da432309bec93cc9929f10ec8102dbd482；S1 6d7ad6dc568db4b2a91fa4a28f4cbbfb1114dfd4。

状态：核验与方案完成。负责人：协调助手；研究与代码审查子 agent 仅只读回传，协调者维护总状态。产品实现由后续 WorkBuddy 任务执行；文档同步状态以 STATUS 为准。

用户要求检查当前进度、上网找开源项目借鉴、优化现有项目结构，并提供 WorkBuddy 执行提示词。此次交付为核验记录、最小增量结构设计和可执行任务包；产品代码由 WorkBuddy 后续执行。

读取范围：远端 AGENTS、STATUS、SPRINT、PROJECT_RULES、S1 与相关代码和测试；本地 WORKFLOW 交接协议。可写：本任务、来源记录、结构建议、WorkBuddy 任务包、README、STATUS、TASKS、LOG；不改产品代码、仓库设置，不合并他人 PR。

验收：分清已合并/分支实现/未验证；开源链接有实际核验；方案保持 FastAPI 与确定性计算；提示词包含基线、范围、依赖、停止条件和真实验收；核验文档链接、入口预算与敏感信息。

## 当前进度与依据

| 对象 | 核验结果 |
|---|---|
| [仓库](https://github.com/luoziming49-ops/ryde-hackathon) | GitHub 元数据为 public；main protected=true，不重新核验或更改管理员保护配置 |
| [S0 PR #2](https://github.com/luoziming49-ops/ryde-hackathon/pull/2) | 2026-10-07 19:51（Asia/Singapore）已合并；main 为 36d127d，已有产品代码和实施授权记录 |
| [S1 PR #3](https://github.com/luoziming49-ops/ryde-hackathon/pull/3) | 作者 unknownAndy123；head 6d7ad6d，open、未合并。分支有适配器与健壮性修改，PR 正文仍是未填写的模板；不能把分支实现写成主线已交付 |
| [旧 PR #1](https://github.com/luoziming49-ops/ryde-hackathon/pull/1) | 仍 open，包含旧阶段记录；本轮不合并。处理其冲突时只保留仍有效的协作配置，不能覆盖新的实施阶段 |
| GitHub Actions | 核验时 runs=0，没有远端 CI 通过证据；本轮测试在隔离环境实际运行 |
| 本地工作目录 | 原为修订10文档副本，未包含远端代码。本轮下载准确 S1 提交的36份产品/测试文件到临时目录，只为审查和测试；未将其混入文档根目录 |

main 的 STATUS 仍写 private，TASKS 仍有旧 P0/构思待办；已在本轮文档记录纠正。远端已有实施授权记录，本轮用户要求由助手负责规划、WorkBuddy执行；不重新追问已选定的产品方向，也不把此轮建议当作全部功能已实施。

## 实际验证

环境为 Python 3.12.14，安装项目现有 requirements-dev.txt；FastAPI 0.110.0、pytest 8.2.2、httpx 0.27.0，解析得到 Pydantic 2.13.5。没有调用真实云模型。快照没有读取用户 .env。

实际工作目录为 `/private/tmp/ryde-audit-20261007`；运行命令：

```sh
env -u OPENAI_API_KEY -u LLM_API_KEY /private/tmp/ryde-audit-venv/bin/python -m pytest -o addopts= -q
```

原始输出：

```text
........................................................................ [ 91%]
.......                                                                  [100%]
79 passed in 0.17s
```

另用 FastAPI TestClient 进入 lifespan，调用 health、首页、四案 resolve；原始摘要：

```text
health: no_key
home: 200
RYDE-2026-0001 200 {'action': 'partial_refund', 'amount': 7.87, 'confidence': 0.96, 'escalated': False}
RYDE-2026-0002 200 {'action': 'full_refund', 'amount': 5.0, 'confidence': 0.98, 'escalated': False}
RYDE-2026-0003 200 {'action': 'no_action', 'amount': 0.0, 'confidence': 0.95, 'escalated': False}
DISP-002 200 {'action': 'no_action', 'amount': 0.0, 'confidence': 0.95, 'escalated': False}
malformed official ticket: 500 {'detail': 'Internal server error'}
```

最后一行输入为 `{"dispute_ticket":"broken"}`，证实全局异常 JSON 不等于有效输入校验。首页 200 只证明文件可提供，不证明浏览器操作通过。

## 新发现及优先级

下列行号均基于 S1 6d7ad6d；不代表正在变动的 main 行号。

| 问题 | 证据和影响 | 处理批次 |
|---|---|---|
| 官方输入绕过内部验证 | main.py:120–122；adapters/official_ticket.py 对嵌套数据直接 .get。上述反例返回 500 | WB01 |
| 缺费用变零元成功退款 | core/evidence.py:241–243 等把缺失值当0；本轮实测删除0001的base/distance费用后 partial_refund 0.0、未升级；删除0002取消费后 full_refund 0.0、未升级 | WB01 |
| 官方时间回退与边界 | adapters/official_ticket.py:152–155 接收 arrival_time 却未使用；evidence.py:306 在 arrived=false 且无距离时格式化 None。子 agent 用输入副本复现 | WB01 |
| 官方案例页面字段不匹配 | frontend/index.html:318–323 无条件 toFixed，但 adapter 不提供全部费用；子 agent Node 表达式复现 TypeError。未做浏览器视觉验收 | WB01 |
| 模型文字与裁决矛盾 | judge.py:146–162 自由文字直出；本轮 Mock 完整 resolve 实测3次调用，结构化金额7.87保持正确，但 reasoning 原样显示 Full refund SGD 9999 under FAKE-001 | WB02 |
| 引用缺少可核验链 | evidence.py 聚合字段无 evidence_id；双方 prompt 未包含实际政策正文，Judge 主要收到双方自然语言。属于静态代码核验，不等于已发生真实模型幻觉 | WB02 |
| 日志和模式展示不完整 | trace 无逐调用模式/版本；index.html:382–401 是处理完成后的260ms动画；:447 读取旧 health 字段。不能宣称实时流或三个模型调用均成功 | WB02–03 |

补充：三个角色都已有 LLM 入口，不能说“完全没接 AI”；Mock 调用只能证明路径，不证明真实 API 或模型质量。当前金额由确定性规则决定，下一步需要保护最终说明及引用，而非把金额决定权交给 LLM。官方 adapter 仅映射 no_show_charge，内部两类流程已可运行；不能宣称两类官方格式均覆盖。

## 交付与未完成项

- [开源机制来源](../sources/2026-10-07-open-source-patterns.md)：6个相关项目及取舍，核心采用模式而不安装框架。
- [结构建议](../ideas/2026-10-07-structure.md)：模块职责、数据契约、阶段、展示和验收方向。
- [WB01](WB01-reliability.md)：第一轮具体文件范围、失败测试、修复顺序和交回报告。
- README、STATUS、TASKS 与 LOG 更新导航、现状和交接；未改产品代码，未合并PR、部署或更改仓库权限。
- 36份审查快照逐份以Git blob SHA核对；文档交接复核补充了测试网络隔离和双方代理可提出相反主张的边界。共享文档本地链接与入口预算检查通过，远端发布后按完整内容回读。
- 尚未完成：WB01修复、真实LLM试跑、浏览器端到端、实时事件、部署验证、截图与提交材料验收；赛事截止日期和 official 样例原始出处本轮未重新核验。

协调方式：用户把 WB01 发给 WorkBuddy；它仅执行本轮并交回 REPORT/差异；我根据证据验收再安排 WB02。没有自动连接 WorkBuddy 或后台监控，用户转交结果才开始下一轮。
