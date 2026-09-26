#include "CombatFeelLibrary.h"
#include "AirAttackComponent.h"
#include "UppercutComponent.h"

#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "AnimNotifyState_MotionWarping.h"
#include "Components/ActorComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Math/RotationMatrix.h"
#include "RootMotionModifier.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#endif


namespace CombatFeel
{
	struct FBladeTraceHistory
	{
		FVector Start = FVector::ZeroVector;
		FVector End = FVector::ZeroVector;
		double TimeSeconds = 0.0;
		TWeakObjectPtr<UWorld> World;
	};

	TMap<TWeakObjectPtr<UObject>, FBladeTraceHistory> BladeTraceHistories;

	AActor* ResolveAttacker(const UObject* WorldContextObject)
	{
		if (AActor* Actor = const_cast<AActor*>(Cast<AActor>(WorldContextObject)))
		{
			return Actor;
		}
		if (const UActorComponent* Component = Cast<UActorComponent>(WorldContextObject))
		{
			return Component->GetOwner();
		}
		return nullptr;
	}

	bool IsInsideAssistCone(
		const FVector& Origin,
		const FVector& Forward,
		const FVector& Target,
		const float MaxDistance,
		const float MinForwardDot
	)
	{
		const FVector Delta = Target - Origin;
		const FVector FlatDelta(Delta.X, Delta.Y, 0.0);
		const double Distance = FlatDelta.Length();
		if (Distance <= UE_DOUBLE_SMALL_NUMBER || Distance > MaxDistance || FMath::Abs(Delta.Z) > 120.0)
		{
			return false;
		}
		return FVector::DotProduct(Forward.GetSafeNormal2D(), FlatDelta / Distance) >= MinForwardDot;
	}

	bool TraceSegment(
		const UObject* WorldContextObject,
		const FVector& Start,
		const FVector& End,
		const float Radius,
		const TArray<TEnumAsByte<EObjectTypeQuery>>& ObjectTypes,
		const bool bTraceComplex,
		const TArray<AActor*>& ActorsToIgnore,
		const bool bIgnoreSelf,
		FHitResult& OutHit
	)
	{
		return UKismetSystemLibrary::SphereTraceSingleForObjects(
			WorldContextObject,
			Start,
			End,
			Radius,
			ObjectTypes,
			bTraceComplex,
			ActorsToIgnore,
			EDrawDebugTrace::None,
			OutHit,
			bIgnoreSelf
		);
	}

	double ExecutionScore(const AActor* Executor, const AActor* Target)
	{
		const FVector Delta = Executor->GetActorLocation() - Target->GetActorLocation();
		const double Distance = Delta.Size2D();
		const double TargetFacingExecutor = FVector::DotProduct(
			Target->GetActorForwardVector().GetSafeNormal2D(),
			Delta.GetSafeNormal2D()
		);
		// Prefer a target whose back faces the executor, while distance remains dominant.
		return Distance + FMath::Max(0.0, TargetFacingExecutor + 0.15) * 90.0;
	}

	bool ImplementsExecutionInterface(const AActor* Actor)
	{
		static TWeakObjectPtr<UClass> CachedInterface;
		UClass* InterfaceClass = CachedInterface.Get();
		if (!InterfaceClass)
		{
			InterfaceClass = LoadObject<UClass>(
				nullptr,
				TEXT("/Game/\u84DD\u56FE/BPI_\u6697\u6740.BPI_\u6697\u6740_C")
			);
			CachedInterface = InterfaceClass;
		}
		return Actor && InterfaceClass && Actor->GetClass()->ImplementsInterface(InterfaceClass);
	}

	void SetPairMoveIgnore(AActor* First, AActor* Second, const bool bIgnore)
	{
		if (First && Second)
		{
			if (UPrimitiveComponent* RootPrimitive = Cast<UPrimitiveComponent>(First->GetRootComponent()))
			{
				RootPrimitive->IgnoreActorWhenMoving(Second, bIgnore);
			}
		}
	}
}


