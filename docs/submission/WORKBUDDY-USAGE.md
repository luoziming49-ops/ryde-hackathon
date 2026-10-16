# WorkBuddy 使用说明与采用记录

2026-10-16收到用户提供的3张对话截图，已逐张查看。三图均可辨认WorkBuddy、用户任务及部分回答；是局部画面，不据此推断不可见的完整对话、执行时间或结果。原始文件保留不变，并原样复制为下列提交文件。截图不进入公开源码，随本地独立的 `WorkBuddy-Usage-Evidence-2026-10-16.zip` 提交；包内MANIFEST.json提供原名、尺寸和SHA256。

## 文件与实际采用

| 文件 | 可见任务及输出 | 核对与采用情况 |
|---|---|---|
| `workbuddy-01-input-robustness.png` | 早期P1.5输入健壮性任务交流及报告片段；任务涉及错误类型输入、HTTP 500及新增测试 | 保留为历史工具使用记录。截图列出的4个测试名在当前仓库及可达Git历史中未精确找到；现有相关检查不能因此归为WorkBuddy所写。本轮未据该图改代码，不把回复的“完成/真实输出”当作独立验证。 |
| `workbuddy-02-demo-checklist.png` | 演示核对表草拟；可见答复称12项，右侧显示演示前部分内容 | 仓库未收到完整原始DEMO-CHECKLIST.md。只将可见的模拟模式、0001未知金额、合成样例边界三项整理加入[演示脚本](DEMO.md#演示前快速核对)，保留未勾选，不声称已彩排或采用完整12项原稿。 |
| `workbuddy-03-ui-review.png` | 对所附界面截图作静态可读性审核；可见答复指出当时画面未显示运行结果，部分内容无法评价 | 保留为静态审核及覆盖范围记录。未据不可见的后续建议改UI；不将该截图当作键盘、下载、屏幕阅读器、模型调用或完整视觉验收证明。 |

上述核对由协调助手逐图及对照项目文件完成；收到时间不是对话执行时间。三个附件不等同于[预备提示词](WORKBUDDY-PROMPTS.md)中的三个新任务都完成，目前没有提交文案准确性审核任务的对应截图。

## 可粘贴的英文使用说明

WorkBuddy was used for an early input-robustness task discussion, demo-checklist drafting, and static UI screenshot review. Three supplied screenshots show the user requests and portions of WorkBuddy's responses.

We incorporated the visible pre-demo checks into the demo script: confirm Simulation mode, keep the unresolved amount in case 0001 distinct from zero, and identify synthetic cases clearly. The original twelve-item checklist file was not supplied, so we do not claim to have adopted the complete original output. The UI review is retained as a static review record. The historical robustness report is retained as a conversation record, not independent proof of current test results or code authorship.

Contribution scope: input-robustness task assistance and submission preparation. These screenshots do not establish that WorkBuddy developed the entire system or completed browser validation.

## 提交方式与剩余边界

可在官方表单的工具使用证明位置逐张上传3个PNG，并粘贴上述使用说明；若入口支持附件包，可使用独立证明ZIP。上传格式、大小和数量的最终限制仍须在官方表单确认。源码ZIP与证明ZIP相互独立，上传源码不能替代上传截图。

截图数量及可辨认内容已核对，最终是否满足赛事对使用范围和证明完整性的要求由主办方判断；不写成资格已获认可。团队资料、正式提交与回执仍需完成，见[提交要求](../REQUIREMENTS.md)。
