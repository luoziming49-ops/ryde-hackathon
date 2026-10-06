# T011：为 main 启用强制分支保护

2026-10-06（Asia/Singapore）· 基线修订 8，配置记录修订 9 / CP-009 · 负责人：协调助手。公开与强制保护设置已生效；记录更新须经 PR 审阅后进入 main。

## 目标与授权范围

用户已明确要求将 [luoziming49-ops/ryde-hackathon](https://github.com/luoziming49-ops/ryde-hackathon) 设为公开，并为 main 开启强制保护；此前不付费的偏好继续有效。授权覆盖可见性变更与保护规则，产品阶段保持不变。

可写范围：GitHub 可见性、main 保护规则、docs/STATUS、TASKS、archive/LOG、本任务包及 T010 的配置引用、CONTRIBUTING。文档通过 docs/public-main-protection 分支和 PR 同步，不绕过已经生效的保护。

## 本次规则与验收

| 规则 | 目标 |
|---|---|
| 合并入口 | main 必须通过 Pull Request 修改 |
| 审阅 | 至少 1 名有写入权限的另一位成员批准；新增修改后旧批准失效 |
| 讨论 | 合并前解决所有审阅讨论 |
| 管理员 | 同样执行保护，不设置绕过主体 |
| 覆盖及删除 | 禁止强制推送、禁止删除 main |

当前没有产品代码或 CI，不要求尚不存在的状态检查、签名或部署。

完成条件：保护设置保存、服务端回读规则一致、GitHub 套餐支持当前可见性的强制执行；不能仅凭配置存在或 protected 字段认定已强制生效。

## 实际核验与阻塞

- 2026-10-06，GitHub main API 返回 protected=false；读取规则集 API 返回 403，并明确要求升级 GitHub Pro 或将仓库设为公开。
- 官方 [分支保护说明](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) 确认：Free 的公开仓库可用，私有仓库需要 Pro、Team 或 Enterprise。当前是个人账号仓库，无需仅为此迁入组织。
- 仓库创建页仍显示当前私有仓库规则不会强制执行。已在未保存表单中准备 main、至少一人批准、修改后重新审阅、解决讨论及管理员不绕过；未点击 Create。
- 用户随后明确表示不接受付费并取消设置。已清空分支名并撤下主要勾选项，Create 恢复禁用；服务端再次返回 protected=false。
- 本轮未购买套餐、公开或迁移仓库，未保存保护规则；T011 从活动任务索引移出，取消检查点写入 CP-008。

用户的新指令替代本任务的取消状态；旧取消检查点保留在 CP-008。

## 当前结果与验证

- 公开前检查当前 19 个文件、全部 4 次可达提交及 27 个不同版本的文件内容：未发现敏感码、私人原文、个人联系地址或被忽略的原件；来源摘要仅含主办方业务地址。提交历史包含 GitHub 记录的作者邮箱，公开前已告知用户。
- GitHub 网页完成可见性变更，仓库接口回读 visibility=public、default_branch=main；未购买套餐或迁移所有者。
- 保存经典分支保护 [main 规则](https://github.com/luoziming49-ops/ryde-hackathon/settings/branch_protection_rules/84317034)，当前适用于 1 个分支；规则重新打开后逐项读取，PR、1 人批准、旧批准失效、讨论解决及管理员不可绕过均启用，force pushes / deletions 均未允许。
- main 接口回读 protected=true。插件无 administration 权限，完整 protection 子接口返回 integration 403，因此详细字段用已经保存的 GitHub 设置页回读核验，而非将接口访问失败解释为保护未生效。
- unknownAndy123 当前权限为 write，可作为另一位审阅者。无需重复邀请。

## 文档交接

配置记录在 [docs/public-main-protection 分支](https://github.com/luoziming49-ops/ryde-hackathon/tree/docs/public-main-protection) 提交，并通过 PR 请求合入 main；本地与该分支对齐修订 9。保护启用后不能由作者自己批准并绕过合并；PR 合并前，main 的旧记录可能仍显示先前可见性和规则状态，实际设置以上述服务端和已保存页面为准。

剩余步骤为另一位成员审阅并合并记录 PR；设置本身已经生效。后续业务工作仍为 T009 / T004，不进入产品开发。