UCombatFeelLibrary::UCombatFeelLibrary(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	if (!HasAnyFlags(RF_ClassDefaultObject))
	{
		return;
	}
	static const TCHAR* Directions[] = {
		TEXT("F"), TEXT("F_R_45"), TEXT("R"), TEXT("B_R_45"),
		TEXT("B"), TEXT("B_L_45"), TEXT("L"), TEXT("F_L_45")
	};
	AirDodgeMontages.SetNum(UE_ARRAY_COUNT(Directions));
	for (int32 Index = 0; Index < UE_ARRAY_COUNT(Directions); ++Index)
	{
		const FString Name = FString::Printf(TEXT("Dodge_Air_%s_Seq_Montage"), Directions[Index]);
		const FString Path = FString::Printf(
			TEXT("/Game/Characters/\u6797\u7b26/\u52a8\u753b/Montages/\u7a7a\u4e2d\u95ea\u907f/%s.%s"),
			*Name, *Name
		);
		ConstructorHelpers::FObjectFinder<UAnimMontage> Found(*Path);
		if (Found.Succeeded())
		{
			AirDodgeMontages[Index] = Found.Object;
		}
	}
}


bool UCombatFeelLibrary::TryAirAttack(const UObject* WorldContextObject)
{
	ACharacter* Character = Cast<ACharacter>(CombatFeel::ResolveAttacker(WorldContextObject));
	if (!IsValid(Character))
	{
		return false;
	}
	const UUppercutComponent* Uppercut = Character->FindComponentByClass<UUppercutComponent>();
	if (Uppercut && Uppercut->IsUppercutActive())
	{
		return true; // 挑飞动画期间吸收重复左键，避免普通连击打断。
	}
	UAirAttackComponent* AirAttack = Character->FindComponentByClass<UAirAttackComponent>();
	if (!AirAttack)
	{
		AirAttack = NewObject<UAirAttackComponent>(Character, TEXT("AirAttackComponent"));
		AirAttack->RegisterComponent();
	}
	return AirAttack->TryAttack();
}


bool UCombatFeelLibrary::IsAirAttackActive(const UObject* WorldContextObject)
{
	const ACharacter* Character = Cast<ACharacter>(CombatFeel::ResolveAttacker(WorldContextObject));
	const UAirAttackComponent* AirAttack = Character ? Character->FindComponentByClass<UAirAttackComponent>() : nullptr;
	return AirAttack && AirAttack->IsAirAttackActive();
}


void UCombatFeelLibrary::BeginUppercutHold(const UObject* WorldContextObject)
{
	ACharacter* Character = Cast<ACharacter>(CombatFeel::ResolveAttacker(WorldContextObject));
	if (!IsValid(Character))
	{
		return;
	}
	UUppercutComponent* Uppercut = Character->FindComponentByClass<UUppercutComponent>();
	if (!Uppercut)
	{
		Uppercut = NewObject<UUppercutComponent>(Character, TEXT("UppercutComponent"));
		Uppercut->RegisterComponent();
	}
	Uppercut->OnAttackPressed();
}


void UCombatFeelLibrary::EndUppercutHold(const UObject* WorldContextObject)
{
	ACharacter* Character = Cast<ACharacter>(CombatFeel::ResolveAttacker(WorldContextObject));
	if (UUppercutComponent* Uppercut = Character ? Character->FindComponentByClass<UUppercutComponent>() : nullptr)
	{
		Uppercut->OnAttackReleased();
	}
}


