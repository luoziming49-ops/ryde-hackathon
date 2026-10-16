# WB03/WB04 模拟工作台实施计划

2026-10-12，基线c62663f；负责人：协调助手。用户授权自主规划实施，先交成果后审阅；API最后接入。规格：[MVP-SIM](MVP-SIM.md)。沿用brainstorming、writing-plans、TDD；独立模块按dispatching-parallel-agents并行，协调者负责集成和最终审查。复用当前独立checkout，在feat/mvp-simulation-workbench开发，不合并同伴PR，不发布或收费调用。

## 目标与取舍

交付评委可现场运行的两类争议工作台：明确模拟场景、双方带引用主张、实时阶段事件、可定位证据/政策、错误回退，以及独立预期的评测结果和演示材料。保留FastAPI/Pydantic/原生JS，不引入框架。模拟是实际后端中的本地响应生成器，不是替换页面元数据；外部HTTP被测试禁止。

选择有界内存运行记录加轮询；与SSE相比无需新增长连接管理，与SQLite相比部署更简单。代价：重启丢失运行，单进程演示用途；不承诺刷新恢复或生产多租户。保留/api/resolve；新/api/runs只执行模拟，避免网页误触真实API。运行最多保留50条，最多2条并发执行，超限503；错误只返回固定代码。

## 固定接口与文件职责

1. `backend/core/simulation.py`：`SimulationProvider(scenario='success')`实现complete_structured相同签名；复用LLMProvider的JSON/引用校验与重试逻辑，仅将_request替换为本地响应。场景success、rider_rejected、retry_success、provider_error。增加LLMResult的`is_simulated: bool=False`、`scenario: str|None=None`；模拟成功mode保留llm以兼容，UI必须优先显示Simulated。环境有密钥也不触网，实例每次运行独立；不把已校验fallback直接冒充模型调用。
2. `backend/core/events.py`：线程安全RunRecorder与RunStore，状态running/completed/failed。事件字段run_id、seq、parent_id、actor、kind、status、started_at、duration_ms、input_summary、output_summary、evidence_ids、mode。`BaseAgent.emit`即时回调；actor对应真实代理，工具仅白名单读取本案数据。
3. `backend/core/tools.py`：CaseTools读取gps/chat_log/fare/rider/driver/trip和匹配政策，记录开始/结束、输入摘要、结果摘要与耗时，不暴露密钥或完整私人资料。实际返回数据进入pipeline，不做装饰性工具调用。
4. `DisputeOrchestrator.resolve(dispute, *, is_simulated=None, provider=None, recorder=None)`：所有代理注入同一运行provider，emit实时记录；回应保留旧字段并加run_id、execution、policy_catalog。policy_catalog只含本案命中规则，version与guard相同。
5. `POST /api/runs`严格请求`{case_id, scenario}`返回202 `{run_id,status:'running'}`；`GET /api/runs/{id}?after=0`返回`{run_id,status,events,next_seq,result,error_code}`，result仅完成时有；未知ID404，非法场景422。默认success，背景线程实际执行。新增`GET /api/simulation/scenarios`列出ID/标签。
6. 前端保留入口和旧行为函数供回归；默认明确SIMULATION横幅、场景选择；点击运行POST后轮询增量事件直到完成；切案/重跑请求令牌隔离旧响应，关闭旧轮询，失败可重试。双方主张及裁决提供证据/政策按钮，弹窗显示已返回目录项的原文、来源、版本；所有动态内容转义。可导出当前审计JSON，标明模拟及不执行支付。

## 测试任务（先RED后GREEN）

- [x] 核对S1b远端新增测试与本地现有实现，按语义整合缺口，保留WB01更严格的输入与缺失值边界；不直接覆盖整个远端实现。
- [x] Provider：四场景、每代理尝试次数、坏引用、无效JSON修复、异常不泄漏、并发隔离；网络替身抛错证明没有HTTP调用。
- [x] 后端：事件在受控阻塞的代理结束前可读、seq严格递增、工具错误/非法字段、容量及并发限制、失败可回读、/api/resolve兼容；快照及结果隔离不串案。
- [x] 前端：模拟标识、全链路请求、故障/重试、切案/重跑旧回包隔离、引用转义及找不到引用、可访问关闭弹窗、空数据与旧响应兼容。
- [x] WB04独立预期矩阵覆盖四案与缺证/冲突/非法数据/模型错误/政策缺失；预期冻结为JSON，不从实际输出生成。逐项实际结果保存报告。
- [x] 真实浏览器验证两类争议、四模拟场景、引用定位及窄屏；记录console及截图。完整pytest通过、独立审查后本地提交。

## 展示交付与评分对应

补齐项目介绍、架构图、5–8分钟演示脚本、封面SVG、模型提示词说明、现有证据与提交清单。R02–R07由完整模拟链路展示；R08/D06所需真实CodeBuddy/WorkBuddy聊天截图不能制造，已有真实资料才引用，缺口保留。D03最新代码暂本地，发布/正式提交另行确认。

## 进度与决策记录

- 初始化：现有临时Python环境已被清理；在项目.gitignore覆盖的.venv重建依赖，不改全局环境。
- Ruling：用户已明确要求自行规划完成、成果后审阅，沿用已确认规格直接实施，不新增中途设计确认门槛。
- Ruling：采用模块隔离并行执行provider和前端，协调者负责后端、评测、资料与集成；共同接口如上，禁止跨文件写入。
- Ruling：运行过程是真实本地执行，模型响应为模拟，两个维度分别标识；不把多模型一致当作真实性证明。

- 完成：独立审查发现GPS离开后仍累计等待的P1，四个组合回归先失败后通过，复查关闭。交付证据与限制见[WB03/WB04报告](../reports/WB03-WB04.md)。
- 收尾：按用户先成果后审阅的授权，采用保留本地分支，不发起中途合并菜单；同步依赖版本与运行说明。最终CSS只压缩长记录区域并补键盘聚焦，全量回归及浏览器复验通过。
