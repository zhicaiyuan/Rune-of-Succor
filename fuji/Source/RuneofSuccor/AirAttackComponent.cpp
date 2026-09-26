#include "AirAttackComponent.h"

#include "Algo/AllOf.h"
#include "AlphaBlend.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "Animation/AnimTypes.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "UObject/ConstructorHelpers.h"


UAirAttackComponent::UAirAttackComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.bStartWithTickEnabled = false;
	PrimaryComponentTick.TickGroup = TG_PostPhysics;
	if (HasAnyFlags(RF_ClassDefaultObject))
	{
		// 硬引用让打包包含动画，并避免第一次点击时同步加载造成卡顿。
		for (int32 Step = 1; Step <= 4; ++Step)
		{
			const FString Name = FString::Printf(TEXT("Combo_Attack_Air_06_0%d_Seq_Montage"), Step);
			const FString Path = FString::Printf(
				TEXT("/Game/Characters/\u6797\u7b26/\u52a8\u753b/Montages/\u7a7a\u4e2d\u8fde\u51fb/%s.%s"),
				*Name, *Name
			);
			ConstructorHelpers::FObjectFinder<UAnimMontage> Found(*Path);
			if (Found.Succeeded())
			{
				Montages.Add(Found.Object);
			}
		}
	}
}


bool UAirAttackComponent::LoadMontages()
{
	if (Montages.Num() == 4 && Algo::AllOf(Montages, [](const TObjectPtr<UAnimMontage>& Montage) { return IsValid(Montage); }))
	{
		return true;
	}
	Montages.Reset();
	for (int32 Step = 1; Step <= 4; ++Step)
	{
		const FString Name = FString::Printf(TEXT("Combo_Attack_Air_06_0%d_Seq_Montage"), Step);
		const FString Path = FString::Printf(
			TEXT("/Game/Characters/\u6797\u7b26/\u52a8\u753b/Montages/\u7a7a\u4e2d\u8fde\u51fb/%s.%s"),
			*Name, *Name
		);
		UAnimMontage* Montage = LoadObject<UAnimMontage>(nullptr, *Path);
		if (!IsValid(Montage))
		{
			UE_LOG(LogTemp, Warning, TEXT("Air attack montage missing: %s"), *Path);
			Montages.Reset();
			return false;
		}
		Montages.Add(Montage);
	}
	return true;
}


bool UAirAttackComponent::TryAttack()
{
	ACharacter* Character = Cast<ACharacter>(GetOwner());
	if (!IsValid(Character))
	{
		return false;
	}
	if (bDodgeActive)
	{
		return true; // 闪避期间不启动新的空中连击或地面攻击。
	}
	if (bActive)
	{
		if (CurrentStep + 1 < Montages.Num())
		{
			bNextStepQueued = true;
		}
		return true;
	}

	UCharacterMovementComponent* Movement = Character->GetCharacterMovement();
	if (!Movement || !Movement->IsFalling())
	{
		return false;
	}
	UAnimInstance* Anim = Character->GetMesh() ? Character->GetMesh()->GetAnimInstance() : nullptr;
	if (!Anim || !LoadMontages())
	{
		return true; // 空中缺少动画时也不触发地面连击。
	}

	OriginalGravityScale = Movement->GravityScale;
	bOriginalOrientRotationToMovement = Movement->bOrientRotationToMovement;
	bOriginalUseControllerDesiredRotation = Movement->bUseControllerDesiredRotation;
	Movement->GravityScale = 0.0f;
	Movement->StopMovementImmediately();
	Character->ConsumeMovementInputVector();
	Movement->SetMovementMode(MOVE_Flying);
	Movement->bOrientRotationToMovement = false;
	Movement->bUseControllerDesiredRotation = false;
	Character->SetAnimRootMotionTranslationScale(1.0f);
	if (AController* Controller = Character->GetController())
	{
		Controller->SetIgnoreMoveInput(true);
		IgnoredMoveController = Controller;
	}
	bActive = true;
	bNextStepQueued = false;
	CurrentStep = INDEX_NONE;
	SetComponentTickEnabled(true);
	if (!PlayComboStep(0))
	{
		FinishAttack();
	}
	return true;
}


