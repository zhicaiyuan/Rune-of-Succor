#include "FujiSkillSubsystem.h"

#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"

namespace FujiSkills
{
	static bool Fail(FText& OutReason, const FString& Message)
	{
		OutReason = FText::FromString(Message);
		return false;
	}

	static const TCHAR* SchoolName(EFujiSkillSchool School)
	{
		switch (School)
		{
		case EFujiSkillSchool::Fire: return TEXT("火系");
		case EFujiSkillSchool::Water: return TEXT("水系");
		case EFujiSkillSchool::Wood: return TEXT("木系");
		default: return TEXT("禁术");
		}
	}

}

UFujiSkillSubsystem::UFujiSkillSubsystem()
{
	BuildCatalog();
	MakeNewState(0);
}

void UFujiSkillSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	MakeNewState(FMath::Clamp(InitialSkillPoints, 0, PointBudget));
	bInitialized = true;
	FText Reason;
	if (!CheckSaveAddress(Reason))
	{
		LastPersistenceError = Reason;
		bSaveWriteBlocked = true;
		return;
	}
	// 新档初始化不落盘；仅在第一次实际成长修改后保存。
	if (UGameplayStatics::DoesSaveGameExist(SaveSlotName, SaveUserIndex))
	{
		LoadFromSlot(Reason);
	}
}

void UFujiSkillSubsystem::Deinitialize()
{
	// 每次成功修改已即时保存，不在退出时重复覆盖或抢救坏档。
	bInitialized = false;
	Super::Deinitialize();
}

void UFujiSkillSubsystem::MakeNewState(int32 Points)
{
	State = FFujiSkillSaveData();
	State.SaveVersion = CurrentSaveVersion;
	State.GrantedPoints = Points;
	State.LearnedRanks.Add(TEXT("F1"), 1);
	State.LearnedRanks.Add(TEXT("W1"), 1);
	State.LearnedRanks.Add(TEXT("M1"), 1);
	State.EquippedSlots.Init(NAME_None, SlotCount);
}

void UFujiSkillSubsystem::NotifyChanged()
{
	if (bAutoSave && bInitialized)
	{
		FText Reason;
		SaveToSlot(Reason);
	}
	OnBuildChanged.Broadcast();
}

const FFujiSkillDefinition* UFujiSkillSubsystem::FindSkill(FName SkillId) const
{
	return Catalog.FindByPredicate([SkillId](const FFujiSkillDefinition& Item) { return Item.SkillId == SkillId; });
}

TArray<FFujiSkillDefinition> UFujiSkillSubsystem::GetAllSkills() const { return Catalog; }

bool UFujiSkillSubsystem::GetSkillDefinition(FName SkillId, FFujiSkillDefinition& OutDefinition) const
{
	if (const FFujiSkillDefinition* Definition = FindSkill(SkillId))
	{
		OutDefinition = *Definition;
		return true;
	}
	OutDefinition = FFujiSkillDefinition();
	return false;
}

int32 UFujiSkillSubsystem::RankInState(const FFujiSkillSaveData& InState, FName SkillId) const
{
	const FFujiSkillDefinition* Definition = FindSkill(SkillId);
	if (Definition && Definition->Kind == EFujiSkillKind::Mastery)
	{
		return InState.SelectedMastery == SkillId ? 1 : 0;
	}
	return InState.LearnedRanks.FindRef(SkillId);
}

int32 UFujiSkillSubsystem::SpentInState(const FFujiSkillSaveData& InState) const
{
	int32 Spent = 0;
	for (const TPair<FName, int32>& Entry : InState.LearnedRanks)
	{
		if (const FFujiSkillDefinition* Definition = FindSkill(Entry.Key))
		{
			Spent += Definition->PointCost * Entry.Value;
		}
	}
	if (const FFujiSkillDefinition* Mastery = FindSkill(InState.SelectedMastery))
	{
		Spent += Mastery->PointCost;
	}
	return Spent;
}

int32 UFujiSkillSubsystem::InvestmentInState(const FFujiSkillSaveData& InState, EFujiSkillSchool School) const
{
	int32 Investment = 0;
	for (const TPair<FName, int32>& Entry : InState.LearnedRanks)
	{
		const FFujiSkillDefinition* Definition = FindSkill(Entry.Key);
		if (Definition && Definition->School == School &&
			(Definition->Kind == EFujiSkillKind::Active || Definition->Kind == EFujiSkillKind::Passive))
		{
			Investment += Definition->PointCost * Entry.Value;
		}
	}
	return Investment;
}