UAnimMontage* UCombatFeelLibrary::SelectAirDodgeMontage(
	const UObject* WorldContextObject,
	UAnimMontage* GroundMontage,
	const int32 DirectionIndex
)
{
	const ACharacter* Character = Cast<ACharacter>(CombatFeel::ResolveAttacker(WorldContextObject));
	const UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
	const bool bAirAttackActive = IsAirAttackActive(WorldContextObject);
	if (!Movement || (!Movement->IsFalling() && !bAirAttackActive))
	{
		return GroundMontage;
	}
	int32 AirDirectionIndex = DirectionIndex;
	// 空中连击期间屏蔽了移动输入，仍用当前按键选择相机朝向的八方向闪避。
	if (bAirAttackActive)
	{
		if (const APlayerController* PlayerController = Cast<APlayerController>(Character->GetController()))
		{
			const int32 ForwardInput = int32(PlayerController->IsInputKeyDown(EKeys::W))
				- int32(PlayerController->IsInputKeyDown(EKeys::S));
			const int32 RightInput = int32(PlayerController->IsInputKeyDown(EKeys::D))
				- int32(PlayerController->IsInputKeyDown(EKeys::A));
			if (ForwardInput != 0 || RightInput != 0)
			{
			const FRotationMatrix CameraYaw(FRotator(0.0f, PlayerController->GetControlRotation().Yaw, 0.0f));
			const FVector WorldDirection = CameraYaw.GetUnitAxis(EAxis::X) * ForwardInput
				+ CameraYaw.GetUnitAxis(EAxis::Y) * RightInput;
			const float Angle = FMath::Atan2(
				FVector::DotProduct(WorldDirection, Character->GetActorRightVector()),
				FVector::DotProduct(WorldDirection, Character->GetActorForwardVector()));
			AirDirectionIndex = (FMath::RoundToInt(FMath::RadiansToDegrees(Angle) / 45.0f) + 8) % 8;
		}
		}
	}
	const TArray<TObjectPtr<UAnimMontage>>& Montages = GetDefault<UCombatFeelLibrary>()->AirDodgeMontages;
	return Montages.IsValidIndex(AirDirectionIndex) && IsValid(Montages[AirDirectionIndex])
		? Montages[AirDirectionIndex].Get() : GroundMontage;
}


UAnimMontage* UCombatFeelLibrary::BeginAirDodgeHover(const UObject* WorldContextObject, UAnimMontage* DodgeMontage)
{
	ACharacter* Character = Cast<ACharacter>(CombatFeel::ResolveAttacker(WorldContextObject));
	if (!IsValid(Character))
	{
		return DodgeMontage;
	}
	UAirAttackComponent* AirCombat = Character->FindComponentByClass<UAirAttackComponent>();
	if (!AirCombat)
	{
		AirCombat = NewObject<UAirAttackComponent>(Character, TEXT("AirAttackComponent"));
		AirCombat->RegisterComponent();
	}
	AirCombat->BeginAirDodge(DodgeMontage);
	return DodgeMontage;
}


void UCombatFeelLibrary::EndAirDodgeHover(const UObject* WorldContextObject)
{
	ACharacter* Character = Cast<ACharacter>(CombatFeel::ResolveAttacker(WorldContextObject));
	if (UAirAttackComponent* AirCombat = Character ? Character->FindComponentByClass<UAirAttackComponent>() : nullptr)
	{
		AirCombat->EndAirDodge();
	}
}


FRotator UCombatFeelLibrary::FindStableLockOnRotation(
	const FVector Start,
	const FVector Target,
	const FRotator CurrentRotation,
	const float MinHorizontalDistance
)
{
	const FVector Delta = Target - Start;
	const float MinDistance = FMath::Max(0.0f, MinHorizontalDistance);
	if (Delta.SizeSquared2D() < FMath::Square(MinDistance))
	{
		return CurrentRotation;
	}
	FRotator Desired = Delta.Rotation();
	Desired.Roll = 0.0f;
	return Desired;
}


