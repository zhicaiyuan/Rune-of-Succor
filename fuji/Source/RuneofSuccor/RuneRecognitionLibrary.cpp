#include "RuneRecognitionLibrary.h"

#include "UObject/Script.h"
#include "UObject/UnrealType.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Engine/Blueprint.h"
#include "Misc/AutomationTest.h"
#endif


namespace RuneRecognition
{
	constexpr int32 MinGridSize = 3;
	constexpr int32 MaxGridSize = 16;
	constexpr double MinBoundsSize = 1.0;
	constexpr double SamplesPerCell = 6.0;
	constexpr int32 StructuralSampleCount = 32;
	constexpr double DirectnessWeight = 0.35;
	constexpr double NetTurningWeight = 0.35;
	constexpr double TurnConsistencyWeight = 0.25;
	constexpr double PathLengthWeight = 0.15;

	void AddSegmentSamples(
		const FVector2D& Start,
		const FVector2D& End,
		const int32 GridSize,
		TArray<float>& Counts,
		int32& TotalSamples
	)
	{
		const double Length = FVector2D::Distance(Start, End);
		const int32 StepCount = FMath::Max(1, FMath::CeilToInt(Length * GridSize * SamplesPerCell));

		// 每段不重复加入末端点；下一段会包含它，避免拐点因鼠标采样密度被过度加权。
		for (int32 Step = 0; Step < StepCount; ++Step)
		{
			const double Alpha = static_cast<double>(Step) / static_cast<double>(StepCount);
			const FVector2D Point = FMath::Lerp(Start, End, Alpha);
			const int32 X = FMath::Clamp(FMath::FloorToInt(Point.X * GridSize), 0, GridSize - 1);
			const int32 Y = FMath::Clamp(FMath::FloorToInt(Point.Y * GridSize), 0, GridSize - 1);
			Counts[Y * GridSize + X] += 1.0f;
			++TotalSamples;
		}
	}

	TArray<FVector2D> ResampleStroke(const TArray<FVector2D>& Stroke, const FBox2D& Bounds, const double LongEdge)
	{
		TArray<FVector2D> Points;
		Points.Reserve(Stroke.Num());
		for (const FVector2D& RawPoint : Stroke)
		{
			const FVector2D Point = (RawPoint - Bounds.Min) / LongEdge;
			if (Points.IsEmpty() || FVector2D::DistSquared(Points.Last(), Point) > UE_DOUBLE_SMALL_NUMBER)
			{
				Points.Add(Point);
			}
		}

		if (Points.Num() < 2)
		{
			return {};
		}

		TArray<double> Distances;
		Distances.SetNumZeroed(Points.Num());
		for (int32 Index = 1; Index < Points.Num(); ++Index)
		{
			Distances[Index] = Distances[Index - 1] + FVector2D::Distance(Points[Index - 1], Points[Index]);
		}

		const double TotalLength = Distances.Last();
		if (TotalLength <= UE_DOUBLE_SMALL_NUMBER)
		{
			return {};
		}

		TArray<FVector2D> Result;
		Result.Reserve(StructuralSampleCount);
		int32 SegmentIndex = 1;
		for (int32 SampleIndex = 0; SampleIndex < StructuralSampleCount; ++SampleIndex)
		{
			const double TargetDistance = TotalLength * SampleIndex / (StructuralSampleCount - 1);
			while (SegmentIndex < Distances.Num() - 1 && Distances[SegmentIndex] < TargetDistance)
			{
				++SegmentIndex;
			}
			const double SegmentStart = Distances[SegmentIndex - 1];
			const double SegmentLength = Distances[SegmentIndex] - SegmentStart;
			const double Alpha = SegmentLength > UE_DOUBLE_SMALL_NUMBER
				? (TargetDistance - SegmentStart) / SegmentLength
				: 0.0;
			Result.Add(FMath::Lerp(Points[SegmentIndex - 1], Points[SegmentIndex], Alpha));
		}

		// 轻度平滑鼠标抖动，同时保留闪电折线的主要拐点。
		TArray<FVector2D> Smoothed = Result;
		for (int32 Index = 1; Index < Result.Num() - 1; ++Index)
		{
			Smoothed[Index] = (Result[Index - 1] + Result[Index] * 2.0 + Result[Index + 1]) * 0.25;
		}
		return Smoothed;
	}

