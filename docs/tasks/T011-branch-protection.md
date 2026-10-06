# T011：为 main 启用强制分支保护

2026-10-06（Asia/Singapore）· 基线修订 7，记录修订 8 / CP-008 · 负责人：协调助手。用户已取消设置，main 未启用强制保护。

## 目标与授权范围

用户明确要求添加强制分支保护。目标仓库为 [luoziming49-ops/ryde-hackathon](https://github.com/luoziming49-ops/ryde-hackathon)，保护 main；准备及保存保护规则属于本次授权，付费升级、公开仓库或迁移所有者需单独决定。产品阶段保持不变。

可写范围：GitHub main 保护规则、docs/STATUS、TASKS、archive/LOG、本任务包及 T010 的配置引用。CONTRIBUTING 仅在强制执行确实生效后更新对应说明。

## 曾准备的规则与验收（未实施）

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

当前不继续启用，也不继续核对付费流程。沿用 CONTRIBUTING 中的分支、PR 与相互审阅约定；仅在用户未来重新提出请求时再核验套餐条件。