bool UCombatFeelLibrary::AssistedMeleeTrace(
	const UObject* WorldContextObject,
	const FVector Start,
	const FVector End,
	const float Radius,
	const TArray<TEnumAsByte<EObjectTypeQuery>>& ObjectTypes,
	const bool bTraceComplex,
	const TArray<AActor*>& ActorsToIgnore,
	const bool bIgnoreSelf,
	FHitResult& OutHit,
	const float AssistDistance,
	const float AssistHalfAngleDegrees
)
{
	OutHit = FHitResult();
	if (!WorldContextObject)
	{
		return false;
	}

	UWorld* World = WorldContextObject->GetWorld();
	if (!World)
	{
		return false;
	}

	const float EffectiveRadius = FMath::Max(Radius, 18.0f);
	const TWeakObjectPtr<UObject> HistoryKey(const_cast<UObject*>(WorldContextObject));
	const double Now = World->GetTimeSeconds();
	CombatFeel::FBladeTraceHistory* History = CombatFeel::BladeTraceHistories.Find(HistoryKey);

	bool bHit = CombatFeel::TraceSegment(
		WorldContextObject,
		Start,
		End,
		EffectiveRadius,
		ObjectTypes,
		bTraceComplex,
		ActorsToIgnore,
		bIgnoreSelf,
		OutHit
	);

	// Cover the volume crossed between timer samples, so fast attacks cannot pass through a target.
	if (!bHit && History && History->World == World && Now - History->TimeSeconds <= 0.18)
	{
		const FVector PreviousMidpoint = (History->Start + History->End) * 0.5;
		const FVector CurrentMidpoint = (Start + End) * 0.5;
		const TPair<FVector, FVector> SweepSegments[] = {
			{History->Start, Start},
			{History->End, End},
			{PreviousMidpoint, CurrentMidpoint},
			{History->Start, End},
		};
		for (const TPair<FVector, FVector>& Segment : SweepSegments)
		{
			if (CombatFeel::TraceSegment(
				WorldContextObject,
				Segment.Key,
				Segment.Value,
				EffectiveRadius,
				ObjectTypes,
				bTraceComplex,
				ActorsToIgnore,
				bIgnoreSelf,
				OutHit
			))
			{
				bHit = true;
				break;
			}
		}
	}

	CombatFeel::FBladeTraceHistory& NewHistory = CombatFeel::BladeTraceHistories.FindOrAdd(HistoryKey);
	NewHistory.Start = Start;
	NewHistory.End = End;
	NewHistory.TimeSeconds = Now;
	NewHistory.World = World;

	if (bHit || AssistDistance <= 0.0f)
	{
		return bHit;
	}

	AActor* Attacker = CombatFeel::ResolveAttacker(WorldContextObject);
	if (!Attacker)
	{
		return false;
	}

	TArray<AActor*> IgnoreActors = ActorsToIgnore;
	IgnoreActors.AddUnique(Attacker);
	TArray<AActor*> Overlaps;
	UKismetSystemLibrary::SphereOverlapActors(
		WorldContextObject,
		Attacker->GetActorLocation(),
		AssistDistance,
		ObjectTypes,
		nullptr,
		IgnoreActors,
		Overlaps
	);

	const float MinForwardDot = FMath::Cos(FMath::DegreesToRadians(FMath::Clamp(AssistHalfAngleDegrees, 5.0f, 89.0f)));
	AActor* BestActor = nullptr;
	double BestScore = TNumericLimits<double>::Max();
	for (AActor* Candidate : Overlaps)
	{
		if (!IsValid(Candidate) || Candidate == Attacker)
		{
			continue;
		}
		const FVector CandidatePoint = Candidate->GetComponentsBoundingBox(true).GetCenter();
		const FVector BladeMidpoint = (Start + End) * 0.5;
		const bool bCloseToBlade = FVector::Dist2D(CandidatePoint, BladeMidpoint) <= 110.0
			&& FMath::Abs(CandidatePoint.Z - BladeMidpoint.Z) <= 120.0;
		if (!bCloseToBlade && !CombatFeel::IsInsideAssistCone(
			Attacker->GetActorLocation(),
			Attacker->GetActorForwardVector(),
			CandidatePoint,
			AssistDistance,
			MinForwardDot
		))
		{
			continue;
		}
		const FVector FlatDelta = FVector(CandidatePoint.X, CandidatePoint.Y, 0.0)
			- FVector(Attacker->GetActorLocation().X, Attacker->GetActorLocation().Y, 0.0);
		const double ForwardDot = FVector::DotProduct(
			Attacker->GetActorForwardVector().GetSafeNormal2D(),
			FlatDelta.GetSafeNormal()
		);
		const double Score = FlatDelta.Length() + (1.0 - ForwardDot) * 70.0;
		if (Score < BestScore)
		{
			BestScore = Score;
			BestActor = Candidate;
		}
	}

	if (!BestActor)
	{
		return false;
	}

	const FVector ImpactPoint = BestActor->GetComponentsBoundingBox(true).GetCenter();
	const FVector ImpactNormal = (Attacker->GetActorLocation() - ImpactPoint).GetSafeNormal();
	OutHit = FHitResult(BestActor, Cast<UPrimitiveComponent>(BestActor->GetRootComponent()), ImpactPoint, ImpactNormal);
	OutHit.bBlockingHit = true;
	OutHit.Location = ImpactPoint;
	OutHit.ImpactPoint = ImpactPoint;
	OutHit.Distance = FVector::Distance(Attacker->GetActorLocation(), ImpactPoint);
	return true;
}