	void AppendStructuralFeatures(
		const TArray<TArray<FVector2D>>& Strokes,
		const FBox2D& Bounds,
		const double LongEdge,
		TArray<float>& Features
	)
	{
		double TotalLength = 0.0;
		double EndpointDistance = 0.0;
		double TotalSignedTurning = 0.0;
		double TotalAbsoluteTurning = 0.0;

		for (const TArray<FVector2D>& Stroke : Strokes)
		{
			const TArray<FVector2D> Points = ResampleStroke(Stroke, Bounds, LongEdge);
			if (Points.Num() < 2)
			{
				continue;
			}

			EndpointDistance += FVector2D::Distance(Points[0], Points.Last());
			FVector2D PreviousDirection = FVector2D::ZeroVector;
			bool bHasPreviousDirection = false;
			for (int32 Index = 1; Index < Points.Num(); ++Index)
			{
				const FVector2D Segment = Points[Index] - Points[Index - 1];
				const double SegmentLength = Segment.Length();
				if (SegmentLength <= UE_DOUBLE_SMALL_NUMBER)
				{
					continue;
				}

				TotalLength += SegmentLength;
				const FVector2D Direction = Segment / SegmentLength;
				if (bHasPreviousDirection)
				{
					const double Cross = PreviousDirection.X * Direction.Y - PreviousDirection.Y * Direction.X;
					const double Dot = FVector2D::DotProduct(PreviousDirection, Direction);
					const double Angle = FMath::Atan2(Cross, Dot);
					TotalSignedTurning += Angle;
					TotalAbsoluteTurning += FMath::Abs(Angle);
				}
				PreviousDirection = Direction;
				bHasPreviousDirection = true;
			}
		}

		const double Directness = TotalLength > UE_DOUBLE_SMALL_NUMBER ? EndpointDistance / TotalLength : 0.0;
		const double NetTurning = FMath::Clamp(FMath::Abs(TotalSignedTurning) / (4.0 * UE_DOUBLE_PI), 0.0, 1.0);
		const double TurnConsistency = TotalAbsoluteTurning > UE_DOUBLE_SMALL_NUMBER
			? FMath::Clamp(FMath::Abs(TotalSignedTurning) / TotalAbsoluteTurning, 0.0, 1.0)
			: 0.0;
		const double NormalizedPathLength = FMath::Clamp(TotalLength / 4.0, 0.0, 1.0);

		Features.Add(static_cast<float>(Directness * DirectnessWeight));
		Features.Add(static_cast<float>(NetTurning * NetTurningWeight));
		Features.Add(static_cast<float>(TurnConsistency * TurnConsistencyWeight));
		Features.Add(static_cast<float>(NormalizedPathLength * PathLengthWeight));
	}
}


void URuneRecognitionLibrary::ExtractRuneFeatures(
	const TArray<int32>& Strokes,
	TArray<float>& Features,
	float& AspectRatio,
	int32 GridSize
)
{
	// CustomThunk 会直接调用 GenericExtractRuneFeatures，此函数不会实际执行。
	checkNoEntry();
}


DEFINE_FUNCTION(URuneRecognitionLibrary::execExtractRuneFeatures)
{
	Stack.MostRecentProperty = nullptr;
	Stack.StepCompiledIn<FArrayProperty>(nullptr);
	void* ArrayAddress = Stack.MostRecentPropertyAddress;
	const FArrayProperty* ArrayProperty = CastField<FArrayProperty>(Stack.MostRecentProperty);
	if (!ArrayProperty)
	{
		Stack.bArrayContextFailed = true;
		return;
	}

	P_GET_TARRAY_REF(float, Z_Param_Out_Features);
	P_GET_PROPERTY_REF(FFloatProperty, Z_Param_Out_AspectRatio);
	P_GET_PROPERTY(FIntProperty, Z_Param_GridSize);
	P_FINISH;

	P_NATIVE_BEGIN;
	GenericExtractRuneFeatures(
		ArrayAddress,
		ArrayProperty,
		Z_Param_Out_Features,
		Z_Param_Out_AspectRatio,
		Z_Param_GridSize
	);
	P_NATIVE_END;
}


