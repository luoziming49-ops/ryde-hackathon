# 活动任务索引

仅列未完成任务；当前结论见[STATUS](STATUS.md)，完成记录见[LOG](archive/LOG.md)。

| ID | 状态 | 负责人 | 依赖与入口 |
|---|---|---|---|
| MODEL-QUALITY | 可选扩测：司机提示词更新后小样本通过，稳定性未充分验证 | 协调助手 | [真实API报告](reports/WB02-LIVE.md)；既有接入已完成，后续调用需明确预算 |
| FINAL-INTEGRATION | updating：审查分支取舍、合并main、终稿与成品入口 | 协调助手 | [当前任务](tasks/SUBMISSION-FINAL.md) |
| SUBMISSION | UI、材料和GitHub成果分支已完成；浏览器彩排、真实工具截图、表单资料与正式提交待补 | 协调助手协调；用户补真实使用与个人信息 | [收尾报告](reports/SUBMISSION-FINAL.md)、[要求清单](REQUIREMENTS.md)、[草稿PR #5](https://github.com/luoziming49-ops/ryde-hackathon/pull/5) |
| S1 | S1b按语义整合本地，PR#3仍未合并 | PR作者unknownAndy123；协调助手审查 | [PR#3](https://github.com/luoziming49-ops/ryde-hackathon/pull/3)、[本地验收](reports/WB03-WB04.md)；发布前协调分支，避免覆盖同伴 |
| T004 | 模型资源已确认；工具使用证明及未核验的上传限制待补 | 用户提供信息，协调助手记录 | [资源任务](tasks/T004-resources.md)；不重问已有API配置 |
| T011 | 旧配置记录PR待核对 | 协调助手与成员 | [记录](tasks/T011-branch-protection.md)／[PR#1](https://github.com/luoziming49-ops/ryde-hackathon/pull/1) |

WB01、WB02离线、WB03/WB04模拟验收及WB02-LIVE接入均已完成。不要根据旧任务文件重新启动未选方向或重复可靠性开发。模型稳定性与赛事提交保持独立验收。
