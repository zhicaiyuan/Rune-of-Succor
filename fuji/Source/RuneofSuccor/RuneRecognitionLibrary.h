#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "RuneRecognitionLibrary.generated.h"


/**
 * 画符识别的稳定特征提取。
 *
 * 接受任意“结构体数组”，结构体中需要包含一个 FVector2D 数组。
 * 这样可以直接接收蓝图现有的 F笔画[]，不需要迁移已有数据结构。
 */
UCLASS()
class RUNEOFSUCCOR_API URuneRecognitionLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	UFUNCTION(
		BlueprintCallable,
		CustomThunk,
		meta = (
			DisplayName = "提取画符特征（稳定采样）",
			ArrayParm = "Strokes",
			AdvancedDisplay = "GridSize",
			GridSize = "6"
		),
		Category = "画符|识别"
	)
	static void ExtractRuneFeatures(
		const TArray<int32>& Strokes,
		TArray<float>& Features,
		float& AspectRatio,
		int32 GridSize = 6
	);

	DECLARE_FUNCTION(execExtractRuneFeatures);

	/** 计算两个画符特征向量的欧氏距离。 */
	UFUNCTION(
		BlueprintPure,
		meta = (DisplayName = "计算画符特征距离"),
		Category = "画符|识别"
	)
	static float ScoreRuneFeatures(
		const TArray<float>& A,
		const TArray<float>& B
	);

	/** 供 C++ 验证与后续扩展使用的类型安全入口。 */
	static bool BuildStableFeatures(
		const TArray<TArray<FVector2D>>& Strokes,
		int32 GridSize,
		TArray<float>& OutFeatures,
		float& OutAspectRatio
	);

private:
	static void GenericExtractRuneFeatures(
		const void* ArrayAddress,
		const FArrayProperty* ArrayProperty,
		TArray<float>& OutFeatures,
		float& OutAspectRatio,
		int32 GridSize
	);
};
