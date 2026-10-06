# T010：建立 GitHub 协作仓库

2026-10-06（Asia/Singapore）· 基线修订 6 · 负责人：协调助手。

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
- [ ] 同步文件到仓库，回读核验内容一致。
- [x] 在账号验证完成后发送 unknownAndy123 邀请，核对为已发送、待接受。
- [ ] 将检查点归档，更新 STATUS/TASKS 并递增修订号。

## 恢复与下一步

邀请已发出，当前完成文件同步与回读核验。若中断，先核对 main 实际提交及本地 STATUS 同步标记，不重复邀请；对方需以 unknownAndy123 登录并接受邀请。后续业务工作仍按 T009 与 T004 的任务包接续。