bool UCombatFeelLibrary::IsBestExecutionTarget(
	const UObject* WorldContextObject,
	const TArray<AActor*>& Candidates,
	AActor* Candidate,
	const float MaxDistance
)
{
	AActor* Executor = CombatFeel::ResolveAttacker(WorldContextObject);
	if (!IsValid(Executor) || !IsValid(Candidate) || Candidate == Executor || !CombatFeel::ImplementsExecutionInterface(Candidate))
	{
		return false;
	}
	const double CandidateDistance = FVector::Distance(Executor->GetActorLocation(), Candidate->GetActorLocation());
	if (CandidateDistance > MaxDistance || FMath::Abs(Executor->GetActorLocation().Z - Candidate->GetActorLocation().Z) > 130.0)
	{
		return false;
	}

	AActor* BestActor = nullptr;
	double BestScore = TNumericLimits<double>::Max();
	for (AActor* Item : Candidates)
	{
		if (!IsValid(Item) || Item == Executor || !CombatFeel::ImplementsExecutionInterface(Item))
		{
			continue;
		}
		if (FVector::Distance(Executor->GetActorLocation(), Item->GetActorLocation()) > MaxDistance
			|| FMath::Abs(Executor->GetActorLocation().Z - Item->GetActorLocation().Z) > 130.0)
		{
			continue;
		}
		const double Score = CombatFeel::ExecutionScore(Executor, Item);
		if (Score < BestScore)
		{
			BestScore = Score;
			BestActor = Item;
		}
	}
	return BestActor == Candidate;
}


