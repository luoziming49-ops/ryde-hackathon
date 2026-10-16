# 表单可粘贴文案

2026-10-16口头同意与双语界面补充稿。英文正文可直接复制；方括号字段必须由负责人据实替换。后续表单页的长度及上传限制尚未核验，必要时再按实际限制精简。本文件不是提交回执。

## Project name

Ryde Dispute AI

## Short introduction

Evidence-led dispute review with transparent multi-agent reasoning.

按空格计7词，少于10词。

## Track / Challenge

Digital Native Track

Ryde — Multi-Agent Autonomous Dispute Resolution System

## Project description

Ryde Dispute AI is an unofficial hackathon prototype for support reviewers handling route-deviation and no-show disputes. The problem framing comes from the organiser's Ryde challenge and supplied ticket format. It brings both parties' accounts, supplied records and demonstration policies into one inspectable review.

A Rider Advocate and a Driver Advocate build evidence-linked positions, then a Judge uses both positions and derived evidence to explain a rule-constrained recommendation. Local deterministic helpers collect evidence, flag risks and match demo policy and precedent records. Code controls final actions and amounts; models select evidence and never execute payments.

The system distinguishes consistent, conflicting and unconfirmed accounts. GPS can support route analysis but cannot establish oral consent, and missing chat does not establish that no conversation occurred. Even when both parties report oral agreement, that remains reported evidence rather than independent verification. If responsibility depends on consent and a key fact remains conflicting or unknown, the recommendation is marked for manual review and the amount remains undetermined. This is a review flag, with no support-team dispatch or case handoff integration.

The browser UI uses four baseline cases and three explicitly synthetic consent variants; these variants are not additional real-world cases. A structured /api/resolve endpoint accepts case data, but there is no upload or new-case entry screen and no persistent new-case storage. The route plot illustrates supplied coordinates. Deviation percentages use provided mileage; routes and traffic fields are not independently checked against a mapping service.

FastAPI, Pydantic, Python orchestration and native browser JavaScript support a fixed sequence of three roles. Versioned prompts separate instructions from untrusted case data. Structured outputs are checked against the evidence catalog and applicable policy. Validation failures receive at most one repair attempt before visible fallback; transport failures fall back without a repair call. The workbench exposes events, per-agent outcomes, attempts, citation inspection and audit JSON. Run records are held in local process memory. The interface switches between Chinese and English without rerunning the case; source evidence, original explanations and audit data are preserved.

Simulation exercises the actual agent and validation pipeline. Explicit Live API mode connects the same roles to DeepSeek and reports provider usage. Earlier bounded live checks demonstrated that connection and its failure paths; they do not validate the latest oral-consent logic or establish production accuracy. The intended value is clearer evidence review and explanations. Review-time savings, accuracy and customer outcomes remain unmeasured on representative data. All evidence and policies are demonstration inputs, with no live Ryde data connection, automated dispatch or payment execution.

## Source code URL

https://github.com/luoziming49-ops/ryde-hackathon

源码以默认main交付；既有整合记录见[终稿报告](../reports/FINAL-RELEASE.md)，最新功能补充的验证与发布状态见[当前状态](../STATUS.md)。

## Demo / video URL（选做）

[Not provided — local prototype only; no public deployment or recorded video supplied]

若表单要求URL格式且该项可选，可留空；不要把127.0.0.1地址填成可公开访问的演示。

## 团队与个人信息（由本人填写）

| 字段 | 当前待填内容 |
|---|---|
| Team name | [队名] |
| Team leader full name | [队长姓名] |
| Job title / course of study | [职位或专业] |
| Company / school | [公司或学校] |
| Team leader email | [邮箱] |
| Team leader phone | [电话，含国家/地区代码] |
| Other team members（如表单要求） | [姓名与对应必填信息] |

个人联系方式直接填写官方表单，不必提交到公开仓库。

## CodeBuddy / WorkBuddy 使用说明（实际完成后填写）

当前没有可据此填写的真实使用证明。先执行[辅助任务](WORKBUDDY-PROMPTS.md)，然后按实际情况填写：

- Tool used: [实际工具名]
- Tasks completed: [实际完成的辅助任务；未做的删除]
- Output used: [具体采用到哪个文件/段落；未采用则写明原因]
- Evidence: [至少3张真实对话截图对应的文件名]
- Contribution scope: Auxiliary review and submission preparation. [根据实际使用修订；不要扩大为核心系统开发]

辅助任务及截图不构成资格已获认可的保证；最终适用性以主办方规则和评审为准。官方材料要求见[REQUIREMENTS](../REQUIREMENTS.md)。
