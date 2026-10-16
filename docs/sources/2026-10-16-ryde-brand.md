# Ryde品牌与界面一手来源 · 2026-10-16

本记录仅支持本项目的视觉适配，不表示获得官方产品发布、商标授权或生产接入。

## 已查看的一手来源

- [Ryde官网](https://rydesharing.com/)：实际页面主按钮莓红背景#E93864、白字、70px胶囊圆角；页面字体Poppins、正文深灰#31373E。按钮16px/600，章节标题42px/600；这些是网页实测，不宣称是原生App设计规范。
- [Google Play官方应用页](https://play.google.com/store/apps/details?hl=en_US&id=com.rydesharing.ryde)：实际查看首页、奖励及RydeFLASH公开截图，白色界面、莓红胶囊主按钮、粉色细边选中卡片、浅粉辅助块、金额右对齐。
- [新加坡App Store](https://apps.apple.com/sg/app/ryde-ride-hailing-more/id979806982)：核对开发者为RYDE Technologies Pte Ltd及官方公开应用页。没有把商店网页字体当作原生App字体。

## 本项目适配决定（非官方规范）

品牌点缀#E93864；为白色小字对比度，主按钮用更深#C72D55（约5.34:1）；白卡片、背景#F7F7F9、文字#31373E、浅粉#FFF0F4。保留系统字体以便离线运行，不引入外部字体、App图标、官方车辆插画或完整标志。卡片12–18px圆角、细边、轻阴影；重要状态同时有文字，不能只靠颜色。

页面持续显示Hackathon prototype；Simulation/Live API仍区分。地图仅输入坐标示意，路线比率由提供里程计算，路况字段没有地图服务独立核验。双边陈述一致不等于事实已独立核验，人工复核目前仅为标记，未接入客服派单。新UI真实浏览器验收情况见本轮报告，不用官方截图代替本项目截图。
