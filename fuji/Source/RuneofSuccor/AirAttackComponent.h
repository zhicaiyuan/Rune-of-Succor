#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "AirAttackComponent.generated.h"

class ACharacter;
class AController;
class UAnimInstance;
class UAnimMontage;
class UCharacterMovementComponent;

/** 管理 Air 06 四段连击，保留动画根运动，并在连击结束后恢复下落。 */
UCLASS(ClassGroup=(Combat), meta=(BlueprintSpawnableComponent))
class RUNEOFSUCCOR_API UAirAttackComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UAirAttackComponent();

	/** 本次点击由空中攻击处理时返回 true。 */
	bool TryAttack();
	bool IsAirAttackActive() const { return bActive; }
	int32 GetCurrentStep() const { return CurrentStep; }
	bool BeginAirDodge(UAnimMontage* Montage);
	void EndAirDodge();

protected:
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	bool LoadMontages();
	bool PlayComboStep(int32 Step);
	void FaceCameraDirection(float DeltaTime);
	float FindComboAdvanceTime(const UAnimMontage* Montage) const;
	void OnMontageEnded(UAnimMontage* Montage, bool bInterrupted);
	void FinishAttack();

	UPROPERTY(EditDefaultsOnly, Category = "Air Attack")
	TArray<TObjectPtr<UAnimMontage>> Montages;

	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> CurrentMontage;
	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> DodgeMontage;

	/** 空中攻击期间朝镜头方向转身的最大角速度。 */
	UPROPERTY(EditDefaultsOnly, Category = "Air Attack", meta = (ClampMin = "0.0"))
	float FacingTurnRate = 360.0f;

	/** 空中闪避的根运动位移比例，保留八方向但缩短飞行距离。 */
	UPROPERTY(EditDefaultsOnly, Category = "Air Dodge", meta = (ClampMin = "0.1", ClampMax = "1.0"))
	float AirDodgeRootMotionScale = 0.65f;

	int32 CurrentStep = INDEX_NONE;
	float OriginalGravityScale = 1.0f;
	float OriginalDodgeGravityScale = 1.0f;
	float CurrentAdvanceTime = 0.0f;
	bool bActive = false;
	bool bDodgeActive = false;
	bool bNextStepQueued = false;
	bool bOriginalOrientRotationToMovement = false;
	bool bOriginalUseControllerDesiredRotation = false;
	TWeakObjectPtr<AController> IgnoredMoveController;
};