bool UAirAttackComponent::BeginAirDodge(UAnimMontage* Montage)
{
	ACharacter* Character = Cast<ACharacter>(GetOwner());
	if (!IsValid(Character) || !IsValid(Montage) || bDodgeActive)
	{
		return false;
	}
	UCharacterMovementComponent* Movement = Character->GetCharacterMovement();
	if (!Movement || (!Movement->IsFalling() && !bActive))
	{
		return false;
	}
	// 先结束空中连击，避免其蒙太奇被闪避打断时再次恢复重力。
	FinishAttack();
	OriginalDodgeGravityScale = Movement->GravityScale;
	DodgeMontage = Montage;
	bDodgeActive = true;
	Movement->StopMovementImmediately();
	Movement->GravityScale = 0.0f;
	Movement->SetMovementMode(MOVE_Flying);
	Character->SetAnimRootMotionTranslationScale(AirDodgeRootMotionScale);
	SetComponentTickEnabled(true);
	return true;
}


void UAirAttackComponent::EndAirDodge()
{
	if (!bDodgeActive)
	{
		return;
	}
	bDodgeActive = false;
	DodgeMontage = nullptr;
	SetComponentTickEnabled(bActive);
	if (ACharacter* Character = Cast<ACharacter>(GetOwner()))
	{
		Character->SetAnimRootMotionTranslationScale(1.0f);
		if (UCharacterMovementComponent* Movement = Character->GetCharacterMovement())
		{
			Movement->GravityScale = OriginalDodgeGravityScale;
			if (Movement->MovementMode == MOVE_Flying)
			{
				Movement->SetMovementMode(MOVE_Falling);
			}
		}
	}
}


bool UAirAttackComponent::PlayComboStep(const int32 Step)
{
	ACharacter* Character = Cast<ACharacter>(GetOwner());
	UAnimInstance* Anim = Character && Character->GetMesh() ? Character->GetMesh()->GetAnimInstance() : nullptr;
	if (!Anim || !Montages.IsValidIndex(Step) || !IsValid(Montages[Step]))
	{
		return false;
	}
	UAnimMontage* Montage = Montages[Step];
	// 播放下一段可能同步中断上一段；先清除旧回调目标，避免误结束整个连击。
	UAnimMontage* PreviousMontage = CurrentMontage;
	CurrentMontage = nullptr;
	const float PlayedLength = Step == 0
		? Anim->Montage_Play(Montage, 1.2f)
		: Anim->Montage_PlayWithBlendIn(Montage, FAlphaBlendArgs(0.06f), 1.2f);
	if (PlayedLength <= 0.0f)
	{
		CurrentMontage = PreviousMontage;
		return false;
	}
	CurrentStep = Step;
	CurrentMontage = Montage;
	CurrentAdvanceTime = Step + 1 < Montages.Num() ? FindComboAdvanceTime(Montage) : Montage->GetPlayLength();
	FOnMontageEnded EndDelegate;
	EndDelegate.BindUObject(this, &UAirAttackComponent::OnMontageEnded);
	Anim->Montage_SetEndDelegate(EndDelegate, Montage);
	return true;
}


void UAirAttackComponent::FaceCameraDirection(const float DeltaTime)
{
	ACharacter* Character = Cast<ACharacter>(GetOwner());
	AController* Controller = Character ? Character->GetController() : nullptr;
	if (!Controller || FacingTurnRate <= 0.0f)
	{
		return;
	}
	FRotator Rotation = Character->GetActorRotation();
	Rotation.Yaw = FMath::FixedTurn(
		Rotation.Yaw,
		Controller->GetControlRotation().Yaw,
		FacingTurnRate * DeltaTime
	);
	Character->SetActorRotation(Rotation);
}


