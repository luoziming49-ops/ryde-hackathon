# 开源机制调研

核验日期：2026-10-07。用于 [T012](../tasks/T012-structure-handoff.md) 的结构建议；以下是官方仓库与文档事实，不是框架已接入或性能已经提升的证据。借鉴方案见 [结构建议](../ideas/2026-10-07-structure.md)。

## 推荐参考

| 项目与来源 | 已核验机制与许可 | 本项目借鉴 | 不引入的部分 |
|---|---|---|---|
| [PydanticAI](https://github.com/pydantic/pydantic-ai) · [输出校验](https://pydantic.dev/docs/ai/core-concepts/output/) · [MIT](https://github.com/pydantic/pydantic-ai/blob/main/LICENSE) | 类型化输出、输出验证与有界重试 | 用现有 Pydantic 约束代理输出；检查证据 ID、政策 ID 与输出动作 | 不替换已有 LLM provider，不安装其运行框架 |
| [LangGraph](https://github.com/langchain-ai/langgraph) · [中断与恢复](https://docs.langchain.com/oss/python/langgraph/interrupts) · [MIT](https://github.com/langchain-ai/langgraph/blob/main/LICENSE) | 显式步骤、checkpoint、暂停与恢复；恢复会重跑节点开头，副作用需可重复执行 | 当前 orchestrator 明确阶段、状态和失败边界；后续补证形成新 run | 不引入 LangGraph 平台、长期记忆和自由循环 |
| [assistant-ui](https://github.com/assistant-ui/assistant-ui) · [工具卡片](https://www.assistant-ui.com/elements/tool-fallback) · [MIT](https://github.com/assistant-ui/assistant-ui/blob/main/LICENSE) | 可折叠卡片呈现工具名、状态、耗时、参数与结果 | 用原生 details 元素实现证据与工具卡片，定位代理引用 | 不把单文件前端迁为 React |
| [Langfuse](https://github.com/langfuse/langfuse) · [数据模式](https://langfuse.com/docs/observability/data-model) · [许可](https://github.com/langfuse/langfuse/blob/main/LICENSE) | trace 包含步骤及输入输出，区分一次运行和会话；主体 MIT，ee 等目录有独立企业许可 | 分开 case_id、run_id、evidence_version，展示步骤和原始证据的关系 | 不部署其数据库、队列和完整观测平台；不能笼统称整个仓库 MIT |
| [promptfoo](https://github.com/promptfoo/promptfoo) · [测试案例](https://www.promptfoo.dev/docs/configuration/test-cases/) · [Python 集成](https://www.promptfoo.dev/docs/integrations/python/) · [MIT](https://github.com/promptfoo/promptfoo/blob/main/LICENSE) | 案例变量、断言与结果对比；支持 Python 集成 | 使用现有 pytest 和 JSON 案例做案例×版本结果表 | 不为首版增加 Node 评测服务，也不以模型给自己打分代替确定性断言 |

优先顺序是输出契约、执行事件、证据展示、回归评测。结构化输出只能约束格式，不能保证事实正确；本地校验仍须判断引用是否属于本案、政策是否适用、金额是否来自程序。

## 补充与取舍

[OpenHands Software Agent SDK](https://github.com/OpenHands/software-agent-sdk) 的 [架构](https://docs.openhands.dev/sdk/arch/overview) 区分 Action、Observation、Executor 与事件，SDK [许可](https://github.com/OpenHands/software-agent-sdk/blob/main/LICENSE) 为 MIT。可以参考真实工具执行后再记录 observation 的做法；不向本项目业务代理开放 shell、文件编辑或代码执行工具。

[AutoGen](https://github.com/microsoft/autogen) 当前 README 标注维护模式并引导新用户使用 Microsoft Agent Framework，因此不建议在本冲刺引入新的 AutoGen 依赖。

本轮没有复制这些项目的源码，没有安装上述框架，没有验证其版本与项目的兼容性。若后续复制代码，执行者需在所用提交核对许可并保留相关声明。官方样例名称不自动证明来源权威：本项目 DISP-002 的来源仍须团队用赛事原件核对，不能从 GitHub 路径 official 推定真实 Ryde 政策。
