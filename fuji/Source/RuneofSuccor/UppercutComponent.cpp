#include "UppercutComponent.h"
#include "AirAttackComponent.h"

#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"


namespace
{
	constexpr const TCHAR* UppercutAssetPath =
		TEXT("/Game/Characters/\u6797\u7b26/\u52a8\u753b/Montages/\u51fb\u98de/Attack_Up_01_Seq_Montage.Attack_Up_01_Seq_Montage");
}


UUppercutComponent::UUppercutComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.bStartWithTickEnabled = false;
	PrimaryComponentTick.TickGroup = TG_PostPhysics;
	if (HasAnyFlags(RF_ClassDefaultObject))
	{
		ConstructorHelpers::FObjectFinder<UAnimMontage> Found(UppercutAssetPath);
		if (Found.Succeeded())
		{
			UppercutMontage = Found.Object;
		}
	}
}


void UUppercutComponent::OnAttackPressed()
{
	bMouseHeld = true;
	const ACharacter* Character = Cast<ACharacter>(GetOwner());
	const UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
	const UAnimInstance* Anim = Character && Character->GetMesh() ? Character->GetMesh()->GetAnimInstance() : nullptr;
	const UAnimMontage* CurrentMontage = Anim ? Anim->GetCurrentActiveMontage() : nullptr;
	bStartedInGroundAttackContext = Movement && (Movement->IsMovingOnGround()
		|| (CurrentMontage && CurrentMontage->GetName().Contains(TEXT("Combo_Attack_03"))));
	if (bUppercutActive)
	{
		return;
	}
	if (!bStartedInGroundAttackContext)
	{
		return;
	}
	if (!IsValid(UppercutMontage))
	{
		UppercutMontage = LoadObject<UAnimMontage>(nullptr, UppercutAssetPath);
	}
	if (!IsValid(UppercutMontage) || !GetWorld())
	{
		UE_LOG(LogTemp, Warning, TEXT("Uppercut hold could not start: Attack_Up_01 montage is missing"));
		return;
	}
	GetWorld()->GetTimerManager().SetTimer(
		HoldTimer, this, &UUppercutComponent::OnHoldReached, HoldSeconds, false
	);
	UE_LOG(LogTemp, Log, TEXT("Uppercut hold armed for %.2fs; press movement mode=%d"),
		HoldSeconds, Movement ? int32(Movement->MovementMode) : -1);
}


void UUppercutComponent::OnAttackReleased()
{
	bMouseHeld = false;
	bStartedInGroundAttackContext = false;
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(HoldTimer);
	}
}


void UUppercutComponent::OnHoldReached()
{
	ACharacter* Character = Cast<ACharacter>(GetOwner());
	UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
	UAnimInstance* Anim = Character && Character->GetMesh() ? Character->GetMesh()->GetAnimInstance() : nullptr;
	const UAirAttackComponent* AirAttack = Character ? Character->FindComponentByClass<UAirAttackComponent>() : nullptr;
	if (!bMouseHeld || !bStartedInGroundAttackContext || bUppercutActive || !IsValid(UppercutMontage)
		|| !Movement || !Anim || (AirAttack && AirAttack->IsAirAttackActive()))
	{
		UE_LOG(LogTemp, Log, TEXT("Uppercut hold skipped: held=%d startedGround=%d active=%d mode=%d montage=%d anim=%d"),
			bMouseHeld, bStartedInGroundAttackContext, bUppercutActive,
			Movement ? int32(Movement->MovementMode) : -1, IsValid(UppercutMontage), Anim != nullptr);
		return;
	}
	if (const UAnimMontage* CurrentMontage = Anim->GetCurrentActiveMontage())
	{
		const FString Name = CurrentMontage->GetName();
		if (Name.Contains(TEXT("Dodge")) || Name.Contains(TEXT("Roll"))
			|| Name.Contains(TEXT("Execution")) || Name.Contains(TEXT("Execute"))
			|| Name.Contains(TEXT("Die")) || Name.Contains(TEXT("\u5904\u51b3"))
			|| Name.Contains(TEXT("Traversal")))
		{
			return;
		}
	}

	// 原普通攻击已经在按下时开始，长按成立后先结束剑追踪并清掉连击缓存。
	for (UActorComponent* Component : Character->GetComponents())
	{
		if (Component && Component->GetClass()->GetName().Contains(TEXT("BPC_\u653b\u51fb\u7cfb\u7edf")))
		{
			if (UFunction* StopSwordTrace = Component->FindFunction(TEXT("\u505c\u6b62\u5251\u8ffd\u8e2a")))
			{
				Component->ProcessEvent(StopSwordTrace, nullptr);
			}
			if (UFunction* EndGroundCombo = Component->FindFunction(TEXT("\u7ec8\u6b62\u666e\u901a\u653b\u51fb\u8fde\u51fb")))
			{
				Component->ProcessEvent(EndGroundCombo, nullptr);
			}
			break;
		}
	}
	if (Anim->Montage_Play(UppercutMontage) <= 0.0f)
	{
		UE_LOG(LogTemp, Warning, TEXT("Uppercut hold reached but Attack_Up_01 montage failed to play"));
		return;
	}
	UE_LOG(LogTemp, Log, TEXT("Uppercut Attack_Up_01 started after %.2fs hold"), HoldSeconds);
	bUppercutActive = true;
	HitActors.Reset();
	Movement->StopMovementImmediately();
	Character->SetAnimRootMotionTranslationScale(1.0f);
	if (AController* Controller = Character->GetController())
	{
		Controller->SetIgnoreMoveInput(true);
		IgnoredMoveController = Controller;
	}
	FOnMontageEnded EndDelegate;
	EndDelegate.BindUObject(this, &UUppercutComponent::OnUppercutMontageEnded);
	Anim->Montage_SetEndDelegate(EndDelegate, UppercutMontage);
	SetComponentTickEnabled(true);
}


