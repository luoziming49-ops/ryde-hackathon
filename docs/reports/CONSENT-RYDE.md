# 口头同意、证据边界与Ryde风格补充 · 2026-10-16

基于main 4e089cf，用户已授权补充优化并匹配Ryde官方App风格，沿用自主验证、合并和交付授权。分支融合取舍仍以[CP-020报告](FINAL-RELEASE.md)为准；本报告只记录新增变化。正式比赛尚未提交。

## 行为与范围

双方可分别提供结构化`route_consent`：agreed / not_agreed / unknown，缺省unknown；程序比较为consistent / conflicting / unconfirmed。陈述一致只表示双方报告一致，不表示口头同意已独立核验。GPS支持位置、里程与停靠，缺聊天不证明无沟通；新增证据目录条目保持reported，Judge不能将原始声明选成独立事实。

未确认或冲突事实会改变责任或金额时，停止自动退款，输出amount=null、人工复核标记和review_questions。额外停靠的解释、同意与费用影响单独判断；未知路况保留null。客观no-show和无额外停靠的小偏差可继续按规则处理。演示政策RD-001.8与Judge提示词1.0.1明确这些边界，不是Ryde官方生产政策。

保留原3个内部样例的全部原始值与文本；原0001结果由旧自动退款改为待人工，不为保留7.87倒填同意。另加3个明确标记Synthetic的变体，均无额外停靠：双方认可→no_action/0，双方冲突→待人工/null，双方报告未同意→演示规则建议7.87。原3案、合成3案和官方1案共7案。0002仍为full_refund/5，0003与DISP-002仍no_action/0。

前端展示双方原话、结构化声明、三类比较状态和待核实问题；所有外来文本转义，未知金额不显示0。保留28个已有ID、模拟/Live区分、回退、证据引用和审计。人工复核仅标记，没有客服派单；无新案件上传/输入页或持久化。地图为输入坐标示意，里程比例来自输入字段，traffic字段未经外部地图核验，不执行支付。

## 视觉与材料

一手来源与项目适配分别记录在[Ryde品牌来源](../sources/2026-10-16-ryde-brand.md)。采用莓红点缀、可读性更高的深莓红主按钮、浅粉选中态、白卡片和系统字体；保留简洁层级，标明Hackathon prototype。没有复制官方标志或声称是官方产品。

同步更新英文文案、约6分钟脚本、导览、真实WorkBuddy辅助任务提示词、封面与架构SVG。3张PNG重新导出；实际查看两张1920×1080主图，文字完整、布局无溢出；380×216版保持比例并留边。真实工具对话与采用记录仍为空待补，不伪造证明，不把旧Live报告作为新规则实测。

## 实际验证

后端首批新测试先运行得到28 failed in 0.29s，完成最小实现后28 passed in 0.23s；最终独立consent测试36项。前端新增13种行为，新增显示先失败，完成后前端60项通过。旧金额和保护测试保留原验证目标，在需要的副本中显式提供双方not_agreed；不修改原样例事实来迁就预期。

在禁用收费调用的环境运行：

```bash
OPENAI_API_KEY= LLM_API_KEY= LLM_LIVE_ENABLED=false .venv/bin/python -m pytest -o addopts= -q
```

协调者实际输出：

```text
........................................................................ [ 17%]
........................................................................ [ 34%]
........................................................................ [ 51%]
........................................................................ [ 69%]
........................................................................ [ 86%]
........................................................                 [100%]
416 passed in 2.51s
```

```bash
OPENAI_API_KEY= LLM_API_KEY= LLM_LIVE_ENABLED=false .venv/bin/python -m backend.evaluate --output /tmp/ryde-consent-final-evaluation.json
```

```text
36/36 passed; 0 failed. SIMULATION ONLY.
```

预期冻结于sample_data/evaluation/golden.json版本2026-10-16-consent-demo-v3；保留四种provider场景，新增同意、停靠、未知路况、小偏差和客观no-show边界。原始全量与逐项评测输出保存在[验证附件](assets/consent-ryde/verification.txt)。没有新收费模型请求。

通过FastAPI TestClient实际调用7个样例，输出如下；同一检查确认根路由逐字节等于当前frontend/index.html，health.live_enabled=false，原3内部样例与改动前深比较相同：

| 案例 | 声明比较 | 动作 | 金额 | 待核实问题数 |
|---|---|---|---|---|
| RYDE-2026-0001 | unconfirmed | insufficient_evidence | null | 2 |
| RYDE-2026-0002 | unconfirmed | full_refund | 5.0 | 0 |
| RYDE-2026-0003 | unconfirmed | no_action | 0.0 | 0 |
| DEMO-ORAL-AGREED | consistent | no_action | 0.0 | 0 |
| DEMO-ORAL-CONFLICT | conflicting | insufficient_evidence | null | 1 |
| DEMO-ORAL-NOT-AGREED | consistent | partial_refund | 7.87 | 0 |
| DISP-002 | unconfirmed | no_action | 0.0 | 0 |

独立审查发现人工说明仍暗示已派单；新增真实API、trace及运行事件断言先得到4 failed，再统一为Flagged for human review / No support case has been dispatched。独立复查已关闭该P2；修复后完整416项通过。git diff --check通过；87处修改文档链接核查无新增缺失，5处历史来源链接仍沿用父目录原始资料，不复制私人原文入仓库。

## 浏览器与发布

用户提供Always Allow后，同一http://127.0.0.1:8766重试仍被浏览器工具的保存权限或受管策略拒绝。没有换端口、浏览器、CDP或其他路径绕过。新页面真实桌面/窄屏渲染、浏览器交互与新UI截图仍未验收；本报告的程序测试和材料图片查看不能替代浏览器验收。

实际服务已重启加载本轮代码，启动输出Application startup complete，仍为127.0.0.1:8766、禁用收费调用。

本轮发布回执将在实际合并后追加；交付ZIP从最终远端main生成，外部使用说明保存完整commit、tree和SHA256。