void URuneRecognitionLibrary::GenericExtractRuneFeatures(
	const void* ArrayAddress,
	const FArrayProperty* ArrayProperty,
	TArray<float>& OutFeatures,
	float& OutAspectRatio,
	const int32 GridSize
)
{
	OutFeatures.Reset();
	OutAspectRatio = 0.0f;

	if (!ArrayAddress || !ArrayProperty)
	{
		return;
	}

	const FStructProperty* StrokeStructProperty = CastField<FStructProperty>(ArrayProperty->Inner);
	if (!StrokeStructProperty || !StrokeStructProperty->Struct)
	{
		return;
	}

	const FArrayProperty* PointsArrayProperty = nullptr;
	const FStructProperty* PointStructProperty = nullptr;
	for (TFieldIterator<FProperty> It(StrokeStructProperty->Struct); It; ++It)
	{
		const FArrayProperty* CandidateArray = CastField<FArrayProperty>(*It);
		const FStructProperty* CandidateInner =
			CandidateArray ? CastField<FStructProperty>(CandidateArray->Inner) : nullptr;
		if (CandidateInner && CandidateInner->Struct == TBaseStructure<FVector2D>::Get())
		{
			PointsArrayProperty = CandidateArray;
			PointStructProperty = CandidateInner;
			break;
		}
	}

	if (!PointsArrayProperty || !PointStructProperty)
	{
		return;
	}

	TArray<TArray<FVector2D>> TypedStrokes;
	FScriptArrayHelper StrokeHelper(ArrayProperty, ArrayAddress);
	TypedStrokes.Reserve(StrokeHelper.Num());

	for (int32 StrokeIndex = 0; StrokeIndex < StrokeHelper.Num(); ++StrokeIndex)
	{
		const void* StrokeData = StrokeHelper.GetRawPtr(StrokeIndex);
		const void* PointsAddress = PointsArrayProperty->ContainerPtrToValuePtr<void>(StrokeData);
		FScriptArrayHelper PointHelper(PointsArrayProperty, PointsAddress);

		TArray<FVector2D>& TypedStroke = TypedStrokes.AddDefaulted_GetRef();
		TypedStroke.Reserve(PointHelper.Num());
		for (int32 PointIndex = 0; PointIndex < PointHelper.Num(); ++PointIndex)
		{
			FVector2D Point = FVector2D::ZeroVector;
			PointStructProperty->Struct->CopyScriptStruct(&Point, PointHelper.GetRawPtr(PointIndex));
			if (FMath::IsFinite(Point.X) && FMath::IsFinite(Point.Y))
			{
				TypedStroke.Add(Point);
			}
		}
	}

	BuildStableFeatures(TypedStrokes, GridSize, OutFeatures, OutAspectRatio);
}


float URuneRecognitionLibrary::ScoreRuneFeatures(
	const TArray<float>& A,
	const TArray<float>& B
)
{
	if (A.IsEmpty() || A.Num() != B.Num())
	{
		return TNumericLimits<float>::Max();
	}

	double SquaredDistance = 0.0;
	for (int32 Index = 0; Index < A.Num(); ++Index)
	{
		if (!FMath::IsFinite(A[Index]) || !FMath::IsFinite(B[Index]))
		{
			return TNumericLimits<float>::Max();
		}

		const double Difference = static_cast<double>(A[Index]) - static_cast<double>(B[Index]);
		SquaredDistance += Difference * Difference;
	}

	return static_cast<float>(FMath::Sqrt(SquaredDistance));
}


