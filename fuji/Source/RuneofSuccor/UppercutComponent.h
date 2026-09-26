#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "TimerManager.h"
#include "UppercutComponent.generated.h"

class AController;
class UAnimMontage;

/** 长按左键触发 Attack_Up_01；由 C++ 检测命中，避免依赖动画通知。 */
UCLASS(ClassGroup=(Combat), meta=(BlueprintSpawnableComponent))
class RUNEOFSUCCOR_API UUppercutComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UUppercutComponent();
	void OnAttackPressed();
	void OnAttackReleased();
	bool IsUppercutActive() const { return bUppercutActive; }

protected:
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	void OnHoldReached();
	void TraceUppercutHits();
	void OnUppercutMontageEnded(UAnimMontage* Montage, bool bInterrupted);
	void FinishUppercut();

	UPROPERTY(EditDefaultsOnly, Category = "Uppercut")
	TObjectPtr<UAnimMontage> UppercutMontage;

	UPROPERTY(EditDefaultsOnly, Category = "Uppercut", meta = (ClampMin = "0.1"))
	float HoldSeconds = 0.4f;

	UPROPERTY(EditDefaultsOnly, Category = "Uppercut")
	float Damage = 18.0f;

	UPROPERTY(EditDefaultsOnly, Category = "Uppercut")
	float HitRadius = 135.0f;

	UPROPERTY(EditDefaultsOnly, Category = "Uppercut")
	float HitReach = 135.0f;

	FTimerHandle HoldTimer;
	TSet<TWeakObjectPtr<AActor>> HitActors;
	TWeakObjectPtr<AController> IgnoredMoveController;
	bool bMouseHeld = false;
	bool bStartedInGroundAttackContext = false;
	bool bUppercutActive = false;
};