int32 UFujiSkillSubsystem::GetAvailablePoints() const { return State.GrantedPoints - SpentInState(State); }
int32 UFujiSkillSubsystem::GetGrantedPoints() const { return State.GrantedPoints; }
int32 UFujiSkillSubsystem::GetSpentPoints() const { return SpentInState(State); }
int32 UFujiSkillSubsystem::GetSchoolInvestment(EFujiSkillSchool School) const { return InvestmentInState(State, School); }
int32 UFujiSkillSubsystem::GetLearnedRank(FName SkillId) const { return RankInState(State, SkillId); }
TArray<FName> UFujiSkillSubsystem::GetEquippedSlots() const { return State.EquippedSlots; }
FName UFujiSkillSubsystem::GetSelectedMastery() const { return State.SelectedMastery; }
bool UFujiSkillSubsystem::IsSkillEquipped(FName SkillId) const { return !SkillId.IsNone() && State.EquippedSlots.Contains(SkillId); }
bool UFujiSkillSubsystem::IsHiddenSkillDiscovered(FName SkillId) const { return State.DiscoveredHiddenSkills.Contains(SkillId); }
bool UFujiSkillSubsystem::IsMasteryUnlocked() const { return State.bMasteryUnlocked; }
FFujiSkillSaveData UFujiSkillSubsystem::GetSaveData() const { return State; }

bool UFujiSkillSubsystem::CheckBuildChanges(FText& OutReason) const
{
	if (!bBuildChangesAllowed) return FujiSkills::Fail(OutReason, TEXT("当前不能调整构筑，请在安全地点操作。"));
	OutReason = FText::GetEmpty();
	return true;
}

bool UFujiSkillSubsystem::CanLearnInState(const FFujiSkillSaveData& InState, const FFujiSkillDefinition& Definition, FText& OutReason) const
{
	if (RankInState(InState, Definition.SkillId) >= Definition.MaxRank)
	{
		return FujiSkills::Fail(OutReason, Definition.Kind == EFujiSkillKind::Passive ? TEXT("此被动已达到最高等级。") : TEXT("已经掌握此节点。"));
	}
	if (Definition.Kind == EFujiSkillKind::Mastery && !InState.bMasteryUnlocked)
	{
		return FujiSkills::Fail(OutReason, TEXT("需要先完成定道试炼。"));
	}
	if (InvestmentInState(InState, Definition.School) < Definition.RequiredInvestment)
	{
		return FujiSkills::Fail(OutReason, FString::Printf(TEXT("需要%s已投入%d点，不计精通费用。"), FujiSkills::SchoolName(Definition.School), Definition.RequiredInvestment));
	}
	if (!Definition.PrerequisiteAny.IsEmpty())
	{
		bool bHasPrerequisite = false;
		for (FName Prerequisite : Definition.PrerequisiteAny) bHasPrerequisite |= RankInState(InState, Prerequisite) > 0;
		if (!bHasPrerequisite) return FujiSkills::Fail(OutReason, TEXT("尚未掌握所需前置技能，满足列出的任意一项即可。"));
	}
	for (const TPair<EFujiSkillSchool, int32>& Requirement : Definition.RequiredInvestments)
	{
		if (InvestmentInState(InState, Requirement.Key) < Requirement.Value)
		{
			return FujiSkills::Fail(OutReason, FString::Printf(TEXT("需要%s已投入%d点，不计精通费用。"), FujiSkills::SchoolName(Requirement.Key), Requirement.Value));
		}
	}
	if (Definition.bRequiresDiscovery && !InState.DiscoveredHiddenSkills.Contains(Definition.SkillId))
	{
		return FujiSkills::Fail(OutReason, TEXT("尚未发现此禁印或完成对应试炼。"));
	}
	if (Definition.bRequiresMastery && InState.SelectedMastery.IsNone())
	{
		return FujiSkills::Fail(OutReason, TEXT("需要先选择一种精通。"));
	}
	int32 Refund = 0;
	if (Definition.Kind == EFujiSkillKind::Mastery)
	{
		if (const FFujiSkillDefinition* Previous = FindSkill(InState.SelectedMastery)) Refund = Previous->PointCost;
	}
	if (InState.GrantedPoints - SpentInState(InState) + Refund < Definition.PointCost)
	{
		return FujiSkills::Fail(OutReason, FString::Printf(TEXT("修习点不足，本次需要%d点。"), Definition.PointCost));
	}
	OutReason = FText::GetEmpty();
	return true;
}

FFujiSkillNodeView UFujiSkillSubsystem::GetNodeView(FName SkillId) const
{
	FFujiSkillNodeView View;
	View.SkillId = SkillId;
	const FFujiSkillDefinition* Definition = FindSkill(SkillId);
	if (!Definition)
	{
		View.BlockReason = FText::FromString(TEXT("未知技能。"));
		return View;
	}
	View.Rank = RankInState(State, SkillId);
	View.NextRankCost = Definition->PointCost;
	View.EquippedSlot = State.EquippedSlots.IndexOfByKey(SkillId);
	View.bIsEquipped = View.EquippedSlot != INDEX_NONE;
	View.bIsSelectedMastery = State.SelectedMastery == SkillId;
	View.bCanLearn = CanLearnInState(State, *Definition, View.BlockReason);
	if (View.bCanLearn) View.bCanLearn = CheckBuildChanges(View.BlockReason);
	if (View.Rank > 0)
	{
		View.State = View.bCanLearn ? EFujiSkillNodeState::UpgradeAvailable : EFujiSkillNodeState::Learned;
	}
	else
	{
		View.State = View.bCanLearn ? EFujiSkillNodeState::Learnable : EFujiSkillNodeState::Locked;
	}
	return View;
}

