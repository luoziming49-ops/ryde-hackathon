# FORM-FILL · 实际表单填写与附件适配

状态：本轮填写与上传已核验，待补两个必填URL；没有正式提交。负责人：协调者负责表单与记录，执行者分别生成PPTX和PDF，未操作浏览器或公开原图。基线修订26，交接修订27。

用户明确要求填写当前Chrome的腾讯云黑客松项目提交表单。第二页要求唯一记录在[S9](../sources/2026-10-16-submission-form.md)，交付清单见[REQUIREMENTS](../REQUIREMENTS.md)。不回读或保存第一页个人资料。

## 已填写并回读

- Project Title：Ryde Dispute AI。
- Short Blurb：Evidence-led dispute review with transparent multi-agent reasoning.（7词）
- Project Description：使用[FORM-COPY](../submission/FORM-COPY.md)的完整英文描述。
- Source Code：https://github.com/luoziming49-ops/ryde-hackathon。
- Working Prototype：说明本地运行入口、route deviation/no-show两类端到端流程、0001未定金额与0002建议退款5新元、三角色/引用/事件/fallback/审计，以及合成样例、无支付/派单和未公网部署边界。

## 已上传并核对

| 表单栏 | 文件 | 字节数 | 验证 |
|---|---|---:|---|
| Cover Image | docs/submission/cover.png | 136736 | 真PNG，1920×1080；小于1MB；表单出现已选文件 |
| Conversation History | 父目录交付包/WorkBuddy-Conversation-History.pdf | 773656 | 4页，使用说明可检索，3张完整原图；逐页渲染检查且图片像素一致；表单出现PDF |
| Architecture Diagram PPT | 父目录交付包/Ryde-Architecture.pptx | 224316 | 单页16:9，有效PPTX；重导入及渲染与原架构图一致；表单出现PPTX |

两项新附件仅存本地交付包与用户指定表单，原始对话未进入公开GitHub。其SHA256集中维护在交付包/SHA256SUMS.txt。Chrome最后显示Draft saved；截图确认PDF/PPTX位于正确栏位。

## 尚缺与下一步

用户明确回答没有在线演示和视频链接。Project Demo Link与Demo Video Link保持空白；当前表单必填，不能替换为localhost、仓库代码页或演示脚本。社交Bonus留空。下一步需要部署可体验的演示并提供5–8分钟视频链接，再复核完整表单并正式提交、保存回执。此记录只证明草稿填写与附件上传，不证明主办方认可或已提交。