bool URuneRecognitionLibrary::BuildStableFeatures(
	const TArray<TArray<FVector2D>>& Strokes,
	const int32 GridSize,
	TArray<float>& OutFeatures,
	float& OutAspectRatio
)
{
	OutFeatures.Reset();
	OutAspectRatio = 0.0f;

	if (GridSize < RuneRecognition::MinGridSize || GridSize > RuneRecognition::MaxGridSize)
	{
		return false;
	}

	FBox2D Bounds(ForceInit);
	int32 UsableStrokeCount = 0;
	for (const TArray<FVector2D>& Stroke : Strokes)
	{
		if (Stroke.Num() < 2)
		{
			continue;
		}

		++UsableStrokeCount;
		for (const FVector2D& Point : Stroke)
		{
			if (FMath::IsFinite(Point.X) && FMath::IsFinite(Point.Y))
			{
				Bounds += Point;
			}
		}
	}

	if (UsableStrokeCount == 0 || !Bounds.bIsValid)
	{
		return false;
	}

	const FVector2D BoundsSize = Bounds.GetSize();
	const double LongEdge = FMath::Max(BoundsSize.X, BoundsSize.Y);
	if (LongEdge < RuneRecognition::MinBoundsSize)
	{
		return false;
	}

	// 与原蓝图保持同一量级。完全水平的线高度为 0，如果除以极小数，
	// 宽高比会膨胀到几十万并被横线模板错误过滤掉。
	OutAspectRatio = static_cast<float>(BoundsSize.X / FMath::Max(BoundsSize.Y, 1.0));
	OutFeatures.Init(0.0f, GridSize * GridSize);

	int32 TotalSamples = 0;
	for (const TArray<FVector2D>& Stroke : Strokes)
	{
		if (Stroke.Num() < 2)
		{
			continue;
		}

		for (int32 PointIndex = 1; PointIndex < Stroke.Num(); ++PointIndex)
		{
			const FVector2D Start = (Stroke[PointIndex - 1] - Bounds.Min) / LongEdge;
			const FVector2D End = (Stroke[PointIndex] - Bounds.Min) / LongEdge;
			if (FVector2D::DistSquared(Start, End) <= UE_DOUBLE_SMALL_NUMBER)
			{
				continue;
			}

			RuneRecognition::AddSegmentSamples(Start, End, GridSize, OutFeatures, TotalSamples);
		}

		const FVector2D LastPoint = (Stroke.Last() - Bounds.Min) / LongEdge;
		const int32 LastX = FMath::Clamp(FMath::FloorToInt(LastPoint.X * GridSize), 0, GridSize - 1);
		const int32 LastY = FMath::Clamp(FMath::FloorToInt(LastPoint.Y * GridSize), 0, GridSize - 1);
		OutFeatures[LastY * GridSize + LastX] += 1.0f;
		++TotalSamples;
	}

	if (TotalSamples <= 0)
	{
		OutFeatures.Reset();
		return false;
	}

	const float InverseSampleCount = 1.0f / static_cast<float>(TotalSamples);
	for (float& Value : OutFeatures)
	{
		Value *= InverseSampleCount;
	}
	RuneRecognition::AppendStructuralFeatures(Strokes, Bounds, LongEdge, OutFeatures);

	return true;
}


#if WITH_DEV_AUTOMATION_TESTS
namespace RuneRecognitionTests
{
	TArray<FVector2D> MakeCircle(const int32 PointCount, const double RadiusX, const double RadiusY)
	{
		TArray<FVector2D> Points;
		Points.Reserve(PointCount + 1);
		for (int32 Index = 0; Index <= PointCount; ++Index)
		{
			const double Angle = -UE_DOUBLE_PI * 0.5 + 2.0 * UE_DOUBLE_PI * Index / PointCount;
			Points.Emplace(RadiusX * FMath::Cos(Angle), RadiusY * FMath::Sin(Angle));
		}
		return Points;
	}

	TArray<FVector2D> MakeSpiral(
		const int32 PointCount,
		const double InnerRadius,
		const double OuterRadius,
		const double ScaleX = 1.0,
		const double ScaleY = 1.0
	)
	{
		TArray<FVector2D> Points;
		Points.Reserve(PointCount + 1);
		for (int32 Index = 0; Index <= PointCount; ++Index)
		{
			const double Alpha = static_cast<double>(Index) / PointCount;
			const double Angle = -UE_DOUBLE_PI * 0.5 + 4.0 * UE_DOUBLE_PI * Alpha;
			const double Radius = FMath::Lerp(InnerRadius, OuterRadius, Alpha);
			Points.Emplace(
				ScaleX * Radius * FMath::Cos(Angle),
				ScaleY * Radius * FMath::Sin(Angle)
			);
		}
		return Points;
	}

