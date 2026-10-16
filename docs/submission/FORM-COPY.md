# 表单可粘贴文案

2026-10-16口头同意与双语界面补充稿，已按[实际Digital Native提交页](../sources/2026-10-16-submission-form.md)校正字段。英文正文可直接复制；方括号字段必须由负责人据实替换。标题、7词短介绍、项目描述、源码和原型说明已填入草稿。当前表单要求在线演示与5–8分钟视频链接，用户确认均未具备，两项留空。本文件不是提交回执。

## Project Title

Ryde Dispute AI

## Short Blurb

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

## Project Demo Link（当前表单必填）

待补真实的、浏览器可在线体验的公网URL。用户确认目前没有部署链接。不要把此说明、占位符、GitHub源码链接或127.0.0.1地址当作可体验的演示URL填写。

## Demo Video Link（当前表单必填）

待补真实可访问的视频URL。当前表单要求5–8分钟，涵盖项目介绍、核心agent功能及用法、开发方式反思和开发工具经验。用户确认目前没有视频链接；现有[演示脚本](DEMO.md)不能代替视频。

手册p40曾将上述两项列为选做；当前实际表单均有必填标记，因此本次按必填缺口处理。

## Working Prototype

Runnable prototype and setup instructions: https://github.com/luoziming49-ops/ryde-hackathon

The local browser workbench demonstrates two dispute categories end to end: route deviation and no-show. In Simulation mode, select RYDE-2026-0001 for an unresolved consent case (manual-review flag, amount undetermined), or RYDE-2026-0002 for a no-show case (SGD 5.00 full-refund recommendation). Each run exposes Rider Advocate, Driver Advocate and Judge outputs, evidence/policy citations, execution events, failure fallback and downloadable audit JSON. Three additional consent variants are explicitly synthetic. No payment or support dispatch is executed.

Follow the repository README to run the prototype locally. The existing localhost address is not a publicly accessible demo.

以上描述如实说明当前本地原型，不能替代Project Demo Link的公网URL要求。

## 上传附件

| 表单字段 | 已准备材料 | 当前表单限制 |
|---|---|---|
| Cover Image | `cover.png`（1920×1080）；380×216版仅作备用 | 1个文件，最多1MB；16:9，推荐380×216 |
| WorkBuddy/CodeBuddy Conversation History | 本地交付包中的`WorkBuddy-Conversation-History.pdf`，包含3张真实截图及使用范围说明 | 1个文件，最多10MB；聊天记录及至少3张截图 |
| Architecture Diagram PPT | 本地交付包中的`Ryde-Architecture.pptx`，单页16:9架构图 | 1个文件，最多10MB |

三项附件均已实际上传，表单中显示已选文件，页面显示Draft saved；尚未点击Submit。原始对话截图不进入公开仓库。其他文件格式是否被接受仍以实际文件选择器为准。

## Social Media Post Link（Bonus）

当前没有社交发布链接，可留空。实际表单要求社交帖包含`#WorkBuddy #CodeBuddy #Miora #TencentCloudHackathon`；不得填入未经发布的链接。

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

## CodeBuddy / WorkBuddy 使用说明

Tool used: WorkBuddy.

WorkBuddy was used for an early input-robustness task discussion, demo-checklist drafting, and static UI screenshot review. Three supplied screenshots show the requests and portions of its responses. We incorporated the visible pre-demo checks into our demo script. The static UI review and historical robustness report are retained as review/conversation records; they are not independent proof of current test results, complete browser validation, or authorship of the entire system.

Contribution scope: input-robustness task assistance and submission preparation.

Evidence files:
- workbuddy-01-input-robustness.png
- workbuddy-02-demo-checklist.png
- workbuddy-03-ui-review.png

三张原图与采用说明已整理为本地独立证明包`WorkBuddy-Usage-Evidence-2026-10-16.zip`；为适配当前表单单附件、最多10MB的限制，另生成并上传`WorkBuddy-Conversation-History.pdf`，表单已显示该文件。两者均不包含在公开源码ZIP内。详细可见范围、未取得的完整清单和采用边界见[使用记录](WORKBUDDY-USAGE.md)。官方要求与当前表单限制见[REQUIREMENTS](../REQUIREMENTS.md)，不把截图齐备或附件上传写成赛事资格已获认可。
