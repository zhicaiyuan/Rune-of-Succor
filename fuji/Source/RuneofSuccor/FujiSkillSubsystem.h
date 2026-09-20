#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "FujiSkillTypes.h"
#include "FujiSkillSubsystem.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FFujiSkillBuildChanged);

/** 构筑状态唯一来源；所有界面修改均经这里验证。 */
UCLASS(Config=Game)
class RUNEOFSUCCOR_API UFujiSkillSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()
public:
	UFujiSkillSubsystem();
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	/** 只用于新档；保持工程当前原型的24点设置，可由DefaultGame.ini修改。 */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category="技能|配置") int32 InitialSkillPoints = 24;
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category="技能|配置") bool bAutoSave = true;
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category="技能|配置") FString SaveSlotName = TEXT("FujiSkillProgress_v1");
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category="技能|配置") int32 SaveUserIndex = 0;
	/** 定道试炼完成状态由剧情明确授予；原设计要求此条件。 */
	UPROPERTY(BlueprintAssignable, Category="技能") FFujiSkillBuildChanged OnBuildChanged;
	UPROPERTY(BlueprintReadOnly, Category="技能|保存") FText LastPersistenceError;
	UPROPERTY(BlueprintReadOnly, Category="技能|保存") bool bSaveWriteBlocked = false;
	UPROPERTY(BlueprintReadOnly, Category="技能") bool bBuildChangesAllowed = true;

	UFUNCTION(BlueprintPure, Category="技能") TArray<FFujiSkillDefinition> GetAllSkills() const;
	UFUNCTION(BlueprintPure, Category="技能") bool GetSkillDefinition(FName SkillId, FFujiSkillDefinition& OutDefinition) const;
	UFUNCTION(BlueprintPure, Category="技能") FFujiSkillNodeView GetNodeView(FName SkillId) const;
	UFUNCTION(BlueprintPure, Category="技能") int32 GetAvailablePoints() const;
	UFUNCTION(BlueprintPure, Category="技能") int32 GetGrantedPoints() const;
	UFUNCTION(BlueprintPure, Category="技能") int32 GetSpentPoints() const;
	UFUNCTION(BlueprintPure, Category="技能") int32 GetSchoolInvestment(EFujiSkillSchool School) const;
	UFUNCTION(BlueprintPure, Category="技能") int32 GetLearnedRank(FName SkillId) const;
	UFUNCTION(BlueprintPure, Category="技能") TArray<FName> GetEquippedSlots() const;
	UFUNCTION(BlueprintPure, Category="技能") FName GetSelectedMastery() const;
	UFUNCTION(BlueprintPure, Category="技能") bool IsSkillEquipped(FName SkillId) const;
	UFUNCTION(BlueprintPure, Category="技能") bool IsHiddenSkillDiscovered(FName SkillId) const;
	UFUNCTION(BlueprintPure, Category="技能") bool IsMasteryUnlocked() const;
	UFUNCTION(BlueprintPure, Category="技能") FFujiSkillSaveData GetSaveData() const;

	UFUNCTION(BlueprintCallable, Category="技能") bool TryLearn(FName SkillId, FText& OutReason);
	/** 槽序号0至4；已有技能移槽，目标槽原技能被替换，不允许重复装备。 */
	UFUNCTION(BlueprintCallable, Category="技能") bool TryEquip(FName SkillId, int32 SlotIndex, FText& OutReason);
	UFUNCTION(BlueprintCallable, Category="技能") bool TryUnequip(int32 SlotIndex, FText& OutReason);
	UFUNCTION(BlueprintCallable, Category="技能") bool TryResetBuild(FText& OutReason);
	UFUNCTION(BlueprintCallable, Category="技能") bool GrantPoints(int32 Amount, FText& OutReason);
	UFUNCTION(BlueprintCallable, Category="技能") bool DiscoverSkill(FName SkillId, FText& OutReason);
	UFUNCTION(BlueprintCallable, Category="技能") bool SetMasteryUnlocked(bool bUnlocked, FText& OutReason);
	UFUNCTION(BlueprintCallable, Category="技能") void SetBuildChangesAllowed(bool bAllowed);

	/** 自动读档仅在Initialize中一次；成功修改自动保存，界面无需再次保存。 */
	UFUNCTION(BlueprintCallable, Category="技能|保存") bool SaveToSlot(FText& OutReason);
	UFUNCTION(BlueprintCallable, Category="技能|保存") bool LoadFromSlot(FText& OutReason);
	/** 验证失败保持当前状态；不会重置或覆盖磁盘坏档。 */
	UFUNCTION(BlueprintCallable, Category="技能|保存") bool ValidateSaveData(const FFujiSkillSaveData& Candidate, FText& OutReason) const;
	UFUNCTION(BlueprintCallable, Category="技能|保存") bool TryImportSaveData(const FFujiSkillSaveData& Candidate, FText& OutReason);

	static constexpr int32 PointBudget = 24;
	static constexpr int32 SlotCount = 5;
	static constexpr int32 CurrentSaveVersion = 1;

private:
	UPROPERTY() FFujiSkillSaveData State;
	UPROPERTY() TArray<FFujiSkillDefinition> Catalog;
	bool bInitialized = false;

	void BuildCatalog();
	void MakeNewState(int32 Points);
	void NotifyChanged();
	const FFujiSkillDefinition* FindSkill(FName SkillId) const;
	int32 RankInState(const FFujiSkillSaveData& InState, FName SkillId) const;
	int32 SpentInState(const FFujiSkillSaveData& InState) const;
	int32 InvestmentInState(const FFujiSkillSaveData& InState, EFujiSkillSchool School) const;
	bool CanLearnInState(const FFujiSkillSaveData& InState, const FFujiSkillDefinition& Definition, FText& OutReason) const;
	bool CheckBuildChanges(FText& OutReason) const;
	bool CheckSaveAddress(FText& OutReason) const;
};