void UUppercutComponent::TraceUppercutHits()
{
	ACharacter* Character = Cast<ACharacter>(GetOwner());
	UWorld* World = GetWorld();
	if (!IsValid(Character) || !World)
	{
		return;
	}
	const FVector Center = Character->GetActorLocation()
		+ Character->GetActorForwardVector() * HitReach + FVector::UpVector * 35.0f;
	FCollisionObjectQueryParams ObjectParams;
	ObjectParams.AddObjectTypesToQuery(ECC_Pawn);
	FCollisionQueryParams QueryParams(SCENE_QUERY_STAT(Uppercut), false, Character);
	TArray<FOverlapResult> Overlaps;
	World->OverlapMultiByObjectType(
		Overlaps, Center, FQuat::Identity, ObjectParams,
		FCollisionShape::MakeSphere(HitRadius), QueryParams
	);
	for (const FOverlapResult& Overlap : Overlaps)
	{
		AActor* Target = Overlap.GetActor();
		const TWeakObjectPtr<AActor> WeakTarget(Target);
		if (!IsValid(Target) || Target == Character || !Target->ActorHasTag(TEXT("\u53ef\u653b\u51fb\u7684"))
			|| HitActors.Contains(WeakTarget))
		{
			continue;
		}
		HitActors.Add(WeakTarget);
		UGameplayStatics::ApplyDamage(Target, Damage, Character->GetController(), Character, nullptr);
	}
}


void UUppercutComponent::TickComponent(
	const float DeltaTime, const ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction
)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	ACharacter* Character = Cast<ACharacter>(GetOwner());
	UAnimInstance* Anim = Character && Character->GetMesh() ? Character->GetMesh()->GetAnimInstance() : nullptr;
	if (!bUppercutActive || !Anim || !Anim->Montage_IsActive(UppercutMontage))
	{
		FinishUppercut();
		return;
	}
	const float Position = Anim->Montage_GetPosition(UppercutMontage);
	const float Length = UppercutMontage->GetPlayLength();
	if (Position >= Length * 0.28f && Position <= Length * 0.72f)
	{
		TraceUppercutHits();
	}
}


void UUppercutComponent::OnUppercutMontageEnded(UAnimMontage* Montage, const bool bInterrupted)
{
	if (Montage == UppercutMontage)
	{
		FinishUppercut();
	}
}


void UUppercutComponent::FinishUppercut()
{
	if (!bUppercutActive)
	{
		return;
	}
	bUppercutActive = false;
	HitActors.Reset();
	SetComponentTickEnabled(false);
	if (IgnoredMoveController.IsValid())
	{
		IgnoredMoveController->SetIgnoreMoveInput(false);
	}
	IgnoredMoveController.Reset();
	if (ACharacter* Character = Cast<ACharacter>(GetOwner()))
	{
		Character->SetAnimRootMotionTranslationScale(1.0f);
	}
}


void UUppercutComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	OnAttackReleased();
	FinishUppercut();
	Super::EndPlay(EndPlayReason);
}
