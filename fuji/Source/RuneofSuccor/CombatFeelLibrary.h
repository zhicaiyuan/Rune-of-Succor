#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "CombatFeelLibrary.generated.h"

class UAnimMontage;
class USceneComponent;

UCLASS()
class RUNEOFSUCCOR_API UCombatFeelLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	UCombatFeelLibrary(const FObjectInitializer& ObjectInitializer);

	/** 处理空中攻击点击；返回 false 时继续原有地面连击。 */
	UFUNCTION(BlueprintCallable, meta = (WorldContext = "WorldContextObject", DisplayName = "Try Air Attack"), Category = "Combat|Air Attack")
	static bool TryAirAttack(const UObject* WorldContextObject);

	/** 供地面连击通知判断当前是否正在空中攻击。 */
	UFUNCTION(BlueprintPure, meta = (WorldContext = "WorldContextObject", DisplayName = "Is Air Attack Active"), Category = "Combat|Air Attack")
	static bool IsAirAttackActive(const UObject* WorldContextObject);

	/** 普通左键按下时启动长按计时；短按仍按原逻辑立即出招。 */
	UFUNCTION(BlueprintCallable, meta = (WorldContext = "WorldContextObject", DisplayName = "Begin Uppercut Hold"), Category = "Combat|Uppercut")
	static void BeginUppercutHold(const UObject* WorldContextObject);

	/** 左键松开时取消尚未触发的挑飞蓄按。 */
	UFUNCTION(BlueprintCallable, meta = (WorldContext = "WorldContextObject", DisplayName = "End Uppercut Hold"), Category = "Combat|Uppercut")
	static void EndUppercutHold(const UObject* WorldContextObject);

	/** 复用翻滚的八方向索引，空中改用 Dodge_Air 蒙太奇。 */
	UFUNCTION(BlueprintPure, meta = (WorldContext = "WorldContextObject", DisplayName = "Select Air Dodge Montage"), Category = "Combat|Air Dodge")
	static UAnimMontage* SelectAirDodgeMontage(
		const UObject* WorldContextObject,
		UAnimMontage* GroundMontage,
		int32 DirectionIndex
	);

	/** 空中闪避期间暂停下落，保留闪避蒙太奇的根运动。 */
	UFUNCTION(BlueprintCallable, meta = (WorldContext = "WorldContextObject", DisplayName = "Begin Air Dodge Hover"), Category = "Combat|Air Dodge")
	static UAnimMontage* BeginAirDodgeHover(const UObject* WorldContextObject, UAnimMontage* DodgeMontage);

	/** 闪避结束或被打断后恢复下落。 */
	UFUNCTION(BlueprintCallable, meta = (WorldContext = "WorldContextObject", DisplayName = "End Air Dodge Hover"), Category = "Combat|Air Dodge")
	static void EndAirDodgeHover(const UObject* WorldContextObject);

	/** 角色与目标几乎重合时保持原锁定视角，避免朝向突变。 */
	UFUNCTION(BlueprintPure, meta = (DisplayName = "Find Stable Lock On Rotation", AdvancedDisplay = "MinHorizontalDistance"), Category = "Combat|Camera")
	static FRotator FindStableLockOnRotation(
		FVector Start,
		FVector Target,
		FRotator CurrentRotation,
		float MinHorizontalDistance = 80.0f
	);

	/** Traces the current blade and the swept space between the previous and current samples. */
	UFUNCTION(
		BlueprintCallable,
		meta = (
			WorldContext = "WorldContextObject",
			DisplayName = "Assisted Melee Trace",
			AutoCreateRefTerm = "ActorsToIgnore",
			AdvancedDisplay = "bTraceComplex,ActorsToIgnore,bIgnoreSelf,AssistDistance,AssistHalfAngleDegrees"
		),
		Category = "Combat|Hit Detection"
	)
	static bool AssistedMeleeTrace(
		const UObject* WorldContextObject,
		FVector Start,
		FVector End,
		float Radius,
		const TArray<TEnumAsByte<EObjectTypeQuery>>& ObjectTypes,
		bool bTraceComplex,
		const TArray<AActor*>& ActorsToIgnore,
		bool bIgnoreSelf,
		FHitResult& OutHit,
		float AssistDistance = 210.0f,
		float AssistHalfAngleDegrees = 65.0f
	);

	/** Lets only the closest valid target continue through an execution loop. */
	UFUNCTION(
		BlueprintPure,
		meta = (
			WorldContext = "WorldContextObject",
			DisplayName = "Is Best Execution Target",
			AdvancedDisplay = "MaxDistance"
		),
		Category = "Combat|Execution"
	)
	static bool IsBestExecutionTarget(
		const UObject* WorldContextObject,
		const TArray<AActor*>& Candidates,
		AActor* Candidate,
		float MaxDistance = 240.0f
	);

	/** 一次选定成对处决动画，并缓存目标组件供根运动对齐使用。 */
	UFUNCTION(
		BlueprintCallable,
		meta = (
			WorldContext = "WorldContextObject",
			DisplayName = "Prepare Execution Pair",
			AdvancedDisplay = "IgnoreCollisionDuration"
		),
		Category = "Combat|Execution"
	)
	static bool PrepareExecutionPair(
		const UObject* WorldContextObject,
		AActor* Target,
		const TArray<UAnimMontage*>& ExecutionMontages,
		FVector& WarpLocation,
		FRotator& WarpRotation,
		USceneComponent*& WarpTargetComponent,
		AActor*& PreparedTarget,
		UAnimMontage*& SelectedMontage,
		int32& AnimationIndex,
		FName& WarpTargetName,
		float IgnoreCollisionDuration = 2.5f
	);

	/** Clamps final launch velocity and clears accumulated momentum between combo hits. */
	UFUNCTION(
		BlueprintCallable,
		meta = (
			WorldContext = "WorldContextObject",
			DisplayName = "Apply Tuned Knockback",
			AdvancedDisplay = "MaxAirborneYSpeed"
		),
		Category = "Combat|Hit Reaction"
	)
	static void ApplyTunedKnockback(
		const UObject* WorldContextObject,
		FVector RequestedVelocity,
		int32 AttackIndex,
		float MaxAirborneYSpeed = 70.0f
	);

	/** Keeps the attack lunge while reducing its translation so the blade remains in range. */
	UFUNCTION(
		BlueprintCallable,
		meta = (WorldContext = "WorldContextObject", DisplayName = "Begin Attack Root Motion"),
		Category = "Combat|Root Motion"
	)
	static void BeginAttackRootMotion(const UObject* WorldContextObject);

	/** Restores full translation for rolling, traversal and execution montages. */
	UFUNCTION(
		BlueprintCallable,
		meta = (WorldContext = "WorldContextObject", DisplayName = "End Attack Root Motion"),
		Category = "Combat|Root Motion"
	)
	static void EndAttackRootMotion(const UObject* WorldContextObject);

private:
	/** 硬引用保证八方向空中闪避蒙太奇进入打包资源。 */
	UPROPERTY(VisibleDefaultsOnly, Category = "Combat|Air Dodge")
	TArray<TObjectPtr<UAnimMontage>> AirDodgeMontages;
};
