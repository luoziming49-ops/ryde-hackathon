# 团队协作说明

项目阶段与当前任务以 [STATUS](docs/STATUS.md) 为准。先读 [AGENTS](AGENTS.md)，再按任务包打开必要资料；详细交接协议见 [WORKFLOW](docs/WORKFLOW.md#handoff)。

## 加入与开始

1. 使用自己的 GitHub 账号接受仓库邀请；成员邀请的实际状态见 [T010](docs/tasks/T010-collaboration.md)。
2. 新成员可在 GitHub 中直接编辑 Markdown 文档，也可将仓库克隆到本机：

   ```sh
   git clone https://github.com/luoziming49-ops/ryde-hackathon.git
   cd ryde-hackathon
   ```

   私有仓库需使用已获访问权限的账号登录 GitHub。不要把账号密码或访问令牌写进项目文件。

3. 在 [活动任务索引](docs/TASKS.md) 或 Issues 中确认负责人、文件范围、依赖和验收；GitHub Issue 用于沟通，任务包维护完整事实，避免复制两套状态。
4. 领取任务前与协调者核对 STATUS 修订；同一文件由一名成员负责修改。协调者维护总状态，其他成员按约定范围提交。

## 提交与审阅

1. 每项任务建立独立分支，例如 `docs/T004-resources`、`feat/T012-evidence-view`。分支名只表达任务，不代表产品方向已批准。
2. 在分支完成修改，检查受影响内容与链接。工作开始时由协调者将 STATUS 标为 `updating`。
3. 创建目标为 `main` 的 Pull Request，按模板填写任务、原因、修改范围、验证结果和遗留问题。文档任务检查事实归属、引用及未确认标记；代码任务在产品阶段允许实施后运行相关验证。
4. 邀请另一名成员审阅；收到意见后在原分支修改。审阅通过后合并，协调者归档检查点、递增修订并将 STATUS 设为 `complete`。
5. 继续下一项任务前同步最新 `main`。并发冲突由相关成员与协调者核对内容后合并，不按文件时间覆盖。

以上是团队协作约定。GitHub 是否强制审阅，取决于仓库实际启用的分支保护；实际配置见 T010。`complete` 只表示记录同步完成，不能替代产品验收。

## 资料范围

仓库暂存 Markdown 文档、任务与合并请求模板。原始手册、截图、旧文档快照、私人原文、敏感码及本地配置不上传；当前忽略清单见 [.gitignore](.gitignore)。需要引用原件时先使用已有核验摘要；确需共享的新资料应先确认可共享范围。

当前项目仍在讨论定位与范围，进入实现的条件见 WORKFLOW；建立仓库不改变阶段。