bool UFujiSkillSubsystem::TryLearn(FName SkillId, FText& OutReason)
{
	if (!CheckBuildChanges(OutReason)) return false;
	const FFujiSkillDefinition* Definition = FindSkill(SkillId);
	if (!Definition) return FujiSkills::Fail(OutReason, TEXT("未知技能，未扣除修习点。"));
	if (!CanLearnInState(State, *Definition, OutReason)) return false;
	if (Definition->Kind == EFujiSkillKind::Mastery) State.SelectedMastery = SkillId;
	else State.LearnedRanks.FindOrAdd(SkillId) += 1;
	// 余额根据授予点数减总投入计算，不维护易不同步的第二份余额。
	OutReason = FText::GetEmpty();
	NotifyChanged();
	return true;
}

bool UFujiSkillSubsystem::TryEquip(FName SkillId, int32 SlotIndex, FText& OutReason)
{
	if (!CheckBuildChanges(OutReason)) return false;
	if (SlotIndex < 0 || SlotIndex >= SlotCount) return FujiSkills::Fail(OutReason, TEXT("符位序号须为0至4。"));
	const FFujiSkillDefinition* Definition = FindSkill(SkillId);
	if (!Definition || (Definition->Kind != EFujiSkillKind::Active && Definition->Kind != EFujiSkillKind::Hidden))
	{
		return FujiSkills::Fail(OutReason, TEXT("只有主动技能和禁术可以装备。"));
	}
	if (RankInState(State, SkillId) <= 0) return FujiSkills::Fail(OutReason, TEXT("请先学习此技能。"));
	if (State.EquippedSlots[SlotIndex] == SkillId) return FujiSkills::Fail(OutReason, TEXT("此技能已在该符位。"));
	TArray<FName> Proposed = State.EquippedSlots;
	for (FName& Existing : Proposed) if (Existing == SkillId) Existing = NAME_None;
	Proposed[SlotIndex] = SkillId;
	int32 HiddenCount = 0;
	for (FName Existing : Proposed)
	{
		const FFujiSkillDefinition* Item = FindSkill(Existing);
		if (Item && Item->Kind == EFujiSkillKind::Hidden) ++HiddenCount;
	}
	if (HiddenCount > 1) return FujiSkills::Fail(OutReason, TEXT("最多装备一种禁术；请替换现有禁术所在符位。"));
	State.EquippedSlots = MoveTemp(Proposed);
	OutReason = FText::GetEmpty();
	NotifyChanged();
	return true;
}

bool UFujiSkillSubsystem::TryUnequip(int32 SlotIndex, FText& OutReason)
{
	if (!CheckBuildChanges(OutReason)) return false;
	if (SlotIndex < 0 || SlotIndex >= SlotCount) return FujiSkills::Fail(OutReason, TEXT("符位序号须为0至4。"));
	if (State.EquippedSlots[SlotIndex].IsNone()) return FujiSkills::Fail(OutReason, TEXT("此符位已经为空。"));
	State.EquippedSlots[SlotIndex] = NAME_None;
	OutReason = FText::GetEmpty();
	NotifyChanged();
	return true;
}

bool UFujiSkillSubsystem::TryResetBuild(FText& OutReason)
{
	if (!CheckBuildChanges(OutReason)) return false;
	const int32 Granted = State.GrantedPoints;
	const TSet<FName> Discoveries = State.DiscoveredHiddenSkills;
	const bool bUnlocked = State.bMasteryUnlocked;
	MakeNewState(Granted);
	State.DiscoveredHiddenSkills = Discoveries;
	State.bMasteryUnlocked = bUnlocked;
	OutReason = FText::GetEmpty();
	NotifyChanged();
	return true;
}

bool UFujiSkillSubsystem::GrantPoints(int32 Amount, FText& OutReason)
{
	if (Amount <= 0 || Amount > PointBudget - State.GrantedPoints)
	{
		return FujiSkills::Fail(OutReason, TEXT("授予数量必须为正，累计修习点不能超过24。"));
	}
	State.GrantedPoints += Amount;
	OutReason = FText::GetEmpty();
	NotifyChanged();
	return true;
}

bool UFujiSkillSubsystem::DiscoverSkill(FName SkillId, FText& OutReason)
{
	const FFujiSkillDefinition* Definition = FindSkill(SkillId);
	if (!Definition || Definition->Kind != EFujiSkillKind::Hidden) return FujiSkills::Fail(OutReason, TEXT("发现事件必须指定有效的禁术ID。"));
	OutReason = FText::GetEmpty();
	if (State.DiscoveredHiddenSkills.Contains(SkillId)) return true;
	State.DiscoveredHiddenSkills.Add(SkillId);
	NotifyChanged();
	return true;
}

