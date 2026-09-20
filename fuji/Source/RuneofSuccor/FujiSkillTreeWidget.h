#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Components/Button.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "FujiSkillTreeWidget.generated.h"

class UCanvasPanel;
class UHorizontalBox;
class UImage;
class UTextBlock;
class UVerticalBox;
class UTexture2D;
class UFujiSkillActionButton;
class UFujiSkillSubsystem;
struct FFujiSkillDefinition;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FFujiSkillButtonInvoked, UFujiSkillActionButton*, Button);

/** 按技能数据绘制符身，不把鼠标选择的印头混入手绘轨迹。 */
UCLASS()
class RUNEOFSUCCOR_API UFujiGlyphPreview : public UUserWidget
{
    GENERATED_BODY()
public:
    FString Shape;
protected:
    virtual int32 NativePaint(const FPaintArgs& Args, const FGeometry& Geometry,
        const FSlateRect& CullingRect, FSlateWindowElementList& Elements, int32 Layer,
        const FWidgetStyle& Style, bool bParentEnabled) const override;
};

/** 带技能标识的按钮；禁学节点仍允许选中查看条件。 */
UCLASS()
class RUNEOFSUCCOR_API UFujiSkillActionButton : public UButton
{
    GENERATED_BODY()
public:
    UPROPERTY(BlueprintReadOnly, Category="符济|技能界面") FName Action;
    UPROPERTY(BlueprintReadOnly, Category="符济|技能界面") FName SkillId;
    UPROPERTY(BlueprintReadOnly, Category="符济|技能界面") int32 SlotIndex = INDEX_NONE;
    UPROPERTY(BlueprintAssignable, Category="符济|技能界面") FFujiSkillButtonInvoked OnInvoked;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Caption;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> StateCaption;
    UPROPERTY(Transient) TObjectPtr<UImage> Icon;
    void InitializeAction(FName InAction, FName InSkillId = NAME_None, int32 InSlotIndex = INDEX_NONE);
    UFUNCTION() void Invoke();
};

/** 复用现有技能蓝图的容器与背景，状态仅从成长子系统读取。 */
UCLASS(Blueprintable)
class RUNEOFSUCCOR_API UFujiSkillTreeWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    UFujiSkillTreeWidget(const FObjectInitializer& ObjectInitializer);

    // 图集键：fire、water、wood、forbidden、passive、mastery。
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="符济|技能界面|美术")
    TMap<FName, TObjectPtr<UTexture2D>> IconAtlases;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="符济|技能界面|美术")
    TObjectPtr<UTexture2D> SealAtlas;
    UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category="符济|技能界面|美术", meta=(ClampMin="42", ClampMax="100"))
    float SkillRowHeight = 52.f;
    UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category="符济|技能界面|美术", meta=(ClampMin="12", ClampMax="28"))
    int32 BodyFontSize = 16;

    UPROPERTY(BlueprintReadOnly, Category="符济|技能界面") FName SelectedSkillId = TEXT("F1");
    UPROPERTY(BlueprintReadOnly, Category="符济|技能界面") int32 SelectedSlotIndex = 0;
    UPROPERTY(BlueprintReadOnly, Category="符济|技能界面") TObjectPtr<UFujiSkillSubsystem> Progression;

    UFUNCTION(BlueprintCallable, Category="符济|技能界面") void RefreshSkillTree();
    UFUNCTION(BlueprintCallable, Category="符济|技能界面") void SelectSkill(FName SkillId);
    UFUNCTION(BlueprintCallable, Category="符济|技能界面") void LearnSelectedSkill();
    UFUNCTION(BlueprintCallable, Category="符济|技能界面") void EquipSelectedSkill();
    UFUNCTION(BlueprintCallable, Category="符济|技能界面") void CloseSkillMenu();
    UFUNCTION(BlueprintPure, Category="符济|技能界面") UButton* GetSkillButton(FName SkillId) const;
    UFUNCTION(BlueprintPure, Category="符济|技能界面") UButton* GetLearnButton() const;
    UFUNCTION(BlueprintPure, Category="符济|技能界面") FText GetDisplayedRequirements() const;
    void EnterMenuMode();

protected:
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual FReply NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& KeyEvent) override;

private:
    UPROPERTY(Transient) TObjectPtr<UCanvasPanel> Canvas;
    UPROPERTY(Transient) TArray<TObjectPtr<UVerticalBox>> Columns;
    UPROPERTY(Transient) TMap<FName, TObjectPtr<UFujiSkillActionButton>> SkillButtons;
    UPROPERTY(Transient) TArray<TObjectPtr<UFujiSkillActionButton>> SlotButtons;
    UPROPERTY(Transient) TObjectPtr<UFujiSkillActionButton> LearnButton;
    UPROPERTY(Transient) TObjectPtr<UFujiSkillActionButton> EquipButton;
    UPROPERTY(Transient) TObjectPtr<UFujiSkillActionButton> UnequipButton;
    UPROPERTY(Transient) TObjectPtr<UFujiSkillActionButton> OrdinaryTab;
    UPROPERTY(Transient) TObjectPtr<UFujiSkillActionButton> ForbiddenTab;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> DetailTitle;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> DetailKind;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> DetailDescription;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> DetailCombat;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> DetailState;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> DetailRequirements;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Feedback;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> SaveWarning;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> LoadoutHint;
    UPROPERTY(Transient) TObjectPtr<UImage> DetailIcon;
    UPROPERTY(Transient) TObjectPtr<UImage> DetailSeal;
    UPROPERTY(Transient) TObjectPtr<UFujiGlyphPreview> DetailGlyph;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> GlyphCaption;
    UPROPERTY(Transient) TObjectPtr<UFujiSkillActionButton> ResetButton;
    UPROPERTY(Transient) TObjectPtr<UFujiSkillActionButton> CancelResetButton;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> ResetHint;
    bool bResetPending = false;
    bool bBuilt = false;
    bool bForbiddenPage = false;
    bool bOwnsMenuInput = false;
    bool bPausedByThisMenu = false;
    bool bPreviousCursor = false;

    void BuildContent();
    void BuildColumns();
    void RefreshDetail();
    void RestoreMenuInput();
    void SetFeedback(const FText& Message, bool bSuccess);
    UTextBlock* MakeText(const FString& Text, int32 Size, const FLinearColor& Color);
    UFujiSkillActionButton* MakeButton(const FString& Label, FName Action, FName SkillId=NAME_None, int32 SlotIndex=INDEX_NONE);
    void ApplyIcon(UImage* Image, const FFujiSkillDefinition& Definition, float Size);
    void StyleButton(UFujiSkillActionButton* Button, const FLinearColor& Accent, bool bSelected=false, bool bAvailable=false);
    UFUNCTION() void HandleButton(UFujiSkillActionButton* Button);
};

/** 由现有 PlayerController 的 K 键调用，不改变角色/画符蓝图。 */
UCLASS()
class RUNEOFSUCCOR_API UFujiSkillMenuLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="符济|技能界面", meta=(DisplayName="切换技能构筑菜单"))
    static void ToggleSkillMenu(APlayerController* PlayerController, TSubclassOf<UFujiSkillTreeWidget> WidgetClass);
};
