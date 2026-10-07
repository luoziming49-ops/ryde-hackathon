# 活动任务索引

仅列未完成任务；基线与当前进度由 [STATUS](STATUS.md) 和所属任务维护。

| ID | 状态 | 负责人 | 依赖与入口 |
|---|---|---|---|
| S1 | 分支已有实现，PR待合并及缺口修复 | PR #3 作者 unknownAndy123；协调助手审查 | [PR #3](https://github.com/luoziming49-ops/ryde-hackathon/pull/3)，本轮核验见 [T012](tasks/T012-structure-handoff.md) |
| WB01 | 已形成任务包，待用户交给执行器 | WorkBuddy执行，协调助手验收 | 在核对S1基线后进行 [可靠性收尾](tasks/WB01-reliability.md)，不改同伴分支 |
| T004 | 仅核实当前资源增量 | 用户提供，协调助手记录 | [资源任务](tasks/T004-resources.md)；真实API额度与可用性不得由开发工具积分推定 |
| T011 | 旧配置记录PR待核对 | 协调助手与成员 | [任务记录](tasks/T011-branch-protection.md) / [PR #1](https://github.com/luoziming49-ops/ryde-hackathon/pull/1)；不得覆盖新实施阶段 |

WB02–WB04 是 [结构建议](ideas/2026-10-07-structure.md) 中的后续顺序，未作为并行任务下达。WB01回传后再按验收结果细化。T005/T006/T009的旧“未选方向”状态已被远端实施记录替代，保留历史，不重复启动。