bool UCombatFeelLibrary::PrepareExecutionPair(
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
	const float IgnoreCollisionDuration
)
{
	WarpLocation = FVector::ZeroVector;
	WarpRotation = FRotator::ZeroRotator;
	WarpTargetComponent = nullptr;
	PreparedTarget = nullptr;
	SelectedMontage = nullptr;
	AnimationIndex = INDEX_NONE;
	WarpTargetName = NAME_None;
	AActor* Executor = CombatFeel::ResolveAttacker(WorldContextObject);
	if (!IsValid(Executor) || !IsValid(Target) || Executor == Target)
	{
		return false;
	}

	static constexpr float ExecutionStartDistances[] = {95.0f, 105.0f, 90.0f};
	TArray<int32> ValidIndices;
	for (int32 Index = 0; Index < FMath::Min(ExecutionMontages.Num(), static_cast<int32>(UE_ARRAY_COUNT(ExecutionStartDistances))); ++Index)
	{
		if (IsValid(ExecutionMontages[Index]))
		{
			ValidIndices.Add(Index);
		}
	}
	WarpTargetComponent = Target->GetRootComponent();
	if (ValidIndices.IsEmpty() || !IsValid(WarpTargetComponent))
	{
		WarpTargetComponent = nullptr;
		return false;
	}
	AnimationIndex = ValidIndices[FMath::RandHelper(ValidIndices.Num())];
	SelectedMontage = ExecutionMontages[AnimationIndex];
	// 位置继续由 Motion Warping 追踪目标；朝向保留配对动画自己的根运动，避免重复转身。
	for (const FAnimNotifyEvent& Notify : SelectedMontage->Notifies)
	{
		if (const UAnimNotifyState_MotionWarping* State = Cast<UAnimNotifyState_MotionWarping>(Notify.NotifyStateClass))
		{
			if (URootMotionModifier_Warp* Modifier = Cast<URootMotionModifier_Warp>(State->RootMotionModifier))
			{
				Modifier->bWarpRotation = false;
			}
		}
	}
	WarpTargetName = SelectedMontage->GetFName();
	PreparedTarget = Target;
	const float StartDistance = ExecutionStartDistances[AnimationIndex];

	WarpLocation = Target->GetActorLocation();
	WarpRotation = Target->GetActorRotation();
	WarpRotation.Pitch = 0.0;
	WarpRotation.Roll = 0.0;

	// 成对处决动画的根骨骼沿角色前方移动；Mesh 自身的 -90 度偏移不能用于计算起点。
	const FVector ExecutionStart = Target->GetActorLocation()
		- WarpRotation.Vector().GetSafeNormal2D() * StartDistance;
	Executor->SetActorLocationAndRotation(
		ExecutionStart,
		WarpRotation,
		false,
		nullptr,
		ETeleportType::TeleportPhysics
	);

	if (ACharacter* ExecutorCharacter = Cast<ACharacter>(Executor))
	{
		ExecutorCharacter->GetCharacterMovement()->StopMovementImmediately();
	}
	if (ACharacter* MovingTargetCharacter = Cast<ACharacter>(Target))
	{
		MovingTargetCharacter->GetCharacterMovement()->StopMovementImmediately();
	}

	CombatFeel::SetPairMoveIgnore(Executor, Target, true);
	CombatFeel::SetPairMoveIgnore(Target, Executor, true);
	if (UWorld* World = WorldContextObject->GetWorld(); World && IgnoreCollisionDuration > 0.0f)
	{
		const TWeakObjectPtr<AActor> WeakExecutor = Executor;
		const TWeakObjectPtr<AActor> WeakTarget = Target;
		FTimerHandle RestoreHandle;
		World->GetTimerManager().SetTimer(
			RestoreHandle,
			[WeakExecutor, WeakTarget]()
			{
				if (AActor* LiveExecutor = WeakExecutor.Get())
				{
					CombatFeel::SetPairMoveIgnore(LiveExecutor, WeakTarget.Get(), false);
				}
				if (AActor* LiveTarget = WeakTarget.Get())
				{
					CombatFeel::SetPairMoveIgnore(LiveTarget, WeakExecutor.Get(), false);
				}
			},
			IgnoreCollisionDuration,
			false
		);
	}
	return true;
}


