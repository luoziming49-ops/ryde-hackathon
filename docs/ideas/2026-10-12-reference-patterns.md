# 开源参考与采用决策

核验日期：2026-10-12。目标是增强现有模拟MVP的可解释性和现场演示，不因参照获奖项目而推定自己的名次；未复制第三方源码，未更换现有技术栈。

| 一手来源与已核实事实 | 本项目采用的设计判断 | 实际落地 |
|---|---|---|
| [Microsoft AI Agents Hackathon 获奖列表](https://microsoft.github.io/AI_Agents_Hackathon/winners/)列 Apollo 为 Best C#；[Apollo 仓库](https://github.com/manasseh-zw/apollo)展示分工明确的研究代理、事件更新、带来源的报告与迭代状态。 | 将角色职责、引用和过程作为演示核心，比堆叠代理数量更容易让评委核验价值。这里是项目负责人的推论，不是比赛获奖原因证明。 | Rider／Driver／Judge保留各自输出；证据与政策按钮打开实际目录条目；运行报告可导出。 |
| [AutoGen 官方团队教程](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/teams.html)说明团队流式事件和最终结果。 | 过程事件应来自真实执行，失败状态也应可见。无需为该模式引入完整框架。 | RunRecorder在代理emit及实际工具读取时记录；RunStore允许结束前读取；前端增量轮询。 |
| [Promptfoo 官方断言文档](https://www.promptfoo.dev/docs/configuration/expected-outputs/)支持基于预期输出的断言评测。 | 将独立业务预期与当前实现分离，尤其检查金额、缺证和故障，而不是只展示成功截图。 | 冻结golden.json；本地evaluate入口；错误预期仍失败的测试；独立审查反例加入矩阵。 |

## 保留的取舍

- Apollo的复杂多轮研究不等同于争议裁决；本项目当前代理执行顺序固定，模型仅作受约束的证据选择，最终金额由程序计算。
- 不引入AutoGen、向量库、持久化数据库或多模型投票。四个样例与演示政策足以验证流程，不能证明生产检索质量或事实真实性。
- 网页的毫秒耗时属于本地模拟。真实模型耗时、成本、引用合格率要在后置API阶段重新测量。
- 下一项最有价值的改进是少量真实模型与同一评测集的对照实验，其次才是增加场景和包装。

完整验收与限制见[WB03/WB04报告](../reports/WB03-WB04.md)，正式提交项见[要求清单](../REQUIREMENTS.md)。
