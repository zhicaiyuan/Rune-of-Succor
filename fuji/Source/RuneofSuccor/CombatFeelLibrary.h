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
	/** Holds the previous lock-on view direction when target and player nearly coincide. */
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
			DisplayName = "Apply Tuned Knockback"
		),
		Category = "Combat|Hit Reaction"
	)
	static void ApplyTunedKnockback(
		const UObject* WorldContextObject,
		FVector RequestedVelocity,
		int32 AttackIndex
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
};