void UCombatFeelLibrary::ApplyTunedKnockback(
	const UObject* WorldContextObject,
	const FVector RequestedVelocity,
	const int32 AttackIndex,
	const float MaxAirborneYSpeed
)
{
	ACharacter* Victim = Cast<ACharacter>(CombatFeel::ResolveAttacker(WorldContextObject));
	if (!IsValid(Victim))
	{
		return;
	}

	const ACharacter* Player = UGameplayStatics::GetPlayerCharacter(WorldContextObject, 0);
	const float YSpeedLimit = FMath::Max(0.0f, MaxAirborneYSpeed);
	const UUppercutComponent* Uppercut = Player ? Player->FindComponentByClass<UUppercutComponent>() : nullptr;
	if (Victim != Player && Uppercut && Uppercut->IsUppercutActive())
	{
		// 挑飞以竖直速度为主，世界 Y 轴只保留少量侧移以方便继续追击。
		FVector Outward = (Victim->GetActorLocation() - Player->GetActorLocation()).GetSafeNormal2D();
		if (Outward.IsNearlyZero())
		{
			Outward = Player->GetActorForwardVector().GetSafeNormal2D();
		}
		FVector LaunchVelocity = Outward * 115.0f + FVector::UpVector * 650.0f;
		LaunchVelocity.Y = FMath::Clamp(LaunchVelocity.Y, -YSpeedLimit, YSpeedLimit);
		Victim->GetCharacterMovement()->StopMovementImmediately();
		Victim->LaunchCharacter(LaunchVelocity, true, true);
		return;
	}
	const UAirAttackComponent* AirAttack = Player ? Player->FindComponentByClass<UAirAttackComponent>() : nullptr;
	if (Victim != Player && AirAttack && AirAttack->IsAirAttackActive())
	{
		// 前三段轻推以保留后续命中距离，最后一段才明显击退。
		static constexpr float HorizontalSpeeds[] = {140.0f, 170.0f, 200.0f, 360.0f};
		static constexpr float UpwardSpeeds[] = {45.0f, 55.0f, 70.0f, 150.0f};
		const int32 Step = FMath::Clamp(AirAttack->GetCurrentStep(), 0, 3);
		FVector Outward = (Victim->GetActorLocation() - Player->GetActorLocation()).GetSafeNormal2D();
		if (Outward.IsNearlyZero())
		{
			Outward = Player->GetActorForwardVector().GetSafeNormal2D();
		}
		FVector AirLaunch = Outward * HorizontalSpeeds[Step] + FVector::UpVector * UpwardSpeeds[Step];
		AirLaunch.Y = FMath::Clamp(AirLaunch.Y, -YSpeedLimit, YSpeedLimit);
		Victim->GetCharacterMovement()->StopMovementImmediately();
		Victim->LaunchCharacter(AirLaunch, true, true);
		return;
	}
	// 第三段攻击有两个命中窗口。首段保留受击与抽帧反馈，但不能提前把目标打出末段范围。
	if (AttackIndex == 3)
	{
		const UAnimInstance* PlayerAnim = Player && Player->GetMesh() ? Player->GetMesh()->GetAnimInstance() : nullptr;
		const UAnimMontage* ActiveMontage = PlayerAnim ? PlayerAnim->GetCurrentActiveMontage() : nullptr;
		if (ActiveMontage
			&& ActiveMontage->GetName().Contains(TEXT("Combo_Attack_03_03_Seq_Montage"))
			&& PlayerAnim->Montage_GetPosition(ActiveMontage) < 0.60f)
		{
			Victim->GetCharacterMovement()->StopMovementImmediately();
			return;
		}
	}

	const bool bThirdFinisher = AttackIndex == 3;
	const bool bFourthFinisher = AttackIndex == 4;
	const bool bFinisher = AttackIndex >= 3;
	const float MaxHorizontalSpeed = bThirdFinisher ? 520.0f : (bFourthFinisher ? 370.0f : (bFinisher ? 320.0f : 180.0f));
	const float MaxUpwardSpeed = bThirdFinisher ? 180.0f : (bFourthFinisher ? 160.0f : (bFinisher ? 150.0f : 75.0f));
	FVector HorizontalVelocity(RequestedVelocity.X, RequestedVelocity.Y, 0.0);
	if (bThirdFinisher || bFourthFinisher)
	{
		FVector Outward = HorizontalVelocity.GetSafeNormal2D();
		if (Outward.IsNearlyZero() && Player)
		{
			Outward = (Victim->GetActorLocation() - Player->GetActorLocation()).GetSafeNormal2D();
		}
		if (Outward.IsNearlyZero() && Player)
		{
			Outward = Player->GetActorForwardVector().GetSafeNormal2D();
		}
		const double MinHorizontalSpeed = bThirdFinisher ? 420.0 : 300.0;
		HorizontalVelocity = Outward * FMath::Clamp(HorizontalVelocity.Size2D(), MinHorizontalSpeed, static_cast<double>(MaxHorizontalSpeed));
	}
	else
	{
		HorizontalVelocity = HorizontalVelocity.GetClampedToMaxSize2D(MaxHorizontalSpeed);
	}
	FVector LaunchVelocity(
		HorizontalVelocity.X,
		HorizontalVelocity.Y,
		bThirdFinisher || bFourthFinisher
			? FMath::Clamp(RequestedVelocity.Z, bThirdFinisher ? 150.0 : 120.0, static_cast<double>(MaxUpwardSpeed))
			: FMath::Clamp(RequestedVelocity.Z, -75.0, static_cast<double>(MaxUpwardSpeed))
	);
	if (Victim->GetCharacterMovement()->IsFalling())
	{
		LaunchVelocity.Y = FMath::Clamp(LaunchVelocity.Y, -YSpeedLimit, YSpeedLimit);
	}
	Victim->GetCharacterMovement()->StopMovementImmediately();
	Victim->LaunchCharacter(LaunchVelocity, true, true);
}


