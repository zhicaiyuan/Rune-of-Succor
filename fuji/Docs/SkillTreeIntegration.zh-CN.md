# 技能构筑界面接入

在第三人称关卡运行游戏后按 **K** 打开技能页；再次按 K、Esc 或点击“返回”关闭。菜单打开时暂停单人游戏，关闭后恢复。画符界面占用鼠标时，不会同时打开技能菜单。

## 已接入的内容

- 复用 `/Game/UI/技能界面/WBP_技能界面` 的背景、三列技能区、点数顶栏和右侧详情区域。
- 三系共18个主动、9个被动、3个精通；另有6个混系禁术，使用独立页签查看。
- 未达条件的节点仍可选中，右侧逐项显示前置技能、投入门槛、点数及剧情条件；仅修习按钮禁用。
- 可学节点使用朱砂边，已学节点显示青色状态文字；悬停和按下样式独立于解锁状态。
- 学习完成立即更新全部节点和顶栏；重复点击不会重复扣除主动技能费用。
- 被动最多2级；5个主动符位，最多装备1个禁术；学习和装备分开。
- 选择精通需要本系投入10点、4修习点及定道资格；精通费用不计入本系投入。改修其它精通时抵回原精通4点，同时只保留一个精通。
- 禁术的0点费用不跳过发现事件和各系投入条件。
- 成长状态由 `UFujiSkillSubsystem` 统一持有，成功变更后自动保存，关掉界面不会重置。

当前接入完成的是**学习、构筑、装备记录与界面**。技能数值和效果说明来自设计目录；本次未实现36个战斗效果，也未把现有“横/竖/圆”等识别标识直接替换成元素技能ID。

## 剧情和战斗蓝图如何使用

在蓝图获取 Game Instance 的 `FujiSkillSubsystem`：

| 剧情或游戏事件 | 调用 |
|---|---|
| 发放修习点 | `GrantPoints(Amount, OutReason)`；累计上限24 |
| 发现某道禁印 | `DiscoverSkill(H1…H6, OutReason)` |
| 完成定道试炼 | `SetMasteryUnlocked(true, OutReason)` |
| 战斗中禁止改变构筑 | `SetBuildChangesAllowed(false)`；离开后恢复true |
| HUD刷新构筑 | 绑定 `OnBuildChanged`，读取 `GetEquippedSlots` |
| 符形识别完成 | 后续结合所选元素映射到技能ID，再检查 `GetLearnedRank` 和 `IsSkillEquipped` |

保留完整符形模板库做识别，再检查技能权限；不要把识别模板库缩成装备列表，否则未装备符形可能被误识别成其它技能。

## 初始点数和保存

`Config/DefaultGame.ini` 的 `[/Script/RuneofSuccor.FujiSkillSubsystem]`：

```ini
InitialSkillPoints=24
bAutoSave=True
SaveSlotName=FujiSkillProgress_v1
SaveUserIndex=0
```

24点沿用原技能蓝图的初始值，只在创建新档时生效。若改成剧情逐步授予，可调整新档初始值，并用 `GrantPoints` 发放；修改配置不会覆盖已有档。

编辑器/开发版可用控制台 `fuji.Skills.GrantPoints 6` 测试授予，累计不能超过24。正式剧情应通过蓝图发放。

存档为 `Saved/SaveGames/FujiSkillProgress_v1.sav`。加载时验证版本、点数、等级、前置可达性、符位和精通。读档失败会在页面底部显示原因并阻止覆盖；不会自动删除坏档。

## 后续调整界面

- 五个符位显示已装备技能图标与名称；卸下或重置会同步清空图标。
- 页顶“重置修习点”需再次点击“确认重置”，也可取消。返还已花费点数、清空装备和精通，保留三系基础技能、禁印发现及定道资格；成功后沿用自动存档。
- 右侧详情显示对应印头按钮与符身轨迹。印头只通过鼠标点选（不手绘）；符身只需绘制横线、竖线、叉、圆、闪电或螺旋；被动和精通标明“无需画符”。预览读取技能目录的 Glyph 字段，实际战斗识别映射仍按前述接口另行接入。
- 印头图集引用位于 Class Defaults 的 `SealAtlas`，资产为 `/Game/UI/SkillTree/Textures/T_SealSelectors`。

- 原技能Widget的父类为 `FujiSkillTreeWidget`。蓝图中的背景和布局容器保留；技能行及详情由原生类在运行时填充。
- Class Defaults 中的 `IconAtlases` 绑定六张图集；资源在 `/Game/UI/SkillTree/Textures`。
- `SkillRowHeight` 和 `BodyFontSize` 可调整行高和字号。
- `FujiSkillTreeWidget.cpp` 负责状态样式、内容区域及交互；`FujiSkillSubsystem.cpp` 负责目录和学习规则。界面不维护另一份可消费点数。
- PlayerController 只增加独立的 K 输入、Self 和 `ToggleSkillMenu` 三个节点，原有控制器业务连线保持完整。

## 验证与备份

自动化测试名称为 `Fuji.Skills`，包含学习/装备、禁术/精通、保存验证、实际技能蓝图按钮回调四组。测试使用临时GameInstance及随机测试存档槽，不修改正式进度。

运行测试时额外传入 `-FujiSkillScreenshots` 且启用渲染，可在 `Saved/SkillUIIntegration` 生成状态截图。测试报告位于该目录的 `Automation` 子目录。

原技能页和PlayerController的接入前备份位于 `Saved/SkillUIIntegration/Backup` 的时间戳目录。源码的构建配置和游戏配置也有接入前副本。备份不依赖Git，未提交或覆盖其它蓝图改动。