bool UFujiSkillSubsystem::SetMasteryUnlocked(bool bUnlocked, FText& OutReason)
{
	if (!bUnlocked && !State.SelectedMastery.IsNone()) return FujiSkills::Fail(OutReason, TEXT("撤销定道资格前必须先重置构筑。"));
	OutReason = FText::GetEmpty();
	if (State.bMasteryUnlocked == bUnlocked) return true;
	State.bMasteryUnlocked = bUnlocked;
	NotifyChanged();
	return true;
}

void UFujiSkillSubsystem::SetBuildChangesAllowed(bool bAllowed)
{
	if (bBuildChangesAllowed != bAllowed)
	{
		bBuildChangesAllowed = bAllowed;
		// 场景权限不是持久化成长修改，不触发自动写档。
		OnBuildChanged.Broadcast();
	}
}

bool UFujiSkillSubsystem::ValidateSaveData(const FFujiSkillSaveData& Candidate, FText& OutReason) const
{
	if (Candidate.SaveVersion != CurrentSaveVersion) return FujiSkills::Fail(OutReason, TEXT("存档版本不受支持，未更改当前构筑。"));
	if (Candidate.GrantedPoints < 0 || Candidate.GrantedPoints > PointBudget) return FujiSkills::Fail(OutReason, TEXT("存档的总修习点超出0至24范围。"));
	if (Candidate.LearnedRanks.Num() > Catalog.Num() || Candidate.DiscoveredHiddenSkills.Num() > 6)
	{
		return FujiSkills::Fail(OutReason, TEXT("存档节点数量异常。"));
	}
	for (const TPair<FName, int32>& Entry : Candidate.LearnedRanks)
	{
		const FFujiSkillDefinition* Definition = FindSkill(Entry.Key);
		if (!Definition || Definition->Kind == EFujiSkillKind::Mastery || Entry.Value < 1 || Entry.Value > Definition->MaxRank)
		{
			return FujiSkills::Fail(OutReason, FString::Printf(TEXT("存档包含未知节点或非法等级：%s。"), *Entry.Key.ToString()));
		}
	}
	for (FName Starter : { FName(TEXT("F1")), FName(TEXT("W1")), FName(TEXT("M1")) })
	{
		if (Candidate.LearnedRanks.FindRef(Starter) != 1) return FujiSkills::Fail(OutReason, TEXT("存档缺少免费基础符。"));
	}
	for (FName Discovered : Candidate.DiscoveredHiddenSkills)
	{
		const FFujiSkillDefinition* Definition = FindSkill(Discovered);
		if (!Definition || Definition->Kind != EFujiSkillKind::Hidden) return FujiSkills::Fail(OutReason, TEXT("存档含无效禁印发现记录。"));
	}
	if (!Candidate.SelectedMastery.IsNone())
	{
		const FFujiSkillDefinition* Mastery = FindSkill(Candidate.SelectedMastery);
		if (!Mastery || Mastery->Kind != EFujiSkillKind::Mastery || !Candidate.bMasteryUnlocked)
		{
			return FujiSkills::Fail(OutReason, TEXT("存档精通或定道资格无效。"));
		}
	}
	if (SpentInState(Candidate) > Candidate.GrantedPoints) return FujiSkills::Fail(OutReason, TEXT("存档已花费点数超过授予点数。"));
	if (Candidate.EquippedSlots.Num() != SlotCount) return FujiSkills::Fail(OutReason, TEXT("存档必须恰好包含五个符位。"));
	TSet<FName> Seen;
	int32 HiddenCount = 0;
	for (FName Equipped : Candidate.EquippedSlots)
	{
		if (Equipped.IsNone()) continue;
		const FFujiSkillDefinition* Definition = FindSkill(Equipped);
		if (!Definition || (Definition->Kind != EFujiSkillKind::Active && Definition->Kind != EFujiSkillKind::Hidden) ||
			Candidate.LearnedRanks.FindRef(Equipped) != 1 || Seen.Contains(Equipped))
		{
			return FujiSkills::Fail(OutReason, TEXT("存档存在未学、重复或不可装备的节点。"));
		}
		Seen.Add(Equipped);
		if (Definition->Kind == EFujiSkillKind::Hidden) ++HiddenCount;
	}
	if (HiddenCount > 1) return FujiSkills::Fail(OutReason, TEXT("存档装备了超过一种禁术。"));

	// 从免费基础符重放学习，防止高阶节点相互凑门槛而形成不可达构筑。
	FFujiSkillSaveData Replay;
	Replay.GrantedPoints = Candidate.GrantedPoints;
	Replay.bMasteryUnlocked = Candidate.bMasteryUnlocked;
	Replay.DiscoveredHiddenSkills = Candidate.DiscoveredHiddenSkills;
	Replay.LearnedRanks.Add(TEXT("F1"), 1);
	Replay.LearnedRanks.Add(TEXT("W1"), 1);
	Replay.LearnedRanks.Add(TEXT("M1"), 1);
	bool bProgress;
	do
	{
		bProgress = false;
		for (const FFujiSkillDefinition& Definition : Catalog)
		{
			const int32 Desired = Definition.Kind == EFujiSkillKind::Mastery ? (Candidate.SelectedMastery == Definition.SkillId ? 1 : 0) : Candidate.LearnedRanks.FindRef(Definition.SkillId);
			if (RankInState(Replay, Definition.SkillId) >= Desired) continue;
			FText LearnReason;
			if (!CanLearnInState(Replay, Definition, LearnReason)) continue;
			if (Definition.Kind == EFujiSkillKind::Mastery) Replay.SelectedMastery = Definition.SkillId;
			else Replay.LearnedRanks.FindOrAdd(Definition.SkillId) += 1;
			bProgress = true;
		}
	} while (bProgress);
	for (const TPair<FName, int32>& Entry : Candidate.LearnedRanks)
	{
		if (Replay.LearnedRanks.FindRef(Entry.Key) != Entry.Value)
		{
			return FujiSkills::Fail(OutReason, FString::Printf(TEXT("存档节点不满足可达学习前置：%s。"), *Entry.Key.ToString()));
		}
	}
	if (Replay.SelectedMastery != Candidate.SelectedMastery) return FujiSkills::Fail(OutReason, TEXT("存档精通不满足本系投入门槛。"));
	OutReason = FText::GetEmpty();
	return true;
}

