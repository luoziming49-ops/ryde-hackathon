# T011：main 分支保护配置

2026-10-07（Asia/Singapore）· 基线修订 9，配置记录修订 10 / CP-010 · 负责人：协调助手。管理员强制遵守已关闭，普通成员保护保留；说明更新通过现有 PR 同步。

## 目标与授权范围

用户先要求公开仓库并启用强制保护，随后要求“分支保护就行了不用强制”，并明确确认：仅关闭 `Do not allow bypassing the above settings`，让管理员可无需他人批准合并；普通成员的审批、防强制推送及防删除规则保留。不付费的偏好继续有效，仓库保持 public / main。

可写范围：GitHub main 保护规则、docs/STATUS、TASKS、archive/LOG、本任务包及 T010 的配置引用、CONTRIBUTING、现有 PR #1 的说明。记录继续经 docs/public-main-protection 分支提交；本次没有合并 PR，没有改变业务阶段或开始产品开发。

## 当前规则与验收

| 规则 | 已保存配置 |
|---|---|
| 普通成员合并入口 | main 修改必须通过 Pull Request |
| 普通成员审阅 | 至少 1 名有写入权限的另一位成员批准；新增修改撤销旧批准 |
| 普通成员讨论 | 合并前解决所有审阅讨论 |
| 管理员 | 不强制遵守上方 PR、审阅等要求，可选择绕过 |
| 所有人的覆盖及删除 | 禁止强制推送、禁止删除 main |

当前没有产品代码或 CI，未要求状态检查、签名或部署。作者仍不能批准自己的 PR；管理员允许绕过审批合并，不代表已获得另一位成员的批准。普通成员保护不是仅供参考的约定，GitHub 仍强制执行。

验收要求：保存规则后重新读取，确认仅管理员强制项关闭，其余要求与表格一致，main 仍受保护；不能仅凭未保存表单或 protected 字段判断各项设置。

## 当前核验

- 在 [main 规则](https://github.com/luoziming49-ops/ryde-hackathon/settings/branch_protection_rules/84317034) 取消管理员不可绕过选项后保存；GitHub 要求邮箱身份验证，用户自行完成，未收集或记录验证码。
- GitHub 返回 `Branch protection rule settings saved.`。重新打开已保存的规则，适用于 main / 1 个分支；PR、一人批准、旧批准失效及讨论解决均启用，管理员强制项未勾选，force pushes / deletions 均未允许。
- main 接口回读 protected=true，提交仍为 f5141ecac51ee35fba58785facc0b23a2c3c069d；main 的 STATUS 仍为修订 8。PR #1 仍 open、未合并，更新前分支头为 de7ee676c36f71f908db6af0f27cd1c7694fa3f0。
- 插件的 administration 权限限制已在 CP-009 核验，完整保护字段由已保存页面回读；本次不反复请求已知无权限的接口。
- 官方 [分支保护说明](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) 确认 Free 的公开仓库可用；关闭管理员不可绕过后，管理员可绕过上方限制。强制推送与删除选项属于页面明确注明的“适用于所有人，包括管理员”规则。

## 文档交接

本地说明按修订 10 / CP-010 更新，通过 [docs/public-main-protection 分支](https://github.com/luoziming49-ops/ryde-hackathon/tree/docs/public-main-protection) 和 [PR #1](https://github.com/luoziming49-ops/ryde-hackathon/pull/1) 同步；main 的旧记录须在 PR 合并后才更新，实际规则以上述核验为准。管理员现在可自行选择合并，无需强制等待另一成员批准，本次只更新设置与 PR 说明。

此前私有仓库设置取消、公开审查和首次强制保护的历史见 [CP-008–010](../archive/LOG.md)。成员权限及共享范围见 [T010](T010-collaboration.md)，操作见 [CONTRIBUTING](../../CONTRIBUTING.md)。业务工作仍为 T009 / T004。
