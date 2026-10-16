# 2026-10-16 提交要求核验

负责人：协调助手；SUBMISSION／CP-018。用户要求“收尾工作今天项目就要提交了，先查看提交要求”。本轮只读外部页面并更新项目记录，没有填写个人资料、上传、提交、发布代码或调用模型API。

## S7：实际提交表单（2026-10-16现场读取）

- [官方赛事页](https://tch.tencentcloud.com/contest/44)列出项目提交[短链接](https://tinyurl.com/TCHackathonSGProjectSubmission)。浏览器实测跳转至[Google提交表单](https://docs.google.com/forms/d/e/1FAIpQLScr54QzuASZyUPhYYGwZ3tQ1DpU4_FEAIPsVATDrMv4I4fYbw/viewform)。
- 页面标题：TENCENT CLOUD HACKATHON SINGAPORE 2026: Project Submission。
- 表单明确：Friday, October 16, 2026, at 23:59 (GMT+8)。因此截止是2026-10-16 23:59，新加坡与北京同一时区；此证据补足旧资料缺少时刻与时区的问题。
- 表单说明：文件过大可上传至WeTransfer、Google Drive、OneDrive或其他云存储并提供公开可访问链接。这是交付方式要求，不构成本轮公开文件的授权。
- 第一页必填：Team Name、Team Captain Name、Job Title / Field of Study、Company / Institution、Team Captain Email、Team Captain Phone Number、Select Challenge Track、Which Challenge/Problem Statement Are You Participating In?。可选成员姓名与邮箱字段不用于推断允许的队伍人数。
- 本项目对应选项：Digital Native Track；Digital Native Track - Multi-Agent Autonomous Dispute Resolution System (Ryde)。未实际选择或提交。
- 点击“下一页”后，队名出现“此问题必须填写”，仍停留第一页；没有为越过校验输入虚构资料。因此未核验后续上传页的文件格式、数量、大小、描述字数、仓库权限或其他新增限制。
- 页面显示上传并提交时将记录Google账户关联资料；本记录不保存账户信息、队长联系方式或私人原文。

## 与旧资料的关系及边界

- 本表单URL与[S3旧摘要](2026-09-20-registration-review.md#s3)中被标为“报名/更新团队表单”的地址相同；截至本次读取，该地址显示项目提交表单。旧摘要保留其当时所见，不能沿用旧标签判断当前用途。
- 本次未从Outlook再次读取邮件尾部的forms.gle链接，未声称两个短链接等价。
- 重新抽取手册p38–41及p43，并渲染核对完整p40。p40明确要求原创、使用CodeBuddy或WorkBuddy、提供开发对话及至少3张聊天截图；使用证明缺失不进入评分。上方概述虽列出API日志或过程说明等证明形式，不能因此忽略表格中的截图要求。
- p39列原型、架构、现场演示和GitHub完整源码；p38明确至少两类争议、代理通信可观察，并允许模拟外部API/数据。没有把可选视频或线上项目链接改成必交。
- 官方页与手册的差异、实际表单第一屏证据已核实；未获得新的赛道详细评分细则。封面的16:9与推荐380×216仍存在比例差异，等待后续上传页核实。

## 材料盘点结果与影响

要求与材料状态只在[REQUIREMENTS](../REQUIREMENTS.md)维护；当前发布状态只在[STATUS](../STATUS.md)维护。本次只读盘点覆盖项目目录及公开GitHub元数据，未复跑应用或回归测试，也未扩大搜索至其他私人目录。

- 工作树在本轮记录修改前干净；实际HEAD为258c0c396f34b1daee080b635451a56be1a851c6，旧STATUS的3ca40cf不再是当前HEAD。
- 只读GitHub连接器确认仓库公开，搜索无MVP分支，查询该完整HEAD返回422 / No commit found；最新本地提交不能视为已交付到远端。发布前仍需协调同伴分支及PR。
- 项目目录未见CodeBuddy/WorkBuddy开发聊天截图、演示成片或公网服务地址；此结论不表示用户在其他位置没有素材。
- 当前封面/架构原稿为1920×1080 SVG。另有旧docs/cover.png，实际PNG 380×216，未经本次内容审阅。reports/assets/wb03内两个以-preview.png结尾的预览实为JPEG 1280×720，正式打包需统一后缀与实际编码。

受影响任务：SUBMISSION、T004；后续先补工具证明、发布完整源码并适配上传素材，再做可选视频或部署。截止前必须取得实际提交回执才能称正式提交完成。

## 本轮记录验证

变更文件：docs/STATUS.md、TASKS.md、REQUIREMENTS.md、sources/INDEX.md、sources/2026-10-16-submission-review.md、submission/README.md、archive/LOG.md；同名文件同步至ryde-hackathon/docs。

执行 `git -C ryde-hackathon rev-parse --short HEAD`，实际输出：

```text
258c0c3
```

执行 `git -C ryde-hackathon diff --check`，退出码0，无输出。文档校验脚本实际输出：

```text
Shared records identical: 7/7
Parent documentation links: passed
New broken links in repository mirror: 0
Pre-existing missing mirror source/archive targets: 9
STATUS budget passed: 523 Chinese characters; 1000 total characters
```

首次全链接检查在仓库副本发现9个缺失目标；与HEAD基线逐项对照，均是既有背景原件/历史快照未随代码副本携带，父目录目标齐全，本轮没有新增断链。此限制保留，不声称代码副本包含全部背景档案。没有新增产品功能，因此未新增测试或重跑应用回归；功能状态以既有验收报告为依据。