bool UFujiSkillSubsystem::TryImportSaveData(const FFujiSkillSaveData& Candidate, FText& OutReason)
{
	if (!ValidateSaveData(Candidate, OutReason)) return false;
	State = Candidate;
	// 导入和读档不自动写盘，以免加载动作本身覆盖原始证据。
	OnBuildChanged.Broadcast();
	return true;
}

bool UFujiSkillSubsystem::CheckSaveAddress(FText& OutReason) const
{
	if (SaveSlotName.IsEmpty() || SaveSlotName.Len() > 64 || SaveUserIndex < 0)
	{
		return FujiSkills::Fail(OutReason, TEXT("存档槽配置无效。"));
	}
	for (TCHAR Character : SaveSlotName)
	{
		if (!FChar::IsAlnum(Character) && Character != TEXT('_') && Character != TEXT('-'))
		{
			return FujiSkills::Fail(OutReason, TEXT("存档槽只能包含字母、数字、下划线和连字符。"));
		}
	}
	OutReason = FText::GetEmpty();
	return true;
}

bool UFujiSkillSubsystem::SaveToSlot(FText& OutReason)
{
	if (bSaveWriteBlocked)
	{
		return FujiSkills::Fail(OutReason, TEXT("原存档读取失败，已阻止覆盖。请先备份并检查存档，再重新启动。"));
	}
	if (!CheckSaveAddress(OutReason) || !ValidateSaveData(State, OutReason))
	{
		LastPersistenceError = OutReason;
		return false;
	}
	UFujiSkillSaveGame* Save = Cast<UFujiSkillSaveGame>(UGameplayStatics::CreateSaveGameObject(UFujiSkillSaveGame::StaticClass()));
	if (!Save)
	{
		FujiSkills::Fail(OutReason, TEXT("无法创建技能存档，当前构筑仍保留在内存中。"));
		LastPersistenceError = OutReason;
		return false;
	}
	Save->Data = State;
	if (!UGameplayStatics::SaveGameToSlot(Save, SaveSlotName, SaveUserIndex))
	{
		FujiSkills::Fail(OutReason, TEXT("技能存档写入失败，当前构筑仍保留在内存中。"));
		LastPersistenceError = OutReason;
		return false;
	}
	LastPersistenceError = FText::GetEmpty();
	OutReason = FText::GetEmpty();
	return true;
}

bool UFujiSkillSubsystem::LoadFromSlot(FText& OutReason)
{
	if (!CheckSaveAddress(OutReason))
	{
		LastPersistenceError = OutReason;
		bSaveWriteBlocked = true;
		return false;
	}
	if (!UGameplayStatics::DoesSaveGameExist(SaveSlotName, SaveUserIndex))
	{
		return FujiSkills::Fail(OutReason, TEXT("尚无技能存档，当前构筑保持不变。"));
	}
	UFujiSkillSaveGame* Save = Cast<UFujiSkillSaveGame>(UGameplayStatics::LoadGameFromSlot(SaveSlotName, SaveUserIndex));
	if (!Save || !ValidateSaveData(Save->Data, OutReason))
	{
		if (!Save) FujiSkills::Fail(OutReason, TEXT("技能存档损坏或类型不符，未重置、修复或覆盖原文件。"));
		LastPersistenceError = OutReason;
		bSaveWriteBlocked = true;
		OnBuildChanged.Broadcast();
		return false;
	}
	State = Save->Data;
	bSaveWriteBlocked = false;
	LastPersistenceError = FText::GetEmpty();
	OutReason = FText::GetEmpty();
	OnBuildChanged.Broadcast();
	return true;
}

