# 要求、验收与提交清单

基线 [S1](sources/INDEX.md#s1)：比赛手册 V1.0；页码为 PDF 页序。状态更新：2026-10-16；新增[S7实际提交表单核验](sources/2026-10-16-submission-review.md)。模拟验收见[WB03/WB04报告](reports/WB03-WB04.md)，真实接入见[WB02-LIVE报告](reports/WB02-LIVE.md)；赛事提交仍待完成。

## 今日提交入口与表单

- **截止：2026-10-16（星期五）23:59，GMT+8（新加坡／北京时间）**。实际表单明确给出时区，见[S7](sources/2026-10-16-submission-review.md)。
- [官方提交入口](https://tinyurl.com/TCHackathonSGProjectSubmission)已验证进入Google表单Project Submission；该URL虽在旧摘要中称报名表，目前用途已变化。
- 第一页必填：队名、队长姓名、职位或专业、公司或学校、队长邮箱和电话、赛道、题目。本项目对应Digital Native Track及Ryde的Multi-Agent Autonomous Dispute Resolution System。
- Digital Native提交页已在2026-10-16的Chrome实际表单中读取，原始核验事实见[实际提交页记录](sources/2026-10-16-submission-form.md)。Project Title、Short Blurb（少于10词）、Project Description、Cover Image、Project Demo Link、Demo Video Link、WorkBuddy/CodeBuddy Conversation History、Architecture Diagram PPT、Source Code和Working Prototype均标为必填。
- 上传限制已明确：Cover Image为1个文件、最多1MB，16:9、推荐380×216；Conversation History为1个文件、最多10MB，须含聊天记录及至少3张截图；Architecture Diagram PPT为1个文件、最多10MB。文件选择器接受的具体扩展名仍以实际上传校验为准。
- **实际表单要求公网可体验的Project Demo Link，以及5–8分钟Demo Video Link。** 这与手册p40的选做说明不同；本次提交按当前表单必填处理。用户已确认两个链接均没有，本地地址和演示脚本不能替代。Social Media Post Link明确为Bonus。
- 标题、7词短介绍、项目描述、源码和原型说明已填；封面、对话证明PDF、架构PPTX均已实际上传并在表单显示已选文件，页面显示Draft saved。两个必填URL及社交Bonus留空，未点击Submit。填写与缺口摘要见[FORM-FILL](tasks/FORM-FILL.md)，参赛完成仍以正式提交回执为准。

## 核心要求

| ID | 要求 | 来源 | 建议验证证据 | 当前状态 |
|---|---|---|---|---|
| R01 | Digital Native / Ryde，展示开头注明题目 | p34 | 演示开场页 | 已进入工作台标题及封面 |
| R02 | 乘客代理取证、引用政策并建立乘客方主张 | p36 | 一次实际运行的证据、政策引用和输出 | 模拟链路已验收，见WB03/WB04 |
| R03 | 司机代理取证、引用政策并建立司机方抗辩 | p36 | 一次实际运行的证据、政策引用和输出 | 模拟链路已验收，见WB03/WB04 |
| R04 | 裁决代理综合双方证据，输出裁决、置信度、理由摘要和建议动作 | p36 | 与证据及政策可对应的裁决结果 | 模拟链路已验收，见WB03/WB04 |
| R05 | 使用文本与结构化证据，向双方解释结果 | p36 | 数据样本、输入输出、展示界面 | 模拟链路已验收，见WB03/WB04 |
| R06 | 至少两类争议端到端可运行 | p38–39 | 两类流程各有可复现演示与验证结果 | 绕路／未到场模拟流程已验收 |
| R07 | agent 间通信可观察 | p38 | 实际通信记录或 UI | 模拟链路已验收，见WB03/WB04 |
| R08 | 原创且使用 CodeBuddy 或 WorkBuddy 至少其一 | p40 | 真实开发记录、使用说明 | 已收3张WorkBuddy对话截图及采用记录；见[使用说明](submission/WORKBUDDY-USAGE.md)，资格适用性由主办方判断 |

证据类型基线包含 GPS/行程、聊天、费用及历史行为资料（p36）。实际字段、缺失处理及政策版本由设计确定。模拟外部 API/数据允许（p38）；数据取得状态由 [T004](tasks/T004-resources.md) 维护。

## 必交材料

| ID | 材料 | 来源与限制 | 状态 |
|---|---|---|---|
| D01 | 工作原型与现场/实时流程演示 | p39；覆盖至少两类争议 | 本地模拟原型已验收，现场讲述待彩排 |
| D02 | 多代理架构图PPT | p39；当前表单Architecture Diagram PPT必填，1个文件、最多10MB | [架构PNG](submission/architecture.png)与[SVG原稿](submission/architecture.svg)已检查；已校验的单页`Ryde-Architecture.pptx`已上传，表单显示已选文件 |
| D03 | 完整源码 GitHub 仓库 | p39；公开性未在该条明确 | [源码main](https://github.com/luoziming49-ops/ryde-hackathon)为终稿入口；分支取舍见[终稿报告](reports/FINAL-RELEASE.md)，最新功能与验收入口见[当前状态](STATUS.md) |
| D04 | 项目名称与短介绍 | p40；短介绍少于 10 个词 | [提交文案](submission/FORM-COPY.md)，7词短介绍 |
| D05 | 项目描述 | p40；场景/用户/价值、痛点依据、业务/技术架构、提示词作用、量化或明确业务影响 | [英文表单文案](submission/FORM-COPY.md)已整理；业务收益为待测目标 |
| D06 | CodeBuddy/WorkBuddy 开发对话与使用证明 | p40；至少3张真实聊天截图，缺少使用证明不进入评分；当前表单1个文件、最多10MB | 已收3张，原图及[采用记录](submission/WORKBUDDY-USAGE.md)已整理；已校验的单一附件`WorkBuddy-Conversation-History.pdf`已上传，表单显示已选文件；不在公开源码包内 |
| D07 | 封面图 | p40与当前表单：16:9、推荐380×216；当前表单1个文件、最多1MB | [1920×1080 PNG](submission/cover.png)、[380×216留边版](submission/cover-380x216.png)和[SVG](submission/cover.svg)已检查；封面PNG已上传，表单显示已选文件 |
| D08 | 在线项目演示链接 | 当前表单Project Demo Link必填；浏览器可在线体验 | 用户确认暂无公网部署链接，待补；不能使用127.0.0.1代替 |
| D09 | 演示视频链接 | 当前表单Demo Video Link必填；5–8分钟，含项目介绍、核心agent功能与用法、开发反思及工具经验 | [脚本](submission/DEMO.md)已备，用户确认暂无视频链接，待录制并提供可访问链接 |

另需填写上述团队及队长信息。口头同意与Ryde风格补充见[记录](reports/CONSENT-RYDE.md)，最新语言切换及实际验证见[双语报告](reports/BILINGUAL.md)；真实浏览器彩排仍受保存的站点权限阻止。素材盘点发现WB03的封面/架构预览虽后缀为PNG，实际为JPEG；打包时需匹配编码与扩展名，不能直接宣称为PNG。

## 手册选做项与当前表单差异

- O01：额外证据收集、欺诈检测、政策与先例代理（p37）。
- O02：图像分析、低置信度人工升级、纠正反馈、SLA/优先级路由（p37）。
- O03：5–8分钟演示视频在手册p40标为Optional；**当前表单已标必填，按D09补齐**。
- O04：线上项目或演示链接在手册p40标为Optional Bonus；**当前表单Project Demo Link已标必填，按D08补齐**。
- 当前表单仅Social Media Post Link明确为Bonus，要求带指定活动与工具标签；本项目尚未提供该链接。

O01已有本地确定性取证、风险和先例代理；O02已实现缺证与低置信度升级，未实现图像分析、纠正反馈和SLA路由。O01/O02不全部加入承诺范围。O03/O04保留手册历史说法以说明来源差异，但不能据此跳过当前表单必填项。

## 评分视角

p43 列出十项、每项 10 分：影响与相关性、以人为中心的设计、AI 交互、技术实现、可行性、演示与叙事、创新、体验与可访问性、负责任 AI 与伦理、总体质量与印象。

该页注明详细赛道标准在注册后提供；当前不据此预测名次。设计时把选定的价值主张映射到可证明的运行结果，提交前再核对最新正式标准。

## 已完成的材料与工具证明检查（2026-10-16，CP-026）

- 实查发布主线及ZIP完整树、文件内容、SHA256、CRC与提交材料引用，均通过；封面与架构3张PNG已核对真实格式/尺寸并逐张查看，未见裁切。最终版本和校验值统一记录在交付包外使用说明。
- 表单短介绍按空格计7词；文案中金额、合成样例、历史Live证据、双语原文及未实现能力的表述与当前代码一致。演示脚本已补两处操作遗漏：两个合成案例分别运行；切回0001重新运行后再查看引用。
- 本轮只有材料与记录变化，功能代码沿用CP-024的445项回归（含89项前端）结果，未重复运行软件测试或发送模型请求。用户确认此前加载提示在刷新后恢复；不据此声明完整演示彩排完成。
- D06已收到3张WorkBuddy对话截图：历史输入健壮性任务、演示清单草拟、静态界面审核。原图保持不变，只在本地独立证明包交付；实际可见范围及采用情况由[使用说明](submission/WORKBUDDY-USAGE.md)维护。源代码ZIP不包含这些对话原图；后续按表单单附件限制生成的PDF现已另行上传。
- CP-026检查时尚未读到后续上传页，也未填写或提交表单。此后已实际读到Digital Native页并确认上述限制，完成现有文案填写及三项附件上传，页面显示Draft saved。当前仍缺公网演示链接、视频链接及正式提交回执；草稿保存与附件上传均不等于参赛提交完成。具体操作摘要见[FORM-FILL](tasks/FORM-FILL.md)。