float UAirAttackComponent::FindComboAdvanceTime(const UAnimMontage* Montage) const
{
	if (!IsValid(Montage))
	{
		return 0.0f;
	}
	const float Length = Montage->GetPlayLength();
	const float BlendOutLead = Montage->BlendOutTriggerTime >= 0.0f
		? Montage->BlendOutTriggerTime
		: Montage->GetDefaultBlendOutTime() * 1.2f;
	const float LatestTime = Length - FMath::Min(Length * 0.28f, FMath::Max(0.12f, BlendOutLead + 0.03f));
	for (const FAnimNotifyEvent& Notify : Montage->Notifies)
	{
		const bool bAdvanceNotify = Notify.GetNotifyEventName().ToString().Contains(TEXT("下一连击"))
			|| (Notify.Notify && Notify.Notify->GetClass()->GetName().Contains(TEXT("下一连击")));
		if (bAdvanceNotify)
		{
			const float NotifyTime = Notify.GetTriggerTime();
			if (NotifyTime > LatestTime)
			{
				UE_LOG(LogTemp, Warning, TEXT("Air combo notify is after blend-out window: %s at %.2fs, using %.2fs"),
					*Montage->GetName(), NotifyTime, LatestTime);
			}
			return FMath::Clamp(NotifyTime, 0.0f, LatestTime);
		}
	}
	UE_LOG(LogTemp, Warning, TEXT("Air combo has no next-combo notify: %s, using %.2fs"),
		*Montage->GetName(), LatestTime);
	return LatestTime;
}


void UAirAttackComponent::OnMontageEnded(UAnimMontage* Montage, const bool bInterrupted)
{
	if (!bActive || Montage != CurrentMontage)
	{
		return;
	}
	if (!bInterrupted && bNextStepQueued && CurrentStep + 1 < Montages.Num())
	{
		bNextStepQueued = false;
		if (PlayComboStep(CurrentStep + 1))
		{
			return;
		}
	}
	FinishAttack();
}


void UAirAttackComponent::TickComponent(
	const float DeltaTime,
	const ELevelTick TickType,
	FActorComponentTickFunction* ThisTickFunction
)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	ACharacter* Character = Cast<ACharacter>(GetOwner());
	if (bDodgeActive)
	{
		UCharacterMovementComponent* Movement = IsValid(Character) ? Character->GetCharacterMovement() : nullptr;
		UAnimInstance* Anim = IsValid(Character) && Character->GetMesh()
			? Character->GetMesh()->GetAnimInstance() : nullptr;
		if (!Movement || Movement->MovementMode != MOVE_Flying || !Anim
			|| !Anim->Montage_IsActive(DodgeMontage))
		{
			EndAirDodge();
		}
		return;
	}
	if (!bActive || !IsValid(Character))
	{
		return;
	}
	UCharacterMovementComponent* Movement = Character->GetCharacterMovement();
	if (!Movement || Movement->MovementMode != MOVE_Flying)
	{
		FinishAttack();
		return;
	}
	FaceCameraDirection(DeltaTime);
	if (bNextStepQueued && CurrentStep + 1 < Montages.Num() && IsValid(CurrentMontage))
	{
		UAnimInstance* Anim = Character->GetMesh() ? Character->GetMesh()->GetAnimInstance() : nullptr;
		if (Anim && Anim->Montage_IsPlaying(CurrentMontage)
			&& Anim->Montage_GetPosition(CurrentMontage) >= CurrentAdvanceTime)
		{
			bNextStepQueued = false;
			if (!PlayComboStep(CurrentStep + 1))
			{
				FinishAttack();
			}
			return;
		}
	}
}


void UAirAttackComponent::FinishAttack()
{
	if (!bActive)
	{
		return;
	}
	bActive = false;
	bNextStepQueued = false;
	CurrentStep = INDEX_NONE;
	CurrentAdvanceTime = 0.0f;
	CurrentMontage = nullptr;
	SetComponentTickEnabled(false);
	if (IgnoredMoveController.IsValid())
	{
		IgnoredMoveController->SetIgnoreMoveInput(false);
	}
	IgnoredMoveController.Reset();
	if (ACharacter* Character = Cast<ACharacter>(GetOwner()))
	{
		if (UCharacterMovementComponent* Movement = Character->GetCharacterMovement())
		{
			Movement->GravityScale = OriginalGravityScale;
			Movement->bOrientRotationToMovement = bOriginalOrientRotationToMovement;
			Movement->bUseControllerDesiredRotation = bOriginalUseControllerDesiredRotation;
			if (Movement->MovementMode == MOVE_Flying)
			{
				Movement->SetMovementMode(MOVE_Falling);
			}
		}
	}
}


void UAirAttackComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	EndAirDodge();
	FinishAttack();
	Super::EndPlay(EndPlayReason);
}