#if !UE_BUILD_SHIPPING
static FAutoConsoleCommandWithWorldAndArgs GFujiGrantSkillPoints(
	TEXT("fuji.Skills.GrantPoints"), TEXT("授予修习点：fuji.Skills.GrantPoints 6，总预算不超过24。"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		int32 Amount = 0;
		if (Args.Num() != 1 || !LexTryParseString(Amount, *Args[0]) || !World || !World->GetGameInstance())
		{
			UE_LOG(LogTemp, Warning, TEXT("请在游戏运行时使用 fuji.Skills.GrantPoints <正整数>。"));
			return;
		}
		if (UFujiSkillSubsystem* Skills = World->GetGameInstance()->GetSubsystem<UFujiSkillSubsystem>())
		{
			FText Reason;
			if (!Skills->GrantPoints(Amount, Reason))
			{
				UE_LOG(LogTemp, Warning, TEXT("%s"), *Reason.ToString());
			}
			else
			{
				UE_LOG(LogTemp, Display, TEXT("技能修习点：已授予%d，可用%d。"), Skills->GetGrantedPoints(), Skills->GetAvailablePoints());
			}
		}
	}));
#endif

// 编译时目录在下方生成，不依赖运行环境中的JSON文件。

void UFujiSkillSubsystem::BuildCatalog()
{
    Catalog.Reset();
    Catalog.Reserve(36);
    auto Add = [this](const TCHAR* Id, const TCHAR* Name, EFujiSkillSchool School, EFujiSkillKind Kind, int32 Cost, int32 Investment, const TCHAR* Description, const TCHAR* Glyph) -> FFujiSkillDefinition&
    {
        FFujiSkillDefinition& D = Catalog.AddDefaulted_GetRef();
        D.SkillId = FName(Id); D.DisplayName = FText::FromString(Name); D.School = School; D.Kind = Kind;
        D.PointCost = Cost; D.RequiredInvestment = Investment; D.Description = FText::FromString(Description); D.Glyph = FText::FromString(Glyph);
        return D;
    };
    {
        FFujiSkillDefinition& D = Add(TEXT("F1"), TEXT("照烬符"), EFujiSkillSchool::Fire, EFujiSkillKind::Active, 0, 0, TEXT("火弹120%A，附1层烬痕"), TEXT("△＋一"));
        D.InkCost = 20;
        D.CooldownSeconds = 4.0f;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("F2"), TEXT("赤锋符"), EFujiSkillSchool::Fire, EFujiSkillKind::Active, 2, 0, TEXT("扇形火刃180%A，附1层烬痕"), TEXT("△＋竖线"));
        D.InkCost = 25;
        D.CooldownSeconds = 6.0f;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("F3"), TEXT("焚地符"), EFujiSkillSchool::Fire, EFujiSkillKind::Active, 2, 0, TEXT("首次60%A直接伤害，领域后续最多180%A，初次附1层烬痕"), TEXT("△＋×"));
        D.InkCost = 35;
        D.CooldownSeconds = 10.0f;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("F4"), TEXT("引爆符"), EFujiSkillSchool::Fire, EFujiSkillKind::Active, 3, 6, TEXT("180%A并消耗烬痕，每层另加70%A"), TEXT("△＋○"));
        D.PrerequisiteAny.Add(TEXT("F3"));
        D.InkCost = 35;
        D.CooldownSeconds = 10.0f;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("F5"), TEXT("炎龙符"), EFujiSkillSchool::Fire, EFujiSkillKind::Active, 3, 6, TEXT("路径总伤害320%A，最多附2层烬痕"), TEXT("△＋闪电"));
        D.PrerequisiteAny.Add(TEXT("F2"));
        D.InkCost = 45;
        D.CooldownSeconds = 14.0f;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("F6"), TEXT("天陨符"), EFujiSkillSchool::Fire, EFujiSkillKind::Active, 4, 10, TEXT("延迟0.9秒，范围450%A，附3层烬痕"), TEXT("△＋螺旋"));
        D.PrerequisiteAny.Add(TEXT("F4"));
        D.PrerequisiteAny.Add(TEXT("F5"));
        D.InkCost = 60;
        D.CooldownSeconds = 22.0f;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("W1"), TEXT("点澜符"), EFujiSkillSchool::Water, EFujiSkillKind::Active, 0, 0, TEXT("水弹70%A，润印6秒"), TEXT("～＋一"));
        D.InkCost = 20;
        D.CooldownSeconds = 4.0f;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("W2"), TEXT("回潮符"), EFujiSkillSchool::Water, EFujiSkillKind::Active, 2, 0, TEXT("水波100%A，润印6秒，减速20%持续3秒"), TEXT("～＋竖线"));
        D.InkCost = 25;
        D.CooldownSeconds = 8.0f;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("W3"), TEXT("水镜符"), EFujiSkillSchool::Water, EFujiSkillKind::Active, 2, 0, TEXT("12%最大生命护盾，持续6秒"), TEXT("～＋×"));
        D.InkCost = 30;
        D.CooldownSeconds = 12.0f;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("W4"), TEXT("引流符"), EFujiSkillSchool::Water, EFujiSkillKind::Active, 3, 6, TEXT("连接最多3敌6秒，受限复制25%常规直接伤害"), TEXT("～＋○"));
        D.PrerequisiteAny.Add(TEXT("W2"));
        D.InkCost = 35;
        D.CooldownSeconds = 12.0f;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("W5"), TEXT("破浪符"), EFujiSkillSchool::Water, EFujiSkillKind::Active, 3, 6, TEXT("1.2秒射流共240%A，润印8秒，下次常规法术受伤+10%"), TEXT("～＋闪电"));
        D.PrerequisiteAny.Add(TEXT("W1"));
        D.InkCost = 40;
        D.CooldownSeconds = 14.0f;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("W6"), TEXT("沧龙符"), EFujiSkillSchool::Water, EFujiSkillKind::Active, 4, 10, TEXT("范围260%A，润印8秒，受削韧+25%持续6秒"), TEXT("～＋螺旋"));
        D.PrerequisiteAny.Add(TEXT("W4"));
        D.PrerequisiteAny.Add(TEXT("W5"));
        D.InkCost = 55;
        D.CooldownSeconds = 22.0f;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("M1"), TEXT("缠枝符"), EFujiSkillSchool::Wood, EFujiSkillKind::Active, 0, 0, TEXT("藤击60%A，根缚1.2秒"), TEXT("Y＋一"));
        D.InkCost = 20;
        D.CooldownSeconds = 6.0f;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("M2"), TEXT("回生符"), EFujiSkillSchool::Wood, EFujiSkillKind::Active, 2, 0, TEXT("2秒内恢复10%最大生命"), TEXT("Y＋竖线"));
        D.InkCost = 30;
        D.CooldownSeconds = 12.0f;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("M3"), TEXT("青囿符"), EFujiSkillSchool::Wood, EFujiSkillKind::Active, 2, 0, TEXT("6秒领域每秒30%A，在阵内每秒恢复1%最大生命"), TEXT("Y＋×"));
        D.InkCost = 35;
        D.CooldownSeconds = 14.0f;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("M4"), TEXT("障林符"), EFujiSkillSchool::Wood, EFujiSkillKind::Active, 3, 6, TEXT("5秒藤障，阻挡指定投射物，初次根缚1秒"), TEXT("Y＋○"));
        D.PrerequisiteAny.Add(TEXT("M3"));
        D.InkCost = 35;
        D.CooldownSeconds = 14.0f;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("M5"), TEXT("牵藤符"), EFujiSkillSchool::Wood, EFujiSkillKind::Active, 3, 6, TEXT("最多5目标各160%A，根缚1.8秒"), TEXT("Y＋闪电"));
        D.PrerequisiteAny.Add(TEXT("M1"));
        D.InkCost = 40;
        D.CooldownSeconds = 14.0f;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("M6"), TEXT("万木符"), EFujiSkillSchool::Wood, EFujiSkillKind::Active, 4, 10, TEXT("8秒领域每秒35%A，初次根缚1.8秒，前4秒每秒恢复2%最大生命"), TEXT("Y＋螺旋"));
        D.PrerequisiteAny.Add(TEXT("M4"));
        D.PrerequisiteAny.Add(TEXT("M5"));
        D.InkCost = 55;
        D.CooldownSeconds = 24.0f;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("FP1"), TEXT("余烬"), EFujiSkillSchool::Fire, EFujiSkillKind::Passive, 1, 0, TEXT("烬痕伤害+10%／20%"), TEXT(""));
        D.MaxRank = 2;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("FP2"), TEXT("焦锋"), EFujiSkillSchool::Fire, EFujiSkillKind::Passive, 1, 4, TEXT("普攻对烬痕敌人伤害+10%／20%"), TEXT(""));
        D.MaxRank = 2;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("FP3"), TEXT("蓄炎"), EFujiSkillSchool::Fire, EFujiSkillKind::Passive, 1, 8, TEXT("3次普攻后下次常规火符+8%／16%"), TEXT(""));
        D.MaxRank = 2;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("WP1"), TEXT("长润"), EFujiSkillSchool::Water, EFujiSkillKind::Passive, 1, 0, TEXT("润印持续+1／2秒"), TEXT(""));
        D.MaxRank = 2;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("WP2"), TEXT("湿锋"), EFujiSkillSchool::Water, EFujiSkillKind::Passive, 1, 4, TEXT("普攻命中润印额外回墨+1／2，受全局上限"), TEXT(""));
        D.MaxRank = 2;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("WP3"), TEXT("涟护"), EFujiSkillSchool::Water, EFujiSkillKind::Passive, 1, 8, TEXT("常规水符给予2%／4%生命护盾，内部冷却8秒"), TEXT(""));
        D.MaxRank = 2;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("MP1"), TEXT("深根"), EFujiSkillSchool::Wood, EFujiSkillKind::Passive, 1, 0, TEXT("根缚时长+10%／20%；首领削韧+5%／10%"), TEXT(""));
        D.MaxRank = 2;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("MP2"), TEXT("回春"), EFujiSkillSchool::Wood, EFujiSkillKind::Passive, 1, 4, TEXT("木技能治疗+10%／20%"), TEXT(""));
        D.MaxRank = 2;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("MP3"), TEXT("安身"), EFujiSkillSchool::Wood, EFujiSkillKind::Passive, 1, 8, TEXT("自身木领域内减伤4%／8%"), TEXT(""));
        D.MaxRank = 2;
    }
    {
        Add(TEXT("FM"), TEXT("燎原"), EFujiSkillSchool::Fire, EFujiSkillKind::Mastery, 4, 10, TEXT("烬痕上限5；常规火直接命中每施法每目标一次刷新现有烬痕到6秒"), TEXT(""));
    }
    {
        Add(TEXT("WM"), TEXT("御澜"), EFujiSkillSchool::Water, EFujiSkillKind::Mastery, 4, 10, TEXT("润印易伤20%；水符后异系常规法术减费5，最多基础费用20%，内部冷却8秒"), TEXT(""));
    }
    {
        Add(TEXT("MM"), TEXT("长生"), EFujiSkillSchool::Wood, EFujiSkillKind::Mastery, 4, 10, TEXT("木领域与障林+2秒；溢出治疗50%转盾，本来源上限10%最大生命"), TEXT(""));
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("H1"), TEXT("蒸天劫"), EFujiSkillSchool::Forbidden, EFujiSkillKind::Hidden, 0, 0, TEXT("基础总伤害900%A；灵墨65；混沌+30"), TEXT("菱形内一点＋一"));
        D.RequiredInvestments.Add(EFujiSkillSchool::Fire, 4);
        D.RequiredInvestments.Add(EFujiSkillSchool::Water, 4);
        D.bRequiresDiscovery = true;
        D.InkCost = 65;
        D.CooldownSeconds = 24.0f;
        D.ChaosGain = 30;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("H2"), TEXT("烬木葬"), EFujiSkillSchool::Forbidden, EFujiSkillKind::Hidden, 0, 0, TEXT("基础总伤害1050%A；灵墨70；混沌+35"), TEXT("菱形内一点＋竖线"));
        D.RequiredInvestments.Add(EFujiSkillSchool::Fire, 4);
        D.RequiredInvestments.Add(EFujiSkillSchool::Wood, 4);
        D.bRequiresDiscovery = true;
        D.InkCost = 70;
        D.CooldownSeconds = 26.0f;
        D.ChaosGain = 35;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("H3"), TEXT("溟根蚀"), EFujiSkillSchool::Forbidden, EFujiSkillKind::Hidden, 0, 0, TEXT("基础总伤害900%A；灵墨65；混沌+30"), TEXT("菱形内一点＋×"));
        D.RequiredInvestments.Add(EFujiSkillSchool::Water, 4);
        D.RequiredInvestments.Add(EFujiSkillSchool::Wood, 4);
        D.bRequiresDiscovery = true;
        D.InkCost = 65;
        D.CooldownSeconds = 24.0f;
        D.ChaosGain = 30;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("H4"), TEXT("三相归墟"), EFujiSkillSchool::Forbidden, EFujiSkillKind::Hidden, 0, 0, TEXT("基础总伤害1300%A；灵墨80；混沌+40"), TEXT("菱形内一点＋○"));
        D.RequiredInvestments.Add(EFujiSkillSchool::Fire, 3);
        D.RequiredInvestments.Add(EFujiSkillSchool::Water, 3);
        D.RequiredInvestments.Add(EFujiSkillSchool::Wood, 3);
        D.bRequiresDiscovery = true;
        D.InkCost = 80;
        D.CooldownSeconds = 30.0f;
        D.ChaosGain = 40;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("H5"), TEXT("墨界断空"), EFujiSkillSchool::Forbidden, EFujiSkillKind::Hidden, 0, 0, TEXT("基础总伤害1150%A；灵墨75；混沌+35"), TEXT("菱形内一点＋闪电"));
        D.RequiredInvestments.Add(EFujiSkillSchool::Fire, 4);
        D.RequiredInvestments.Add(EFujiSkillSchool::Water, 4);
        D.RequiredInvestments.Add(EFujiSkillSchool::Wood, 3);
        D.bRequiresDiscovery = true;
        D.InkCost = 75;
        D.CooldownSeconds = 26.0f;
        D.ChaosGain = 35;
    }
    {
        FFujiSkillDefinition& D = Add(TEXT("H6"), TEXT("太初寂灭"), EFujiSkillSchool::Forbidden, EFujiSkillKind::Hidden, 0, 0, TEXT("基础总伤害1700%A；灵墨90；混沌+50"), TEXT("菱形内一点＋螺旋"));
        D.RequiredInvestments.Add(EFujiSkillSchool::Fire, 4);
        D.RequiredInvestments.Add(EFujiSkillSchool::Water, 4);
        D.RequiredInvestments.Add(EFujiSkillSchool::Wood, 4);
        D.bRequiresDiscovery = true;
        D.bRequiresMastery = true;
        D.InkCost = 90;
        D.CooldownSeconds = 36.0f;
        D.ChaosGain = 50;
    }
}