void UCombatFeelLibrary::BeginAttackRootMotion(const UObject* WorldContextObject)
{
	if (ACharacter* Attacker = Cast<ACharacter>(CombatFeel::ResolveAttacker(WorldContextObject)))
	{
		Attacker->SetAnimRootMotionTranslationScale(0.55f);
	}
}


void UCombatFeelLibrary::EndAttackRootMotion(const UObject* WorldContextObject)
{
	ACharacter* Attacker = Cast<ACharacter>(CombatFeel::ResolveAttacker(WorldContextObject));
	if (!Attacker || !Attacker->GetWorld())
	{
		return;
	}

	const TWeakObjectPtr<ACharacter> WeakAttacker = Attacker;
	FTimerHandle RestoreHandle;
	Attacker->GetWorld()->GetTimerManager().SetTimer(
		RestoreHandle,
		[WeakAttacker]()
		{
			ACharacter* LiveAttacker = WeakAttacker.Get();
			if (!LiveAttacker)
			{
				return;
			}
			UAnimInstance* AnimInstance = LiveAttacker->GetMesh() ? LiveAttacker->GetMesh()->GetAnimInstance() : nullptr;
			UAnimMontage* ActiveMontage = AnimInstance ? AnimInstance->GetCurrentActiveMontage() : nullptr;
			const bool bComboStillPlaying = ActiveMontage
				&& ActiveMontage->GetPathName().Contains(TEXT("Combo_Attack_03"))
				&& AnimInstance->Montage_IsPlaying(ActiveMontage);
			LiveAttacker->SetAnimRootMotionTranslationScale(bComboStillPlaying ? 0.55f : 1.0f);
		},
		0.05f,
		false
	);
}


#if WITH_DEV_AUTOMATION_TESTS

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FCombatFeelGeometryTest,
	"RuneofSuccor.CombatFeel.Geometry",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter
)

bool FCombatFeelGeometryTest::RunTest(const FString& Parameters)
{
	(void)Parameters;
	const FVector Origin = FVector::ZeroVector;
	const FVector Forward = FVector::ForwardVector;
	const float MinDot = FMath::Cos(FMath::DegreesToRadians(65.0f));

	TestTrue("A close target in front is assisted", CombatFeel::IsInsideAssistCone(Origin, Forward, FVector(150.0, 30.0, 20.0), 210.0f, MinDot));
	TestFalse("A target behind is rejected", CombatFeel::IsInsideAssistCone(Origin, Forward, FVector(-80.0, 0.0, 0.0), 210.0f, MinDot));
	TestFalse("A distant target is rejected", CombatFeel::IsInsideAssistCone(Origin, Forward, FVector(260.0, 0.0, 0.0), 210.0f, MinDot));
	TestFalse("A target on another floor is rejected", CombatFeel::IsInsideAssistCone(Origin, Forward, FVector(80.0, 0.0, 150.0), 210.0f, MinDot));
	return true;
}

#endif
