#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "FujiSkillTypes.generated.h"

UENUM(BlueprintType)
enum class EFujiSkillSchool : uint8 { Fire, Water, Wood, Forbidden };

UENUM(BlueprintType)
enum class EFujiSkillKind : uint8 { Active, Passive, Mastery, Hidden };

UENUM(BlueprintType)
enum class EFujiSkillNodeState : uint8 { Locked, Learnable, Learned, UpgradeAvailable };

/** 技能说明与学习条件；数值仅供界面展示，不执行战斗效果。 */
USTRUCT(BlueprintType)
struct RUNEOFSUCCOR_API FFujiSkillDefinition
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly) FName SkillId;
	UPROPERTY(BlueprintReadOnly) FText DisplayName;
	UPROPERTY(BlueprintReadOnly) EFujiSkillSchool School = EFujiSkillSchool::Fire;
	UPROPERTY(BlueprintReadOnly) EFujiSkillKind Kind = EFujiSkillKind::Active;
	UPROPERTY(BlueprintReadOnly) int32 PointCost = 0;
	UPROPERTY(BlueprintReadOnly) int32 MaxRank = 1;
	UPROPERTY(BlueprintReadOnly) int32 RequiredInvestment = 0;
	UPROPERTY(BlueprintReadOnly) TArray<FName> PrerequisiteAny;
	UPROPERTY(BlueprintReadOnly) TMap<EFujiSkillSchool, int32> RequiredInvestments;
	UPROPERTY(BlueprintReadOnly) bool bRequiresDiscovery = false;
	UPROPERTY(BlueprintReadOnly) bool bRequiresMastery = false;
	UPROPERTY(BlueprintReadOnly) FText Glyph;
	UPROPERTY(BlueprintReadOnly) FText Description;
	UPROPERTY(BlueprintReadOnly) int32 InkCost = 0;
	UPROPERTY(BlueprintReadOnly) float CooldownSeconds = 0.0f;
	UPROPERTY(BlueprintReadOnly) int32 ChaosGain = 0;
};

USTRUCT(BlueprintType)
struct RUNEOFSUCCOR_API FFujiSkillNodeView
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly) FName SkillId;
	UPROPERTY(BlueprintReadOnly) EFujiSkillNodeState State = EFujiSkillNodeState::Locked;
	UPROPERTY(BlueprintReadOnly) int32 Rank = 0;
	UPROPERTY(BlueprintReadOnly) int32 NextRankCost = 0;
	UPROPERTY(BlueprintReadOnly) bool bCanLearn = false;
	UPROPERTY(BlueprintReadOnly) bool bIsEquipped = false;
	UPROPERTY(BlueprintReadOnly) bool bIsSelectedMastery = false;
	UPROPERTY(BlueprintReadOnly) int32 EquippedSlot = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly) FText BlockReason;
};

/** 仅持久化成长状态，不包含生命、灵墨、冷却或战斗混沌。 */
USTRUCT(BlueprintType)
struct RUNEOFSUCCOR_API FFujiSkillSaveData
{
	GENERATED_BODY()
	UPROPERTY(SaveGame, BlueprintReadWrite) int32 SaveVersion = 1;
	UPROPERTY(SaveGame, BlueprintReadWrite) int32 GrantedPoints = 0;
	UPROPERTY(SaveGame, BlueprintReadWrite) TMap<FName, int32> LearnedRanks;
	UPROPERTY(SaveGame, BlueprintReadWrite) TArray<FName> EquippedSlots;
	UPROPERTY(SaveGame, BlueprintReadWrite) FName SelectedMastery;
	UPROPERTY(SaveGame, BlueprintReadWrite) TSet<FName> DiscoveredHiddenSkills;
	UPROPERTY(SaveGame, BlueprintReadWrite) bool bMasteryUnlocked = false;
};

UCLASS()
class RUNEOFSUCCOR_API UFujiSkillSaveGame : public USaveGame
{
	GENERATED_BODY()
public:
	UPROPERTY(SaveGame) FFujiSkillSaveData Data;
};