	double FeatureDistance(const TArray<float>& A, const TArray<float>& B)
	{
		if (A.Num() != B.Num())
		{
			return TNumericLimits<double>::Max();
		}
		double Sum = 0.0;
		for (int32 Index = 0; Index < A.Num(); ++Index)
		{
			Sum += FMath::Square(static_cast<double>(A[Index] - B[Index]));
		}
		return FMath::Sqrt(Sum);
	}

	bool RunBlueprintFeatureFunction(
		const TArray<TArray<FVector2D>>& InputStrokes,
		TArray<float>& OutFeatures,
		float& OutAspectRatio
	)
	{
		UBlueprint* Blueprint = LoadObject<UBlueprint>(nullptr, TEXT("/Game/蓝图/玩家/BPC_画符系统.BPC_画符系统"));
		if (!Blueprint || !Blueprint->GeneratedClass)
		{
			UE_LOG(LogTemp, Error, TEXT("Rune bridge: blueprint or generated class missing"));
			return false;
		}

		UObject* Target = Blueprint->GeneratedClass->GetDefaultObject();
		UFunction* Function = Blueprint->GeneratedClass->FindFunctionByName(TEXT("算特征"));
		if (!Target || !Function)
		{
			UE_LOG(
				LogTemp,
				Error,
				TEXT("Rune bridge: target=%s function=%s"),
				Target ? TEXT("valid") : TEXT("missing"),
				Function ? TEXT("valid") : TEXT("missing")
			);
			for (TFieldIterator<UFunction> FunctionIt(Blueprint->GeneratedClass, EFieldIterationFlags::IncludeSuper); FunctionIt; ++FunctionIt)
			{
				UE_LOG(LogTemp, Error, TEXT("Rune bridge function candidate: %s"), *FunctionIt->GetName());
			}
			return false;
		}

		FArrayProperty* StrokeArrayProperty = nullptr;
		FArrayProperty* FeatureArrayProperty = nullptr;
		FNumericProperty* FeatureValueProperty = nullptr;
		FNumericProperty* AspectProperty = nullptr;
		FArrayProperty* PointsArrayProperty = nullptr;
		FStructProperty* PointStructProperty = nullptr;

		for (TFieldIterator<FProperty> It(Function); It; ++It)
		{
			FProperty* Property = *It;
			if (!Property->HasAnyPropertyFlags(CPF_Parm))
			{
				continue;
			}

			if (FArrayProperty* ArrayProperty = CastField<FArrayProperty>(Property))
			{
				if (FNumericProperty* NumericInner = CastField<FNumericProperty>(ArrayProperty->Inner);
					NumericInner && Property->HasAnyPropertyFlags(CPF_OutParm))
				{
					FeatureArrayProperty = ArrayProperty;
					FeatureValueProperty = NumericInner;
					continue;
				}

				const FStructProperty* StrokeStructProperty = CastField<FStructProperty>(ArrayProperty->Inner);
				if (!StrokeStructProperty || !StrokeStructProperty->Struct)
				{
					continue;
				}

				for (TFieldIterator<FProperty> StrokeIt(StrokeStructProperty->Struct); StrokeIt; ++StrokeIt)
				{
					FArrayProperty* Candidate = CastField<FArrayProperty>(*StrokeIt);
					FStructProperty* CandidateInner = Candidate ? CastField<FStructProperty>(Candidate->Inner) : nullptr;
					if (CandidateInner && CandidateInner->Struct == TBaseStructure<FVector2D>::Get())
					{
						StrokeArrayProperty = ArrayProperty;
						PointsArrayProperty = Candidate;
						PointStructProperty = CandidateInner;
						break;
					}
				}
			}
			else if (FNumericProperty* NumericProperty = CastField<FNumericProperty>(Property))
			{
				if (NumericProperty->IsFloatingPoint() && Property->HasAnyPropertyFlags(CPF_OutParm))
				{
					AspectProperty = NumericProperty;
				}
			}
		}

		if (!StrokeArrayProperty || !PointsArrayProperty || !PointStructProperty ||
			!FeatureArrayProperty || !FeatureValueProperty || !AspectProperty)
		{
			UE_LOG(
				LogTemp,
				Error,
				TEXT("Rune bridge properties: strokes=%s points=%s pointStruct=%s features=%s aspect=%s"),
				StrokeArrayProperty ? *StrokeArrayProperty->GetName() : TEXT("missing"),
				PointsArrayProperty ? *PointsArrayProperty->GetName() : TEXT("missing"),
				PointStructProperty ? *PointStructProperty->GetName() : TEXT("missing"),
				FeatureArrayProperty ? *FeatureArrayProperty->GetName() : TEXT("missing"),
				AspectProperty ? *AspectProperty->GetName() : TEXT("missing")
			);
			for (TFieldIterator<FProperty> PropertyIt(Function); PropertyIt; ++PropertyIt)
			{
				UE_LOG(
					LogTemp,
					Error,
					TEXT("Rune bridge parameter: %s class=%s flags=%llu"),
					*PropertyIt->GetName(),
					*PropertyIt->GetClass()->GetName(),
					static_cast<uint64>(PropertyIt->GetPropertyFlags())
				);
			}
			return false;
		}

		TArray<uint8> Parameters;
		Parameters.SetNumZeroed(Function->ParmsSize);
		Function->InitializeStruct(Parameters.GetData());

		void* StrokeArrayAddress = StrokeArrayProperty->ContainerPtrToValuePtr<void>(Parameters.GetData());
		FScriptArrayHelper StrokeHelper(StrokeArrayProperty, StrokeArrayAddress);
		for (const TArray<FVector2D>& Stroke : InputStrokes)
		{
			const int32 StrokeIndex = StrokeHelper.AddValue();
			void* StrokeAddress = StrokeHelper.GetRawPtr(StrokeIndex);
			void* PointsAddress = PointsArrayProperty->ContainerPtrToValuePtr<void>(StrokeAddress);
			FScriptArrayHelper PointHelper(PointsArrayProperty, PointsAddress);
			for (const FVector2D& Point : Stroke)
			{
				const int32 PointIndex = PointHelper.AddValue();
				PointStructProperty->Struct->CopyScriptStruct(PointHelper.GetRawPtr(PointIndex), &Point);
			}
		}

		Target->ProcessEvent(Function, Parameters.GetData());

		void* FeatureArrayAddress = FeatureArrayProperty->ContainerPtrToValuePtr<void>(Parameters.GetData());
		FScriptArrayHelper FeatureHelper(FeatureArrayProperty, FeatureArrayAddress);
		OutFeatures.SetNum(FeatureHelper.Num());
		for (int32 Index = 0; Index < FeatureHelper.Num(); ++Index)
		{
			OutFeatures[Index] = static_cast<float>(
				FeatureValueProperty->GetFloatingPointPropertyValue(FeatureHelper.GetRawPtr(Index))
			);
		}
		OutAspectRatio = static_cast<float>(AspectProperty->GetFloatingPointPropertyValue(
			AspectProperty->ContainerPtrToValuePtr<void>(Parameters.GetData())
		));

		Function->DestroyStruct(Parameters.GetData());
		return true;
	}
}


IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FRuneRecognitionStableSamplingTest,
	"RuneofSuccor.RuneRecognition.StableSampling",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter
)


bool FRuneRecognitionStableSamplingTest::RunTest(const FString& Parameters)
{
	constexpr int32 GridSize = 6;
	constexpr int32 StructuralFeatureCount = 4;
	constexpr double AcceptanceTolerance = 0.22;
	constexpr double TemplateTolerance = 0.35;

	TArray<float> CircleTemplate;
	TArray<float> CircleCandidate;
	float CircleRatio = 0.0f;
	float CandidateRatio = 0.0f;
	TestTrue(
		TEXT("圆模板特征生成成功"),
		URuneRecognitionLibrary::BuildStableFeatures(
			{RuneRecognitionTests::MakeCircle(96, 100.0, 100.0)},
			GridSize,
			CircleTemplate,
			CircleRatio
		)
	);
	TestTrue(
		TEXT("稀疏椭圆手绘特征生成成功"),
		URuneRecognitionLibrary::BuildStableFeatures(
			{RuneRecognitionTests::MakeCircle(18, 95.0, 105.0)},
			GridSize,
			CircleCandidate,
			CandidateRatio
		)
	);
	TestEqual(TEXT("特征数量"), CircleTemplate.Num(), GridSize * GridSize + StructuralFeatureCount);
	TestTrue(
		TEXT("圆对不同采样密度保持稳定"),
		RuneRecognitionTests::FeatureDistance(CircleTemplate, CircleCandidate) < AcceptanceTolerance
	);
	TestTrue(TEXT("圆的宽高比在模板范围内"), CandidateRatio >= 0.6f && CandidateRatio <= 1.67f);

	TArray<float> VerticalTemplate;
	TArray<float> VerticalCandidate;
	float VerticalRatio = 0.0f;
	URuneRecognitionLibrary::BuildStableFeatures(
		{{FVector2D(0.0, 0.0), FVector2D(0.0, 100.0)}},
		GridSize,
		VerticalTemplate,
		VerticalRatio
	);
	URuneRecognitionLibrary::BuildStableFeatures(
		{{FVector2D(3.0, 100.0), FVector2D(-2.0, 70.0), FVector2D(2.0, 35.0), FVector2D(0.0, 0.0)}},
		GridSize,
		VerticalCandidate,
		VerticalRatio
	);
	TestTrue(
		TEXT("轻微弯曲且反向绘制的竖线可识别"),
		RuneRecognitionTests::FeatureDistance(VerticalTemplate, VerticalCandidate) < AcceptanceTolerance
	);
	TestTrue(TEXT("竖线宽高比在模板范围内"), VerticalRatio <= 0.4f);

	TArray<float> CrossTemplate;
	TArray<float> CrossCandidate;
	float CrossRatio = 0.0f;
	URuneRecognitionLibrary::BuildStableFeatures(
		{
			{FVector2D(0.0, 0.0), FVector2D(100.0, 100.0)},
			{FVector2D(100.0, 0.0), FVector2D(0.0, 100.0)},
		},
		GridSize,
		CrossTemplate,
		CrossRatio
	);
	URuneRecognitionLibrary::BuildStableFeatures(
		{
			{FVector2D(98.0, 102.0), FVector2D(51.0, 49.0), FVector2D(1.0, -2.0)},
			{FVector2D(2.0, 99.0), FVector2D(48.0, 52.0), FVector2D(101.0, 1.0)},
		},
		GridSize,
		CrossCandidate,
		CrossRatio
	);
	TestTrue(
		TEXT("叉号允许反向、稀疏和少量抖动"),
		RuneRecognitionTests::FeatureDistance(CrossTemplate, CrossCandidate) < AcceptanceTolerance
	);
	TestTrue(TEXT("叉号宽高比在模板范围内"), CrossRatio >= 0.6f && CrossRatio <= 1.67f);

	TArray<float> LightningTemplate;
	TArray<float> LightningCandidate;
	float LightningRatio = 0.0f;
	URuneRecognitionLibrary::BuildStableFeatures(
		{{FVector2D(68.0, 0.0), FVector2D(24.0, 44.0), FVector2D(60.0, 44.0), FVector2D(18.0, 100.0)}},
		GridSize,
		LightningTemplate,
		LightningRatio
	);
	URuneRecognitionLibrary::BuildStableFeatures(
		{{FVector2D(70.0, 2.0), FVector2D(28.0, 43.0), FVector2D(62.0, 46.0), FVector2D(17.0, 102.0)}},
		GridSize,
		LightningCandidate,
		LightningRatio
	);
	TestTrue(
		TEXT("轻微变形的闪电折线可识别"),
		RuneRecognitionTests::FeatureDistance(LightningTemplate, LightningCandidate) < AcceptanceTolerance
	);
	TestTrue(
		TEXT("闪电折线不会被竖线抢先匹配"),
		RuneRecognitionTests::FeatureDistance(LightningTemplate, LightningCandidate)
		< RuneRecognitionTests::FeatureDistance(VerticalTemplate, LightningCandidate)
	);
	TestTrue(TEXT("闪电宽高比在模板范围内"), LightningRatio >= 0.25f && LightningRatio <= 0.90f);

	TArray<float> SpiralTemplate;
	TArray<float> SpiralCandidate;
	float SpiralRatio = 0.0f;
	URuneRecognitionLibrary::BuildStableFeatures(
		{RuneRecognitionTests::MakeSpiral(128, 8.0, 48.0)},
		GridSize,
		SpiralTemplate,
		SpiralRatio
	);
	URuneRecognitionLibrary::BuildStableFeatures(
		{RuneRecognitionTests::MakeSpiral(24, 7.0, 50.0, 1.05, 0.95)},
		GridSize,
		SpiralCandidate,
		SpiralRatio
	);
	TestTrue(
		TEXT("稀疏采样的两圈螺旋可识别"),
		RuneRecognitionTests::FeatureDistance(SpiralTemplate, SpiralCandidate) < AcceptanceTolerance
	);
	TestTrue(
		TEXT("两圈螺旋优先匹配螺旋模板而不是圆"),
		RuneRecognitionTests::FeatureDistance(SpiralTemplate, SpiralCandidate)
		< RuneRecognitionTests::FeatureDistance(CircleTemplate, SpiralCandidate)
	);
	TestTrue(
		TEXT("普通圆优先匹配圆模板而不是螺旋"),
		RuneRecognitionTests::FeatureDistance(CircleTemplate, CircleCandidate)
		< RuneRecognitionTests::FeatureDistance(SpiralTemplate, CircleCandidate)
	);
	TestTrue(TEXT("螺旋宽高比在模板范围内"), SpiralRatio >= 0.6f && SpiralRatio <= 1.67f);
	TestTrue(
		TEXT("闪电不会被螺旋模板误识别"),
		RuneRecognitionTests::FeatureDistance(SpiralTemplate, LightningCandidate) > TemplateTolerance
	);
	TestTrue(
		TEXT("螺旋不会被闪电模板误识别"),
		RuneRecognitionTests::FeatureDistance(LightningTemplate, SpiralCandidate) > TemplateTolerance
	);
	TestTrue(
		TEXT("40 维特征可以直接评分"),
		URuneRecognitionLibrary::ScoreRuneFeatures(CircleTemplate, CircleCandidate) < AcceptanceTolerance
	);
	TestEqual(
		TEXT("特征数量不一致时拒绝匹配"),
		URuneRecognitionLibrary::ScoreRuneFeatures({0.0f}, {0.0f, 1.0f}),
		TNumericLimits<float>::Max()
	);

	return true;
}


IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FRuneRecognitionBlueprintBridgeTest,
	"RuneofSuccor.RuneRecognition.BlueprintBridge",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter
)


bool FRuneRecognitionBlueprintBridgeTest::RunTest(const FString& Parameters)
{
	TArray<float> Features;
	float AspectRatio = 0.0f;
	TestTrue(
		TEXT("蓝图算特征函数可以通过 F笔画 调用原生稳定采样"),
		RuneRecognitionTests::RunBlueprintFeatureFunction(
			{{FVector2D(100.0, 20.0), FVector2D(100.0, 320.0)}},
			Features,
			AspectRatio
		)
	);
	TestEqual(TEXT("蓝图桥接输出 40 个特征"), Features.Num(), 40);
	TestTrue(TEXT("蓝图桥接输出竖线宽高比"), AspectRatio <= 0.4f);
	float FeatureSum = 0.0f;
	for (int32 Index = 0; Index < 36; ++Index)
	{
		FeatureSum += Features[Index];
	}
	TestTrue(TEXT("蓝图桥接网格特征已归一化"), FMath::IsNearlyEqual(FeatureSum, 1.0f, 0.001f));
	return true;
}
#endif
