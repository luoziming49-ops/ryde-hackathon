# T010：建立 GitHub 协作仓库

2026-10-06（Asia/Singapore）· 基线修订 6，交付修订 7 / CP-007 · 负责人：协调助手。仓库准备已完成；邀请待对方接受。

## 目标与范围

用户明确要求通过 GitHub 创建可多人协作的仓库，并提供 `unknownAndy123`（YAN XINYU）作为邀请对象。范围为私有仓库、现有 Markdown 文档、协作说明与模板、成员邀请及记录同步；不进行产品开发，不改变 P0/T009 的确认状态。

可写范围：README、CONTRIBUTING、.gitignore、.github 模板及 docs/STATUS、TASKS、archive/LOG、本任务包。现有业务文档只作共享前隐私检查，不改写未确认结论。

## 仓库与权限

| 项目 | 核验结果 |
|---|---|
| 仓库 | [luoziming49-ops/ryde-hackathon](https://github.com/luoziming49-ops/ryde-hackathon) |
| 可见性 / 默认分支 | private / main，已通过 GitHub 插件及网页核对 |
| 仓库所有者 | luoziming49-ops |
| 协作者 | unknownAndy123（YAN XINYU）；用户提供的用户名与 GitHub 搜索结果一致，已发出普通协作者邀请 |
| 邀请状态 | 所有者已完成邮箱身份验证；成员管理页显示 1 invitation、Pending Invite / Awaiting unknownAndy123’s response，尚未接受 |
| 分支保护 | 创建规则页明确提示当前私有仓库不会强制执行保护，需转入 GitHub Team 或 Enterprise 组织账号；本次未升级、迁移或创建不生效的规则。独立分支、PR 与另一名成员审阅目前为团队约定 |
| 本地同步方式 | 当前工作目录尚未初始化 Git；本次通过 GitHub 插件同步指定文档，后续成员可克隆仓库 |

`ryde-hackathon` 是本次协作所用仓库名，不是经确认的产品名称。用户提供的私人联系地址不写入项目记录。

## 共享范围与验收

初次共享 Markdown 项目文档及模板；不上传背景资料目录、图片核验副本、旧文档快照、系统文件、账号凭据和私人原文。现有报名来源文档为已整理摘要，保留兑换码省略说明；完整原邮件仍在用户邮箱。

- [x] 核对现有状态与真实账号，创建私有仓库及 main 初始提交。
- [x] 完成协作说明、任务和 Pull Request 模板，检查文档链接及隐私范围。
- [x] 同步 18 个 UTF-8 文件到仓库；逐项从 main 回读，18 项内容与本地一致。
- [x] 在账号验证完成后发送 unknownAndy123 邀请，核对为已发送、待接受。
- [x] 将检查点归档至 CP-007，T010 从活动索引移出，STATUS 更新为修订 7；收尾记录纳入同一批远端同步与回读。

验证记录：仓库 private / main；初始文件提交 [218a90c](https://github.com/luoziming49-ops/ryde-hackathon/commit/218a90c7fe7903a4177a0c2f52b33a0f1d8c2fbc) 的 18 文件已逐项核对；本地链接、入口预算与共享文件范围检查通过，个人联系地址未写入文档。原件链接按 README 标注仅在完整本地目录可用。

## 恢复与下一步

邀请已发出，对方需以 unknownAndy123 登录 GitHub 并接受邀请；此次不等待对方即时响应，也不重复发送。收尾时核对 main 实际记录与本地修订 7 一致；本地目录没有自动上传机制。后续业务工作仍按 T009 与 T004 的任务包接续。
