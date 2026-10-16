# 表单可粘贴文案

2026-10-16终稿文案。英文正文可直接复制；方括号字段必须由负责人据实替换。后续表单页的长度及上传限制尚未核验，必要时再按实际限制精简。本文件不是提交回执。

## Project name

Ryde Dispute AI

## Short introduction

Evidence-backed dispute resolution with transparent multi-agent review.

按空格计7词，少于10词。

## Track / Challenge

Digital Native Track

Ryde — Multi-Agent Autonomous Dispute Resolution System

## Project description

Ride-hailing disputes leave support reviewers reconciling two accounts across trip records, chat, fees and policy. Ryde Dispute AI brings these inputs into one inspectable workbench for route-deviation and no-show disputes. The prototype is designed for support staff who need to understand both parties' positions and explain a consistent recommendation.

The problem framing comes from the organiser's Ryde challenge and supplied ticket format. Local deterministic helpers collect evidence, flag review risks and match demo policy and precedent records. A Rider Advocate and a Driver Advocate build evidence-linked positions. A Judge uses both positions and verified derived evidence to explain the outcome. Deterministic code computes distances, waiting thresholds, applicable policy, final action and refund amounts. Models select supplied evidence; they do not control the amount or execute payments. Missing or conflicting evidence can trigger human review.

The application uses FastAPI, Pydantic, Python orchestration and native browser JavaScript. Versioned role prompts keep instructions separate from untrusted case data. Each agent's structured response is checked against the evidence catalog and applicable policy. Invalid content receives at most one repair attempt before a visible deterministic fallback; transport failures fall back without a repair call. The workbench shows execution events, individual agent outcomes, attempts, evidence and policy inspection, and a downloadable audit record.

Simulation mode runs repeatable local scenarios through the actual agent and validation pipeline. An explicit Live API mode connects the same three roles to DeepSeek and reports provider token usage. Bounded live checks include accepted outputs, rejected references and fallback; they do not establish production accuracy. The agents run in a fixed sequence, with no claim of autonomous negotiation.

The intended business value is faster evidence review, clearer explanations for riders and drivers, and a reproducible support record. The demo covers two dispute categories and four baseline cases, with additional offline checks for missing evidence and failure handling. Evidence and policies are demonstration inputs; there is no connection to live Ryde data or payment systems. Review-time savings, real-world accuracy and customer outcomes remain to be measured on representative data. Run records are held in local process memory, so production persistence and account isolation remain future work.

## Source code URL

https://github.com/luoziming49-ops/ryde-hackathon

源码以默认main交付；合并与验证记录见[终稿报告](../reports/FINAL-RELEASE.md)。

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
