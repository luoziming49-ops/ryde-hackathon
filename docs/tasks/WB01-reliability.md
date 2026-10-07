# WB01 S1 可靠性收尾执行计划

> 执行者：WorkBuddy；协调与验收：本聊天的助手。按本任务逐步执行，每小步先补失败测试再修复；有相应技能时沿用测试和验收工作流，不要求安装技能。完成本轮后交回报告，后续 WB02–WB04 由协调者另行下达。

**目标**：保留现有原型，修复 S1 输入边界、缺失金额和官方样例展示，让后续模型与事件改造有稳定基础。

**结构**：adapter 负责外部格式，schema 统一内部边界，evidence 保留缺失信息，policy 决定动作金额；前端按实际数据展示。**栈**：现有 Python 3.10+、FastAPI、Pydantic、pytest、原生 HTML/JS，不增加重型依赖。**依据**：[结构建议](../ideas/2026-10-07-structure.md) 的 WB01 与 [核验记录](T012-structure-handoff.md)。用户将此任务交给执行器后，仅执行本任务范围。

## 负责人和基线

- 已核验 main 为 `36d127da432309bec93cc9929f10ec8102dbd482`；[S1 PR #3](https://github.com/luoziming49-ops/ryde-hackathon/pull/3) head 为 `6d7ad6dc568db4b2a91fa4a28f4cbbfb1114dfd4`，作者 unknownAndy123，核验时尚未合并。
- 先读取实际 checkout 的 AGENTS、STATUS、PROJECT_RULES，以及本任务。核对远端 URL、分支、HEAD、未提交修改、PR #3 最新状态；不得在旧的纯文档副本开发，也不要沿用 S1 文档里“PR #2 未合并”的旧说法。
- 若 S1 已合并，从包含它的最新 main 新建 `fix/wb01-input-reliability`；未合并时从核对后的 S1 head 建独立分支，记录依赖 PR #3，绝不改写同伴分支或替其合并。基线变化先对比差异，已修复项只验证，不重做。
- 检查同伴是否正在修改同一范围；发现有未提交他人改动时不 reset、不覆盖，使用独立 checkout。共享 STATUS/TASKS/DECISIONS 由协调者维护；执行者只把报告写到本任务指定路径。

## 全局约束

保留三个原始结果：0001 partial_refund SGD 7.87、0002 full_refund SGD 5.00、0003 no_action；DISP-002 为 no_action、未升级。不得调政策阈值或删断言迎合测试。金额仍由程序计算。缺值不是 0；显式有效 0 不得误判为缺失。负距离仍沿用 S1 的 evidence gap 行为。

本轮不做 LLM 重构、实时通信、页面重设计、部署、支付、框架迁移；不购买或申请资源，不输出密钥，不伪造使用截图。只创建本任务需要的文件。运行测试时不调用收费模型。真正模型调用留到 WB02 的独立 smoke 验证。

## 可写范围

`backend/schemas.py`、`backend/adapters/official_ticket.py`、`backend/adapters/README.md`、`backend/core/evidence.py`、`backend/core/policy.py`、`backend/main.py`、`frontend/index.html`；对应 `tests/conftest.py`、`tests/test_llm.py`、`tests/test_official_ticket.py`、`tests/test_robustness.py`、`tests/test_policy.py`、`tests/test_api.py`；可新增聚焦的边界测试和 `docs/reports/WB01.md`。样例原件保持不变，测试用复制数据构造反例。

## 检查重点

数组或字符串冒充对象应返回 422；缺失和显式零需区分；负值和非有限费用不可产生裁决；时区不同、取消早于到达、相互矛盾时间不可默默修正；前端缺字段和请求失败必须可见。每类都在下列步骤中覆盖。

## 步骤一 统一输入边界

- [ ] 运行任何API测试前，把当前测试进程的 OPENAI_API_KEY 和 LLM_API_KEY 均显式设为空字符串；只删除变量会让 main 从 .env 重新填入。现有 loader 不覆盖已存在变量，因此无需改用户 .env。provider 单元测试沿用 Mock；如新增测试隔离 fixture，只能影响测试进程，不得编辑或打印用户密钥。

接口保留 `POST /api/resolve` 和 `normalize_official_ticket(ticket: dict) -> dict`。可新增 `validate_dispute(data: dict) -> dict` 于 schemas，正式样例和按 ID 加载也必须经过同一内部模型；保留 extra 字段、raw_app_events、单案 policy override 和现有兼容行为。

- [ ] 先补 `test_official_bad_nested_types_422`：dispute_ticket、trip_data、profile 不是对象，或 chats/events 不是对象数组时返回 422 JSON，不是 500；验证已给出的合法数字字符串仍可用。
- [ ] 补 `test_money_invalid_both_formats_422`：内部和官方入口的负费用、非数字费用、字符串 NaN/Infinity 返回 422。缺失或 null 不在这里填零，由证据阶段判断。不要把 arrival/距离负值规则一起改掉。
- [ ] 运行新增测试保存失败输出，再在外部嵌套 schema、适配器与主入口做最小修复；校验在转换前后执行，不能先把坏值转成零再校验。
- [ ] 跑对应测试和全部既有测试，确认样例加载与 API 路径一致。

## 步骤二 金额缺失与到达记录

保留 `analyze_evidence(dispute)`、`apply_policy(evidence, policies, config)` 接口。只有最终规则分支需要的费用缺失才进入 `gaps/missing_fields`，输出 insufficient_evidence、escalated=true、amount=null、confidence=null；不能让全部 no_action 案例无条件要求完整绕路费用。

- [ ] 补 `test_route_refund_missing_fare_escalates` 和 `test_no_show_refund_missing_fee_escalates`：在会发生退款的现有样例副本中删除相应费用，断言上述升级结果；给出显式零的成对用例，验证零不会被当作缺失。
- [ ] 补 `test_arrived_false_without_distance_no_500`：明确 arrived=false 且没有 closest_distance_to_pickup_m 时不得格式化 None 崩溃，文字明确位置数值未知，不编造距离。
- [ ] 先运行失败，再修 evidence 的默认值处理、缺失判断和 policy 当前分支所需条件；不要在各个代理重复计算金额。

## 步骤三 官方等待时间

保留 `_wait_minutes(trip: dict, arrival_time) -> float | None`。优先 trip.driver_wait_start，其次 trip.driver_arrival_time，最后使用 app_events/telemetry 推导的 arrival_time；与 cancellation_time 计算分钟。无法统一时区、时序颠倒或来源矛盾时标记缺失/冲突并升级，不凭空补时区或取绝对值。

- [ ] 补 `test_official_wait_uses_event_arrival`：删除 trip 中 wait_start 和 arrival_time，保留官方样例的到达事件，仍算出约 8 分钟并维持 no_action。
- [ ] 补时间带不同有效 offset 的等价用例、取消早于到达用例、无时区与有时区混用用例；后两种不得 500 或产生负等待的正常裁决。
- [ ] 先失败再修 helper，更新 adapter 映射说明；保留未知 dispute_type 诚实升级。不要在没有正式 schema 的情况下猜测官方 route 类型映射。

## 步骤四 页面与交付

- [ ] 官方 DISP-002 的费用页不得对 undefined/null 调用 toFixed；缺值显示“未提供”，数值 0 显示 0.00。GPS 页缺路线/时长时同样显示未提供。
- [ ] resolve 请求先判断 response.ok，服务端失败展示错误并恢复按钮，不能把错误 JSON 当成功 trace。
- [ ] 健康状态和架构图使用实际 state/model 字段，resolve 后刷新状态；事后动画标“运行回放”，不要标实时。当前模型状态只是全局状态，逐代理状态留 WB02。
- [ ] 用实际浏览器选择四个案例、切换证据 tabs 并运行；检查控制台和错误状态，保留截图。如无法操作浏览器，报告“未验证”，不得用静态断言冒充浏览器测试；backend 边界用 pytest 回归。
- [ ] 使用以下跨平台命令跑全量测试：`python -c "import os; os.environ['OPENAI_API_KEY']=''; os.environ['LLM_API_KEY']=''; import pytest; raise SystemExit(pytest.main(['-o','addopts=','-q']))"`。通过同一空密钥进程调用 /api/health、首页和四个案例；记录 action、amount、confidence、escalated 的实际结果。若改用终端环境变量命令，也必须设为空字符串而非删除。
- [ ] 在任务分支提交，明确列出更改文件，不使用强制推送，不合并 PR，不覆盖现有分支。若用户另行授权推送再发布；本任务默认只本地提交并回报。

## 回传报告

写入 `docs/reports/WB01.md`：基线/分支/提交 SHA、文件列表、每个缺陷修复前后证据、完整测试命令和真实输出、四案例结果、浏览器截图位置、未完成事项、阻塞与下一步。敏感值脱敏。将该报告和差异交回协调者验收；STATUS complete 不由执行者擅自宣布，且测试绿不等于真实 LLM 或产品提交完成。
