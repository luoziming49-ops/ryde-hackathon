# 中英语言切换 · 2026-10-16

用户要求在当前工作台加入中英语言切换。范围见[任务](../tasks/BILINGUAL.md)，代码基线main 5c6b024。保留CP-022恢复的本机DeepSeek配置，模拟仍为默认模式；本轮不发送收费请求，不改后台证据/裁决/金额规则。

## 交付行为

页首“中文 / English”选择器记住选择；没有有效保存值时，浏览器zh语言选择中文，其余英文。存储不可用时仍可切换，document.lang同步zh-CN/en。切换只影响展示，不新增模型请求或重跑，不改变案件、模式、场景、进行中请求、金额或审计数据。

界面标签、状态、固定提示、角色与动作名双语；中文裁决提供结构化摘要，可展开原始理由，英文原始理由默认展开。双方原话、聊天、证据引用、事件正文和未知返回文本不做猜测翻译。仅4种已知待核实问题使用精确映射，其他内容保留原文；审计JSON仍保留原始合同。引用弹窗、证据页签、展开状态、滚动位置及错误/运行状态在切换中保留。

## 文件变化

- frontend/index.html：原生语言选择器、285项显式文案字典、呈现状态快照、动态本地化与中文结果摘要，无新依赖。
- tests/frontend_behavior.cjs、tests/test_frontend.py：保留原60项前端检查，新增25项行为检查，包括23种语言场景及2个真实离线API结果。
- README.md、docs/submission/DEMO.md、FORM-COPY.md、README.md：使用说明、演示指引及真实能力边界。
- docs/REQUIREMENTS.md、STATUS.md、TASKS.md、archive/LOG.md、tasks/BILINGUAL.md、本报告及验证附件：同步当前记录，包含前轮本机API恢复交接。后台、样例、金额政策和模型提示词没有变化。

## 测试先行及独立检查

首批命令：

```bash
OPENAI_API_KEY='' LLM_API_KEY='' LLM_LIVE_ENABLED=false .venv/bin/python -m pytest -q -o addopts='' tests/test_frontend.py
```

```text
4 failed, 60 passed in 1.70s
```

新失败是setLanguage尚未实现，原60项通过。新增覆盖偏好/浏览器语言/存储异常、切回英文、null与0、运行中切换、完成/失败、原文和转义、引用/架构弹窗、审计不变、真实0001与DEMO-ORAL-NOT-AGREED输出。后续独立检查找到初始化失败状态、重复引用焦点、英文理由初始展开、实际事件角色译名、未知核实问题误套UI字典等边界，逐项先复现再修复。

最后收口命令：

```bash
OPENAI_API_KEY='' LLM_API_KEY='' LLM_LIVE_ENABLED=false .venv/bin/python -m pytest -q -o addopts='' tests/test_frontend.py -k 'i18n_event_roles or i18n_duplicate_reference_focus or i18n_original_reason_disclosure or i18n_review_questions'
```

```text
4 failed, 81 deselected in 0.28s
```

修复后完整前端输出：

```text
........................................................................ [ 84%]
.............                                                            [100%]
85 passed in 2.56s
```

协调者最终完整回归命令：

```bash
OPENAI_API_KEY= LLM_API_KEY= LLM_LIVE_ENABLED=false .venv/bin/python -m pytest -o addopts= -q
```

```text
........................................................................ [ 16%]
........................................................................ [ 32%]
........................................................................ [ 48%]
........................................................................ [ 65%]
........................................................................ [ 81%]
........................................................................ [ 97%]
.........                                                                [100%]
441 passed in 3.15s
```

```bash
OPENAI_API_KEY= LLM_API_KEY= LLM_LIVE_ENABLED=false .venv/bin/python -m backend.evaluate --output /tmp/ryde-bilingual-evaluation.json
```

```text
36/36 passed; 0 failed. SIMULATION ONLY.
```

[验证附件](assets/bilingual/verification.txt)保存完整回归、前端与逐项模拟评测输出。静态检查与应用内TestClient实际输出：

```text
Translation keys: 285; static targets: 31; missing keys: 0; all 28 existing IDs retained; no duplicate IDs
Application route /: 200; exact bilingual frontend bytes; existing live_enabled=true; no model request sent
Backend and sample-data contracts unchanged
```

`git diff --check`及`git diff --exit-code HEAD -- backend sample_data`均退出0、无输出。检查有效本地配置只读取是否启用与模型名，不打印凭据。真实服务仍为原进程，前端静态文件刷新即可生效，本轮没有重启或禁用Live API。

独立审查最后复核了实际事件角色译名、4种核实问题白名单、英文理由及展开状态、重复引用焦点与启动错误状态，均已关闭；没有新增请求/终止运行/改写业务对象的路径。该结论来自静态代码与测试断言核对，不是浏览器验收。

## 真实限制与交付

中文摘要是结构化结果展示，不是原始证据的人工核验或机器翻译。没有新模型实测，旧Live报告不能作为本次新逻辑调用证据。浏览器工具仍存在同一本机站点的权限拒绝；不以离线DOM测试代替真实桌面/窄屏视觉验收，不通过其他端口或控制方式绕过。

交付以GitHub main为入口，最终发布commit、tree与ZIP校验值由交付包外使用说明记录。文档complete只表示本轮记录同步，不表示赛事已经正式提交。真实工具使用截图、团队资料和官方回执仍待补。
