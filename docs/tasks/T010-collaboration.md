# T010：建立 GitHub 协作仓库

2026-10-06（Asia/Singapore）· 首次交付修订 7 / CP-007，当前配置引用修订 9 / CP-009 · 负责人：协调助手。初次仓库准备已完成；后续公开与保护变更见 T011。

## 目标与范围

用户明确要求通过 GitHub 创建可多人协作的仓库，并提供 `unknownAndy123`（YAN XINYU）作为邀请对象。范围为私有仓库、现有 Markdown 文档、协作说明与模板、成员邀请及记录同步；不进行产品开发，不改变 P0/T009 的确认状态。

可写范围：README、CONTRIBUTING、.gitignore、.github 模板及 docs/STATUS、TASKS、archive/LOG、本任务包。现有业务文档只作共享前隐私检查，不改写未确认结论。

## 仓库与权限

| 项目 | 核验结果 |
|---|---|
| 仓库 | [luoziming49-ops/ryde-hackathon](https://github.com/luoziming49-ops/ryde-hackathon) |
| 可见性 / 默认分支 | public / main；后续变更与核验见 [T011](T011-branch-protection.md) |
| 仓库所有者 | luoziming49-ops |
| 协作者 | unknownAndy123（YAN XINYU）；用户提供的用户名与 GitHub 搜索结果一致，已发出普通协作者邀请 |
| 成员权限 | 最新 GitHub 权限接口确认 unknownAndy123 已具有 write，可提交分支并审阅 PR；首次邀请过程保留在 CP-007 |
| 分支保护 | main 已强制保护，实际规则及核验完整维护在 [T011](T011-branch-protection.md) |
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

成员权限已核验，不重复发送邀请。本地目录没有自动上传机制；后续记录通过分支、PR 和另一成员审阅进入受保护的 main。业务工作仍按 T009 与 T004 的任务包接续。
