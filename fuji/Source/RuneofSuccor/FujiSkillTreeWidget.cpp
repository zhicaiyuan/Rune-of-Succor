#include "FujiSkillTreeWidget.h"
#include "FujiSkillSubsystem.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Components/Border.h"
#include "Components/ButtonSlot.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "GameFramework/PlayerController.h"
#include "Brushes/SlateRoundedBoxBrush.h"
#include "Styling/CoreStyle.h"
#include "InputCoreTypes.h"
#include "UObject/UnrealType.h"
#include "Rendering/DrawElements.h"

int32 UFujiGlyphPreview::NativePaint(const FPaintArgs& Args, const FGeometry& Geometry,
    const FSlateRect& CullingRect, FSlateWindowElementList& Elements, int32 Layer,
    const FWidgetStyle& Style, bool bParentEnabled) const
{
    const int32 Base = Super::NativePaint(Args,Geometry,CullingRect,Elements,Layer,Style,bParentEnabled);
    const FVector2D Size = Geometry.GetLocalSize();
    const float Side=FMath::Min(Size.X,Size.Y);
    const FVector2D Origin=(Size-FVector2D(Side,Side))*.5f;
    const auto Stroke = [&](TArray<FVector2D> Points)
    {
        for (auto& P : Points) P = Origin+P*Side;
        FSlateDrawElement::MakeLines(Elements,Base+1,Geometry.ToPaintGeometry(),Points,
            ESlateDrawEffect::None,FLinearColor(.045f,.05f,.045f,1.f),true,3.f);
    };
    if (Shape==TEXT("一")) Stroke({{.15,.5},{.85,.5}});
    else if (Shape==TEXT("×")) { Stroke({{.22,.18},{.78,.82}}); Stroke({{.78,.18},{.22,.82}}); }
    else if (Shape==TEXT("竖线")) Stroke({{.5,.12},{.5,.88}});
    else if (Shape==TEXT("闪电")) Stroke({{.70,.10},{.35,.45},{.64,.45},{.30,.90}});
    else if (Shape==TEXT("○") || Shape==TEXT("螺旋"))
    {
        TArray<FVector2D> Points;
        const bool bSpiral=Shape==TEXT("螺旋");
        for (int32 I=0; I<=80; ++I)
        {
            const float T=float(I)/80.f;
            const float A=-PI/2+T*2*PI*(bSpiral ? 1.75f : 1.f);
            const float R=bSpiral ? .38f*(1-.85f*T) : .35f;
            Points.Add({.5f+FMath::Cos(A)*R,.5f+FMath::Sin(A)*R});
        }
        Stroke(Points);
    }
    return Base+1;
}

namespace FujiUI
{
    const FLinearColor Ink=FLinearColor::FromSRGBColor(FColor(33,38,37));
    const FLinearColor Muted=FLinearColor::FromSRGBColor(FColor(87,89,82));
    const FLinearColor Cinnabar=FLinearColor::FromSRGBColor(FColor(130,42,29));
    const FLinearColor Paper(.90f,.86f,.76f,1.f);
    const FLinearColor Learned=FLinearColor::FromSRGBColor(FColor(56,87,69));

    FLinearColor Accent(FName Id)
    {
        const FString Name = Id.ToString();
        if (Name.StartsWith(TEXT("F"))) return FLinearColor::FromSRGBColor(FColor(130,61,31));
        if (Name.StartsWith(TEXT("W"))) return FLinearColor::FromSRGBColor(FColor(48,82,92));
        if (Name.StartsWith(TEXT("M"))) return FLinearColor::FromSRGBColor(FColor(64,89,59));
        return FLinearColor::FromSRGBColor(FColor(92,64,97));
    }

    void Place(UCanvasPanel* Canvas, UWidget* Widget, float X, float Y, float R, float B)
    {
        UCanvasPanelSlot* Slot = Cast<UCanvasPanelSlot>(Widget->Slot);
        if (!Slot) Slot = Canvas->AddChildToCanvas(Widget);
        Slot->SetAnchors(FAnchors(X,Y,R,B));
        Slot->SetOffsets(FMargin(0));
        Slot->SetAlignment(FVector2D::ZeroVector);
    }

    void AddLine(UVerticalBox* Box, UWidget* Widget, float Bottom=10.f)
    {
        auto* Slot = Box->AddChildToVerticalBox(Widget);
        Slot->SetPadding(FMargin(0,0,0,Bottom));
        Slot->SetHorizontalAlignment(HAlign_Fill);
    }
}

void UFujiSkillActionButton::InitializeAction(FName InAction, FName InSkillId, int32 InSlotIndex)
{
    Action = InAction;
    SkillId = InSkillId;
    SlotIndex = InSlotIndex;
    OnClicked.AddUniqueDynamic(this, &UFujiSkillActionButton::Invoke);
}

void UFujiSkillActionButton::Invoke()
{
    if (GetIsEnabled()) OnInvoked.Broadcast(this);
}

UFujiSkillTreeWidget::UFujiSkillTreeWidget(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    SetIsFocusable(true);
}

UTextBlock* UFujiSkillTreeWidget::MakeText(const FString& Text, int32 Size, const FLinearColor& Color)
{
    UTextBlock* Result = WidgetTree->ConstructWidget<UTextBlock>();
    Result->SetText(FText::FromString(Text));
    Result->SetFont(FCoreStyle::GetDefaultFontStyle(TEXT("Regular"), Size));
    Result->SetColorAndOpacity(FSlateColor(Color));
    Result->SetAutoWrapText(true);
    Result->SetVisibility(ESlateVisibility::HitTestInvisible);
    return Result;
}

void UFujiSkillTreeWidget::StyleButton(UFujiSkillActionButton* Button, const FLinearColor& Accent, bool bSelected, bool bAvailable)
{
    FButtonStyle Style;
    const FLinearColor Frame = bSelected ? Accent : (bAvailable ? FujiUI::Cinnabar : FLinearColor(.48f,.46f,.40f,.5f));
    Style.SetNormal(FSlateRoundedBoxBrush(FLinearColor(.93f,.90f,.82f,.86f), 0.f, Frame, bSelected ? 2.f : 1.f));
    Style.SetHovered(FSlateRoundedBoxBrush(FLinearColor(.99f,.96f,.88f,1.f), 0.f, Accent, 2.f));
    Style.SetPressed(FSlateRoundedBoxBrush(FLinearColor(.78f,.73f,.62f,1.f), 0.f, Accent, 2.f));
    Style.SetDisabled(FSlateRoundedBoxBrush(FLinearColor(.77f,.75f,.68f,.75f), 0.f, FLinearColor(.5f,.48f,.42f,.45f), 1.f));
    Style.SetNormalPadding(FMargin(9,3));
    Style.SetPressedPadding(FMargin(9,4,9,2));
    Button->SetStyle(Style);
    Button->SetBackgroundColor(FLinearColor::White);
    Button->SetColorAndOpacity(FLinearColor::White);
}

UFujiSkillActionButton* UFujiSkillTreeWidget::MakeButton(const FString& Label, FName Action, FName SkillId, int32 SlotIndex)
{
    auto* Button = WidgetTree->ConstructWidget<UFujiSkillActionButton>();
    Button->InitializeAction(Action, SkillId, SlotIndex);
    Button->OnInvoked.AddDynamic(this, &UFujiSkillTreeWidget::HandleButton);
    Button->Caption = MakeText(Label, BodyFontSize, FujiUI::Ink);
    Button->Caption->SetJustification(ETextJustify::Center);
    Button->AddChild(Button->Caption);
    StyleButton(Button, FujiUI::Cinnabar);
    return Button;
}

void UFujiSkillTreeWidget::NativeConstruct()
{
    Super::NativeConstruct();
    if (UGameInstance* GI = GetGameInstance()) Progression = GI->GetSubsystem<UFujiSkillSubsystem>();
    if (!bBuilt) BuildContent();
    if (Progression) Progression->OnBuildChanged.AddUniqueDynamic(this, &UFujiSkillTreeWidget::RefreshSkillTree);
    BuildColumns();
    RefreshSkillTree();
}

void UFujiSkillTreeWidget::NativeDestruct()
{
    if (Progression) Progression->OnBuildChanged.RemoveDynamic(this, &UFujiSkillTreeWidget::RefreshSkillTree);
    RestoreMenuInput();
    Super::NativeDestruct();
}

void UFujiSkillTreeWidget::BuildContent()
{
    if (!WidgetTree) return;
    Canvas = Cast<UCanvasPanel>(WidgetTree->RootWidget);
    if (!Canvas)
    {
        Canvas = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("SkillRoot"));
        WidgetTree->RootWidget = Canvas;
        auto* Background = WidgetTree->ConstructWidget<UBorder>();
        Background->SetBrushColor(FujiUI::Paper);
        Canvas->AddChild(Background);
        FujiUI::Place(Canvas, Background, 0,0,1,1);
    }

    if (auto* Placeholder = GetWidgetFromName(TEXT("Button_81"))) Placeholder->RemoveFromParent();
    if (auto* Header = GetWidgetFromName(TEXT("学习显示框")))
        FujiUI::Place(Canvas, Header, .055f,.125f,.70f,.17f);

    auto* Skills = Cast<UHorizontalBox>(GetWidgetFromName(TEXT("技能栏")));
    if (!Skills) Skills = WidgetTree->ConstructWidget<UHorizontalBox>();
    FujiUI::Place(Canvas, Skills, .055f,.24f,.70f,.815f);
    const TCHAR* Names[] = {TEXT("VerticalBox_121"), TEXT("VerticalBox_241"), TEXT("VerticalBox_71")};
    Columns.Reset();
    for (int32 Index=0; Index<3; ++Index)
    {
        auto* Column = Cast<UVerticalBox>(GetWidgetFromName(Names[Index]));
        if (!Column) Column = WidgetTree->ConstructWidget<UVerticalBox>();
        Column->RemoveFromParent();
        Column->ClearChildren();
        Columns.Add(Column);
    }
    Skills->ClearChildren();
    for (const auto& Column : Columns)
    {
        auto* Scroll = WidgetTree->ConstructWidget<UScrollBox>();
        Scroll->SetScrollbarThickness(FVector2D(3,3));
        Scroll->AddChild(Column);
        auto* ColumnSlot = Skills->AddChildToHorizontalBox(Scroll);
        ColumnSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        ColumnSlot->SetPadding(FMargin(0,0,14,0));
    }

    auto* Tabs = WidgetTree->ConstructWidget<UHorizontalBox>();
    OrdinaryTab = MakeButton(TEXT("三系修习"), TEXT("Ordinary"));
    ForbiddenTab = MakeButton(TEXT("混系禁术"), TEXT("Forbidden"));
    for (auto* Button : {OrdinaryTab.Get(), ForbiddenTab.Get()})
    {
        auto* TabSlot = Tabs->AddChildToHorizontalBox(Button);
        TabSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        TabSlot->SetPadding(FMargin(0,0,14,0));
    }
    FujiUI::Place(Canvas, Tabs, .055f,.185f,.365f,.225f);
    auto* Legend = MakeText(TEXT("朱砂边 · 可学     淡墨 · 未达条件     青印 · 已学"), 15, FujiUI::Muted);
    FujiUI::Place(Canvas, Legend, .39f,.19f,.70f,.225f);

    auto* DetailHost = Cast<UVerticalBox>(GetWidgetFromName(TEXT("VerticalBox_332")));
    if (!DetailHost) DetailHost = WidgetTree->ConstructWidget<UVerticalBox>();
    auto* OldPaper = Cast<UImage>(GetWidgetFromName(TEXT("背景板")));
    if (OldPaper) OldPaper->RemoveFromParent();
    DetailHost->ClearChildren();
    FujiUI::Place(Canvas, DetailHost, .735f,.14f,.963f,.90f);
    auto* DetailOverlay = WidgetTree->ConstructWidget<UOverlay>();
    auto* DetailHostSlot = DetailHost->AddChildToVerticalBox(DetailOverlay);
    DetailHostSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    if (OldPaper)
    {
        OldPaper->SetVisibility(ESlateVisibility::HitTestInvisible);
        auto* PaperSlot = DetailOverlay->AddChildToOverlay(OldPaper);
        PaperSlot->SetHorizontalAlignment(HAlign_Fill);
        PaperSlot->SetVerticalAlignment(VAlign_Fill);
    }
    auto* DetailBorder = WidgetTree->ConstructWidget<UBorder>();
    DetailBorder->SetBrushColor(FLinearColor(.94f,.91f,.82f,OldPaper ? .30f : .97f));
    DetailBorder->SetPadding(FMargin(26,24));
    auto* BorderSlot = DetailOverlay->AddChildToOverlay(DetailBorder);
    BorderSlot->SetHorizontalAlignment(HAlign_Fill);
    BorderSlot->SetVerticalAlignment(VAlign_Fill);
    auto* DetailScroll = WidgetTree->ConstructWidget<UScrollBox>();
    DetailScroll->SetScrollbarThickness(FVector2D(3,3));
    DetailBorder->AddChild(DetailScroll);
    auto* Details = WidgetTree->ConstructWidget<UVerticalBox>();
    DetailScroll->AddChild(Details);
    DetailTitle = MakeText(TEXT("选中技能"), 28, FujiUI::Ink);
    DetailKind = MakeText(TEXT(""), 15, FujiUI::Muted);
    DetailIcon = WidgetTree->ConstructWidget<UImage>();
    auto* IconBox = WidgetTree->ConstructWidget<USizeBox>();
    IconBox->SetWidthOverride(64);
    IconBox->SetHeightOverride(64);
    IconBox->AddChild(DetailIcon);
    auto* IconSlot = Details->AddChildToVerticalBox(IconBox);
    IconSlot->SetHorizontalAlignment(HAlign_Center);
    IconSlot->SetPadding(FMargin(0,0,0,12));
    FujiUI::AddLine(Details,DetailTitle,4);
    FujiUI::AddLine(Details,DetailKind,8);
    auto* CastingRow=WidgetTree->ConstructWidget<UHorizontalBox>();
    auto* SealColumn=WidgetTree->ConstructWidget<UVerticalBox>();
    CastingRow->AddChildToHorizontalBox(SealColumn)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    FujiUI::AddLine(SealColumn,MakeText(TEXT("选择印头"),13,FujiUI::Muted),4);
    DetailSeal=WidgetTree->ConstructWidget<UImage>();
    auto* SealBox=WidgetTree->ConstructWidget<USizeBox>();
    SealBox->SetWidthOverride(165); SealBox->SetHeightOverride(57);
    SealBox->AddChild(DetailSeal); FujiUI::AddLine(SealColumn,SealBox,0);
    auto* GlyphColumn=WidgetTree->ConstructWidget<UVerticalBox>();
    CastingRow->AddChildToHorizontalBox(GlyphColumn)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    GlyphCaption=MakeText(TEXT("画符形状"),13,FujiUI::Muted);
    FujiUI::AddLine(GlyphColumn,GlyphCaption,2);
    DetailGlyph=WidgetTree->ConstructWidget<UFujiGlyphPreview>();
    auto* GlyphBox=WidgetTree->ConstructWidget<USizeBox>();
    GlyphBox->SetWidthOverride(100); GlyphBox->SetHeightOverride(64);
    GlyphBox->AddChild(DetailGlyph); FujiUI::AddLine(GlyphColumn,GlyphBox,0);
    FujiUI::AddLine(Details,CastingRow,12);
    DetailDescription = MakeText(TEXT(""), BodyFontSize, FujiUI::Ink);
    DetailCombat = MakeText(TEXT(""), 15, FujiUI::Muted);
    DetailState = MakeText(TEXT(""), 21, FujiUI::Cinnabar);
    DetailRequirements = MakeText(TEXT(""), BodyFontSize-1, FujiUI::Ink);
    FujiUI::AddLine(Details,DetailDescription,16);
    FujiUI::AddLine(Details,DetailCombat,20);
    FujiUI::AddLine(Details,DetailState,8);
    FujiUI::AddLine(Details,DetailRequirements,18);
    LearnButton = MakeButton(TEXT("修习"),TEXT("Learn"));
    EquipButton = MakeButton(TEXT("装备至所选符位"),TEXT("Equip"));
    UnequipButton = MakeButton(TEXT("卸下此符"),TEXT("Unequip"));
    for (auto* Button : {LearnButton.Get(),EquipButton.Get(),UnequipButton.Get()})
    {
        auto* Box = WidgetTree->ConstructWidget<USizeBox>();
        Box->SetMinDesiredHeight(44);
        Box->AddChild(Button);
        FujiUI::AddLine(Details,Box,10);
    }
    Feedback = MakeText(TEXT(""),15,FujiUI::Muted);
    FujiUI::AddLine(Details,Feedback);

    auto* Loadout = WidgetTree->ConstructWidget<UHorizontalBox>();
    SlotButtons.Reset();
    for (int32 Index=0; Index<5; ++Index)
    {
        auto* Button = MakeButton(TEXT("空符位"),TEXT("Slot"),NAME_None,Index);
        Button->Caption->SetFont(FCoreStyle::GetDefaultFontStyle(TEXT("Regular"),16));
        Button->ClearChildren();
        auto* Row=WidgetTree->ConstructWidget<UHorizontalBox>();
        Button->AddChild(Row);
        CastChecked<UButtonSlot>(Row->Slot)->SetPadding(FMargin(0));
        CastChecked<UButtonSlot>(Row->Slot)->SetHorizontalAlignment(HAlign_Fill);
        auto* SlotIconBox=WidgetTree->ConstructWidget<USizeBox>();
        SlotIconBox->SetWidthOverride(44); SlotIconBox->SetHeightOverride(44);
        Button->Icon=WidgetTree->ConstructWidget<UImage>();
        SlotIconBox->AddChild(Button->Icon);
        Row->AddChildToHorizontalBox(SlotIconBox)->SetVerticalAlignment(VAlign_Center);
        auto* LabelSlot=Row->AddChildToHorizontalBox(Button->Caption);
        LabelSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        LabelSlot->SetVerticalAlignment(VAlign_Center);
        auto* LoadoutSlot = Loadout->AddChildToHorizontalBox(Button);
        LoadoutSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        LoadoutSlot->SetPadding(FMargin(0,0,14,0));
        SlotButtons.Add(Button);
    }
    LoadoutHint = MakeText(TEXT("五符构筑 · 点击符位选择装配位置；最多装备一道禁术"),15,FujiUI::Muted);
    FujiUI::Place(Canvas,LoadoutHint,.055f,.835f,.70f,.87f);
    FujiUI::Place(Canvas,Loadout,.055f,.88f,.70f,.942f);
    SaveWarning = MakeText(TEXT(""),14,FujiUI::Cinnabar);
    FujiUI::Place(Canvas,SaveWarning,.055f,.955f,.89f,.988f);
    auto* Close = MakeButton(TEXT("返回  /  K"),TEXT("Close"));
    FujiUI::Place(Canvas,Close,.85f,.065f,.962f,.108f);
    ResetButton=MakeButton(TEXT("重置修习点"),TEXT("Reset"));
    FujiUI::Place(Canvas,ResetButton,.69f,.065f,.835f,.108f);
    CancelResetButton=MakeButton(TEXT("取消"),TEXT("CancelReset"));
    FujiUI::Place(Canvas,CancelResetButton,.61f,.065f,.68f,.108f);
    CancelResetButton->SetVisibility(ESlateVisibility::Collapsed);
    ResetHint=MakeText(TEXT(""),14,FujiUI::Cinnabar);
    FujiUI::Place(Canvas,ResetHint,.055f,.062f,.60f,.115f);
    ResetButton->SetToolTipText(FText::FromString(TEXT("返还已花费修习点，清空符位与精通；保留基础技能和剧情解锁。")));
    bBuilt = true;
}

void UFujiSkillTreeWidget::EnterMenuMode()
{
    APlayerController* PC = GetOwningPlayer();
    if (!PC || bOwnsMenuInput) return;
    bPreviousCursor = PC->bShowMouseCursor;
    bPausedByThisMenu = !PC->IsPaused() && PC->SetPause(true);
    bOwnsMenuInput = true;
    PC->bShowMouseCursor = true;
    FInputModeUIOnly Mode;
    Mode.SetWidgetToFocus(TakeWidget());
    Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    PC->SetInputMode(Mode);
    SetKeyboardFocus();
}

void UFujiSkillTreeWidget::RestoreMenuInput()
{
    if (!bOwnsMenuInput) return;
    bOwnsMenuInput = false;
    if (APlayerController* PC = GetOwningPlayer())
    {
        if (bPausedByThisMenu) PC->SetPause(false);
        PC->bShowMouseCursor = bPreviousCursor;
        PC->SetInputMode(FInputModeGameOnly());
        PC->FlushPressedKeys();
    }
    bPausedByThisMenu = false;
}

void UFujiSkillTreeWidget::CloseSkillMenu()
{
    RestoreMenuInput();
    RemoveFromParent();
}

FReply UFujiSkillTreeWidget::NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& KeyEvent)
{
    if (KeyEvent.GetKey()==EKeys::Escape || KeyEvent.GetKey()==EKeys::K)
    {
        CloseSkillMenu();
        return FReply::Handled();
    }
    return Super::NativeOnPreviewKeyDown(Geometry,KeyEvent);
}

void UFujiSkillMenuLibrary::ToggleSkillMenu(APlayerController* PlayerController, TSubclassOf<UFujiSkillTreeWidget> WidgetClass)
{
    if (!PlayerController || !PlayerController->IsLocalController() || !WidgetClass) return;
    TArray<UUserWidget*> Existing;
    UWidgetBlueprintLibrary::GetAllWidgetsOfClass(PlayerController,Existing,WidgetClass,true);
    for (auto* Widget : Existing)
    {
        if (auto* Menu = Cast<UFujiSkillTreeWidget>(Widget); Menu && Menu->IsInViewport())
        {
            Menu->CloseSkillMenu();
            return;
        }
    }
    // 画符和其它已占用鼠标的界面结束后才接管输入。
    if (PlayerController->bShowMouseCursor || PlayerController->IsPaused()) return;
    if (auto* Menu = CreateWidget<UFujiSkillTreeWidget>(PlayerController,WidgetClass))
    {
        Menu->AddToViewport(100);
        Menu->EnterMenuMode();
    }
}

UButton* UFujiSkillTreeWidget::GetSkillButton(FName SkillId) const
{
    if (const auto* Button = SkillButtons.Find(SkillId)) return Button->Get();
    return nullptr;
}

UButton* UFujiSkillTreeWidget::GetLearnButton() const { return LearnButton; }
FText UFujiSkillTreeWidget::GetDisplayedRequirements() const { return DetailRequirements ? DetailRequirements->GetText() : FText::GetEmpty(); }

void UFujiSkillTreeWidget::SetFeedback(const FText& Message, bool bSuccess)
{
    if (!Feedback) return;
    Feedback->SetText(Message);
    Feedback->SetColorAndOpacity(FSlateColor(bSuccess ? FujiUI::Learned : FujiUI::Cinnabar));
}

void UFujiSkillTreeWidget::ApplyIcon(UImage* Image, const FFujiSkillDefinition& Definition, float Size)
{
    if (!Image) return;
    const FString Id = Definition.SkillId.ToString();
    const int32 SchoolIndex = Id.StartsWith(TEXT("F")) ? 0 : (Id.StartsWith(TEXT("W")) ? 1 : 2);
    int32 ColumnsCount=3, Rows=2, Column=0, Row=0;
    FName AtlasKey;
    if (Definition.Kind==EFujiSkillKind::Mastery)
    {
        AtlasKey=TEXT("mastery"); Rows=1; Column=SchoolIndex;
    }
    else if (Definition.Kind==EFujiSkillKind::Passive)
    {
        AtlasKey=TEXT("passive"); Rows=3; Row=SchoolIndex;
        Column=FCString::Atoi(*Id.Right(1))-1;
    }
    else
    {
        AtlasKey = Definition.School==EFujiSkillSchool::Fire ? TEXT("fire") :
            (Definition.School==EFujiSkillSchool::Water ? TEXT("water") :
            (Definition.School==EFujiSkillSchool::Wood ? TEXT("wood") : TEXT("forbidden")));
        const int32 Index=FMath::Max(0,FCString::Atoi(*Id.Right(1))-1);
        Column=Index%3; Row=Index/3;
    }
    FSlateBrush Brush;
    Brush.DrawAs=ESlateBrushDrawType::Image;
    Brush.ImageSize=FVector2D(Size,Size);
    if (auto* Texture=IconAtlases.Find(AtlasKey)) Brush.SetResourceObject(Texture->Get());
    Brush.SetUVRegion(FBox2f(FVector2f(float(Column)/ColumnsCount,float(Row)/Rows),
                            FVector2f(float(Column+1)/ColumnsCount,float(Row+1)/Rows)));
    Image->SetBrush(Brush);
    Image->SetVisibility(ESlateVisibility::HitTestInvisible);
}

void UFujiSkillTreeWidget::BuildColumns()
{
    if (!bBuilt || !Progression) return;
    SkillButtons.Reset();
    const TCHAR* Titles[] = {TEXT("离火 · 输出"),TEXT("玄水 · 增伤"),TEXT("青木 · 控制与回复")};
    for (int32 I=0; I<Columns.Num(); ++I)
    {
        Columns[I]->ClearChildren();
        FujiUI::AddLine(Columns[I],MakeText(bForbiddenPage ? TEXT("禁印 · 须先发现") : Titles[I],20,FujiUI::Ink),14);
    }
    const auto Definitions=Progression->GetAllSkills();
    int32 HiddenIndex=0;
    for (const FFujiSkillDefinition& Definition : Definitions)
    {
        const bool bHidden=Definition.Kind==EFujiSkillKind::Hidden;
        if (bHidden!=bForbiddenPage) continue;
        const int32 Column=bHidden ? (HiddenIndex++%3) :
            (Definition.School==EFujiSkillSchool::Fire ? 0 : (Definition.School==EFujiSkillSchool::Water ? 1 : 2));
        auto* Button=MakeButton(Definition.DisplayName.ToString(),TEXT("Select"),Definition.SkillId);
        Button->ClearChildren();
        auto* Row=WidgetTree->ConstructWidget<UHorizontalBox>();
        Button->AddChild(Row);
        CastChecked<UButtonSlot>(Row->Slot)->SetHorizontalAlignment(HAlign_Fill);
        CastChecked<UButtonSlot>(Row->Slot)->SetPadding(FMargin(0));
        auto* IconBox=WidgetTree->ConstructWidget<USizeBox>();
        IconBox->SetWidthOverride(42);
        IconBox->SetHeightOverride(42);
        Button->Icon=WidgetTree->ConstructWidget<UImage>();
        ApplyIcon(Button->Icon,Definition,42);
        IconBox->AddChild(Button->Icon);
        auto* IconSlot=Row->AddChildToHorizontalBox(IconBox);
        IconSlot->SetVerticalAlignment(VAlign_Center);
        IconSlot->SetPadding(FMargin(0,0,10,0));
        auto* Labels=WidgetTree->ConstructWidget<UVerticalBox>();
        auto* LabelSlot=Row->AddChildToHorizontalBox(Labels);
        LabelSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        LabelSlot->SetVerticalAlignment(VAlign_Center);
        Button->Caption->SetJustification(ETextJustify::Left);
        Labels->AddChild(Button->Caption);
        Button->StateCaption=MakeText(TEXT(""),12,FujiUI::Muted);
        Labels->AddChild(Button->StateCaption);
        auto* Box=WidgetTree->ConstructWidget<USizeBox>();
        Box->SetMinDesiredHeight(SkillRowHeight);
        Box->AddChild(Button);
        FujiUI::AddLine(Columns[Column],Box,4);
        SkillButtons.Add(Definition.SkillId,Button);
    }
    StyleButton(OrdinaryTab,FujiUI::Cinnabar,!bForbiddenPage);
    StyleButton(ForbiddenTab,FujiUI::Accent(TEXT("H1")),bForbiddenPage);
}

void UFujiSkillTreeWidget::RefreshSkillTree()
{
    if (!bBuilt || !Progression) return;
    // 兼容原蓝图的“刷新顶栏”函数，旧展示变量只从子系统同步，不能作为扣点来源。
    const auto SyncLegacy=[this](const TCHAR* Name,int32 Value)
    {
        if (auto* Property=FindFProperty<FIntProperty>(GetClass(),Name)) Property->SetPropertyValue_InContainer(this,Value);
    };
    SyncLegacy(TEXT("剩余修习点"),Progression->GetAvailablePoints());
    SyncLegacy(TEXT("火投入点数"),Progression->GetSchoolInvestment(EFujiSkillSchool::Fire));
    SyncLegacy(TEXT("水投入点数"),Progression->GetSchoolInvestment(EFujiSkillSchool::Water));
    SyncLegacy(TEXT("木投入点数"),Progression->GetSchoolInvestment(EFujiSkillSchool::Wood));
    const auto SetHeader=[this](const TCHAR* Name,const FString& Value)
    {
        if (auto* Label=Cast<UTextBlock>(GetWidgetFromName(Name)))
        {
            Label->SetText(FText::FromString(Value));
            Label->SetFont(FCoreStyle::GetDefaultFontStyle(TEXT("Regular"),BodyFontSize));
            Label->SetColorAndOpacity(FSlateColor(FujiUI::Ink));
            if (auto* Slot=Cast<UHorizontalBoxSlot>(Label->Slot)) Slot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        }
    };
    SetHeader(TEXT("修习点"),FString::Printf(TEXT("修习点  %d"),Progression->GetAvailablePoints()));
    SetHeader(TEXT("火投入"),FString::Printf(TEXT("火投入  %d"),Progression->GetSchoolInvestment(EFujiSkillSchool::Fire)));
    SetHeader(TEXT("水投入"),FString::Printf(TEXT("水投入  %d"),Progression->GetSchoolInvestment(EFujiSkillSchool::Water)));
    SetHeader(TEXT("木投入"),FString::Printf(TEXT("木投入  %d"),Progression->GetSchoolInvestment(EFujiSkillSchool::Wood)));
    FFujiSkillDefinition Mastery;
    const bool bMastered=Progression->GetSkillDefinition(Progression->GetSelectedMastery(),Mastery);
    SetHeader(TEXT("精通"),bMastered ? FString(TEXT("精通  "))+Mastery.DisplayName.ToString() : TEXT("精通  未选择"));
    for (auto& Entry : SkillButtons)
    {
        auto* Button=Entry.Value.Get();
        const auto View=Progression->GetNodeView(Entry.Key);
        FFujiSkillDefinition Definition;
        Progression->GetSkillDefinition(Entry.Key,Definition);
        FString Status;
        if (Definition.Kind==EFujiSkillKind::Passive)
            Status=FString::Printf(TEXT("被动 %d/%d · %s"),View.Rank,Definition.MaxRank,
                View.bCanLearn ? (View.Rank>0 ? TEXT("可精进") : TEXT("可修习")) : (View.Rank==Definition.MaxRank ? TEXT("已圆满") : TEXT("条件未达")));
        else if (View.bIsSelectedMastery) Status=TEXT("精通 · 当前道途");
        else if (View.bIsEquipped) Status=FString::Printf(TEXT("已学 · 装备于符位 %d"),View.EquippedSlot+1);
        else if (View.Rank>0) Status=TEXT("已学 · 未装备");
        else Status=View.bCanLearn ? TEXT("可修习") : TEXT("未解锁 · 点击查看条件");
        if (Definition.Kind==EFujiSkillKind::Mastery && !View.bIsSelectedMastery)
            Status=FString(TEXT("精通 · "))+(View.bCanLearn ? TEXT("可选择") : TEXT("条件未达"));
        Button->StateCaption->SetText(FText::FromString(Status));
        Button->StateCaption->SetColorAndOpacity(FSlateColor(View.bCanLearn ? FujiUI::Cinnabar : (View.Rank>0 ? FujiUI::Learned : FujiUI::Muted)));
        Button->Icon->SetColorAndOpacity(View.Rank>0 || View.bCanLearn ? FLinearColor::White : FLinearColor(.40f,.40f,.40f,.75f));
        // 学习许可与控件可点击性独立，锁定节点也能打开详情。
        Button->SetIsEnabled(true);
        StyleButton(Button,FujiUI::Accent(Entry.Key),SelectedSkillId==Entry.Key,View.bCanLearn);
        Button->SetToolTipText(View.bCanLearn ? FText::FromString(TEXT("可以修习，点击查看技能详情。")) : View.BlockReason);
    }
    const auto Slots=Progression->GetEquippedSlots();
    for (int32 I=0; I<SlotButtons.Num(); ++I)
    {
        FFujiSkillDefinition Definition;
        const FName Id=Slots.IsValidIndex(I) ? Slots[I] : NAME_None;
        const bool bHasSkill=Progression->GetSkillDefinition(Id,Definition);
        SlotButtons[I]->SkillId=Id;
        if (bHasSkill) ApplyIcon(SlotButtons[I]->Icon,Definition,44);
        else { SlotButtons[I]->Icon->SetBrush(FSlateBrush()); SlotButtons[I]->Icon->SetVisibility(ESlateVisibility::Hidden); }
        SlotButtons[I]->Caption->SetText(FText::FromString(FString::Printf(TEXT("符位 %d\n%s"),I+1,
            bHasSkill ? *Definition.DisplayName.ToString() : TEXT("空位"))));
        StyleButton(SlotButtons[I],FujiUI::Cinnabar,I==SelectedSlotIndex);
    }
    SaveWarning->SetText(Progression->LastPersistenceError.IsEmpty() ? FText::GetEmpty() :
        FText::FromString(FString(TEXT("保存提示："))+Progression->LastPersistenceError.ToString()));
    ResetButton->SetIsEnabled(Progression->bBuildChangesAllowed);
    RefreshDetail();
}

void UFujiSkillTreeWidget::RefreshDetail()
{
    if (!Progression || !DetailTitle) return;
    FFujiSkillDefinition Definition;
    if (!Progression->GetSkillDefinition(SelectedSkillId,Definition)) return;
    const auto View=Progression->GetNodeView(SelectedSkillId);
    DetailTitle->SetText(Definition.DisplayName);
    const TCHAR* Kind=Definition.Kind==EFujiSkillKind::Passive ? TEXT("被动 · 学习后纳入构筑") :
        (Definition.Kind==EFujiSkillKind::Mastery ? TEXT("精通 · 同时只能选择一种") :
        (Definition.Kind==EFujiSkillKind::Hidden ? TEXT("禁术 · 占用一道主动符位") : TEXT("主动 · 学习后可装备")));
    DetailKind->SetText(FText::FromString(Kind));
    DetailDescription->SetText(Definition.Description);
    ApplyIcon(DetailIcon,Definition,64);
    const int32 SchoolRow=static_cast<int32>(Definition.School);
    FSlateBrush SealBrush;
    SealBrush.DrawAs=ESlateBrushDrawType::Image;
    SealBrush.SetResourceObject(SealAtlas);
    SealBrush.ImageSize=FVector2D(165,57);
    // 原印头按钮图集左列四行，裁取完整按钮边框。
    const float Top[]={.047f,.279f,.512f,.745f};
    const float Bottom[]={.255f,.488f,.722f,.952f};
    SealBrush.SetUVRegion(FBox2f(FVector2f(.083f,Top[SchoolRow]),FVector2f(.478f,Bottom[SchoolRow])));
    DetailSeal->SetBrush(SealBrush);
    DetailSeal->SetVisibility(ESlateVisibility::HitTestInvisible);
    FString Head, Shape;
    Definition.Glyph.ToString().Split(TEXT("＋"),&Head,&Shape);
    DetailGlyph->Shape=Shape;
    DetailGlyph->InvalidateLayoutAndVolatility();
    GlyphCaption->SetText(FText::FromString(Shape.IsEmpty() ? TEXT("无需画符") : FString(TEXT("画符 · "))+Shape));
    DetailGlyph->SetVisibility(Shape.IsEmpty() ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
    DetailCombat->SetText((Definition.Kind==EFujiSkillKind::Active || Definition.Kind==EFujiSkillKind::Hidden) ?
        FText::FromString(FString::Printf(TEXT("灵墨 %d    调息 %.0f 秒%s"),Definition.InkCost,Definition.CooldownSeconds,
            Definition.ChaosGain>0 ? *FString::Printf(TEXT("    混沌 +%d"),Definition.ChaosGain) : TEXT(""))) : FText::GetEmpty());
    const bool bMaxed=View.Rank>=Definition.MaxRank;
    FString Status=View.bCanLearn ? (View.Rank>0 ? TEXT("可以精进") : TEXT("可以修习")) : (bMaxed ? TEXT("已经掌握") : TEXT("尚未满足条件"));
    if (View.bIsEquipped) Status=FString::Printf(TEXT("已装备 · 符位 %d"),View.EquippedSlot+1);
    if (View.bIsSelectedMastery) Status=TEXT("当前精通");
    DetailState->SetText(FText::FromString(Status));
    DetailState->SetColorAndOpacity(FSlateColor(View.Rank>0 ? FujiUI::Learned : (View.bCanLearn ? FujiUI::Cinnabar : FujiUI::Muted)));

    TArray<FString> Lines;
    const auto AddCondition=[&Lines](bool bMet,const FString& Label)
    {
        Lines.Add(FString(bMet ? TEXT("已达 · ") : TEXT("未达 · "))+Label);
    };
    if (!bMaxed)
    {
        const bool bChangingMastery=Definition.Kind==EFujiSkillKind::Mastery && !Progression->GetSelectedMastery().IsNone();
        AddCondition(Progression->GetAvailablePoints()+(bChangingMastery ? 4 : 0)>=Definition.PointCost,
            FString::Printf(TEXT("修习消耗 %d 点 · 剩余 %d 点%s"),Definition.PointCost,Progression->GetAvailablePoints(),bChangingMastery ? TEXT("（改修抵回原4点）") : TEXT("")));
        if (Definition.RequiredInvestment>0)
            AddCondition(Progression->GetSchoolInvestment(Definition.School)>=Definition.RequiredInvestment,
                FString::Printf(TEXT("本系投入 %d / %d（精通费用不计入）"),Progression->GetSchoolInvestment(Definition.School),Definition.RequiredInvestment));
        if (!Definition.PrerequisiteAny.IsEmpty())
        {
            TArray<FString> Names;
            bool bMet=false;
            for (FName Id : Definition.PrerequisiteAny)
            {
                FFujiSkillDefinition Prerequisite;
                if (Progression->GetSkillDefinition(Id,Prerequisite)) Names.Add(Prerequisite.DisplayName.ToString());
                bMet|=Progression->GetLearnedRank(Id)>0;
            }
            AddCondition(bMet,FString(TEXT("前置："))+FString::Join(Names,TEXT(" 或 "))+TEXT("（学会即可）"));
        }
        for (EFujiSkillSchool School : {EFujiSkillSchool::Fire,EFujiSkillSchool::Water,EFujiSkillSchool::Wood})
        {
            const int32 Need=Definition.RequiredInvestments.FindRef(School);
            if (Need<=0) continue;
            const TCHAR* Name=School==EFujiSkillSchool::Fire ? TEXT("火") : (School==EFujiSkillSchool::Water ? TEXT("水") : TEXT("木"));
            AddCondition(Progression->GetSchoolInvestment(School)>=Need,FString::Printf(TEXT("%s系投入 %d / %d"),Name,Progression->GetSchoolInvestment(School),Need));
        }
        if (Definition.Kind==EFujiSkillKind::Mastery) AddCondition(Progression->IsMasteryUnlocked(),TEXT("完成定道试炼"));
        if (Definition.bRequiresDiscovery) AddCondition(Progression->IsHiddenSkillDiscovered(SelectedSkillId),TEXT("发现对应禁印"));
        if (Definition.bRequiresMastery) AddCondition(!Progression->GetSelectedMastery().IsNone(),TEXT("已选择一种精通"));
        if (!Progression->bBuildChangesAllowed) Lines.Add(TEXT("当前不能调整构筑，请在安全地点操作。"));
    }
    else if (Definition.Kind==EFujiSkillKind::Passive) Lines.Add(FString::Printf(TEXT("已修至 %d / %d 级，不占主动符位。"),View.Rank,Definition.MaxRank));
    else if (Definition.Kind==EFujiSkillKind::Mastery) Lines.Add(TEXT("精通费用已计入总花费；仍可混搭其它两系。"));
    else Lines.Add(TEXT("无需再次消耗修习点。选择下方符位后即可装配。"));
    DetailRequirements->SetText(FText::FromString(FString::Join(Lines,TEXT("\n"))));
    LearnButton->SetIsEnabled(View.bCanLearn);
    FString LearnText=bMaxed ? TEXT("已掌握") : (View.Rank>0 ? TEXT("精进一级") : TEXT("修习此符"));
    if (Definition.Kind==EFujiSkillKind::Passive && bMaxed) LearnText=TEXT("已达最高等级");
    if (Definition.Kind==EFujiSkillKind::Mastery && !bMaxed) LearnText=Progression->GetSelectedMastery().IsNone() ? TEXT("选择此精通") : TEXT("改修此精通（抵回原费用）");
    LearnButton->Caption->SetText(FText::FromString(LearnText));
    LearnButton->SetToolTipText(View.bCanLearn ? FText::FromString(TEXT("确认时再次检查条件，成功后扣除修习点。")) : View.BlockReason);
    StyleButton(LearnButton,FujiUI::Cinnabar,false,View.bCanLearn);
    const bool bActive=Definition.Kind==EFujiSkillKind::Active || Definition.Kind==EFujiSkillKind::Hidden;
    EquipButton->SetVisibility(bActive ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
    UnequipButton->SetVisibility(bActive && View.bIsEquipped ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
    const auto Slots=Progression->GetEquippedSlots();
    const bool bAlreadyInTarget=Slots.IsValidIndex(SelectedSlotIndex) && Slots[SelectedSlotIndex]==SelectedSkillId;
    EquipButton->SetIsEnabled(View.Rank>0 && !bAlreadyInTarget && Progression->bBuildChangesAllowed);
    EquipButton->Caption->SetText(FText::FromString(bAlreadyInTarget ? TEXT("已在所选符位") : FString::Printf(TEXT("装备至符位 %d"),SelectedSlotIndex+1)));
    UnequipButton->SetIsEnabled(Progression->bBuildChangesAllowed);
}

void UFujiSkillTreeWidget::SelectSkill(FName SkillId)
{
    FFujiSkillDefinition Definition;
    if (!Progression || !Progression->GetSkillDefinition(SkillId,Definition)) return;
    SelectedSkillId=SkillId;
    const bool bHidden=Definition.Kind==EFujiSkillKind::Hidden;
    if (bForbiddenPage!=bHidden) { bForbiddenPage=bHidden; BuildColumns(); }
    if (Feedback) Feedback->SetText(FText::GetEmpty());
    RefreshSkillTree();
}

void UFujiSkillTreeWidget::LearnSelectedSkill()
{
    if (!Progression) return;
    FText Reason;
    const bool bSuccess=Progression->TryLearn(SelectedSkillId,Reason);
    RefreshSkillTree();
    SetFeedback(bSuccess ? FText::FromString(TEXT("修习完成，构筑已更新。")) : Reason,bSuccess);
}

void UFujiSkillTreeWidget::EquipSelectedSkill()
{
    if (!Progression) return;
    FText Reason;
    const bool bSuccess=Progression->TryEquip(SelectedSkillId,SelectedSlotIndex,Reason);
    RefreshSkillTree();
    SetFeedback(bSuccess ? FText::FromString(TEXT("已装配到所选符位。")) : Reason,bSuccess);
}

void UFujiSkillTreeWidget::HandleButton(UFujiSkillActionButton* Button)
{
    if (!Button) return;
    if (Button->Action==TEXT("Close")) { CloseSkillMenu(); return; }
    if (!Progression) return;
    if (Button->Action!=TEXT("Reset"))
    {
        bResetPending=false;
        ResetButton->Caption->SetText(FText::FromString(TEXT("重置修习点")));
        CancelResetButton->SetVisibility(ESlateVisibility::Collapsed);
        ResetHint->SetText(FText::GetEmpty());
    }
    if (Button->Action==TEXT("Reset"))
    {
        if (!bResetPending)
        {
            bResetPending=true;
            ResetButton->Caption->SetText(FText::FromString(TEXT("确认重置")));
            CancelResetButton->SetVisibility(ESlateVisibility::Visible);
            ResetHint->SetText(FText::FromString(TEXT("返还已花费点数，清空符位与精通。\n保留基础技能、已发现禁印及定道资格。")));
        }
        else
        {
            FText Reason;
            const bool bSuccess=Progression->TryResetBuild(Reason);
            bResetPending=false;
            ResetButton->Caption->SetText(FText::FromString(TEXT("重置修习点")));
            CancelResetButton->SetVisibility(ESlateVisibility::Collapsed);
            ResetHint->SetText(bSuccess ? FText::FromString(TEXT("修习点已返还，可重新构筑。")) : Reason);
            RefreshSkillTree();
        }
        return;
    }
    if (Button->Action==TEXT("Select")) SelectSkill(Button->SkillId);
    else if (Button->Action==TEXT("Learn")) LearnSelectedSkill();
    else if (Button->Action==TEXT("Equip")) EquipSelectedSkill();
    else if (Button->Action==TEXT("Slot"))
    {
        SelectedSlotIndex=Button->SlotIndex;
        RefreshSkillTree();
        SetFeedback(FText::FromString(FString::Printf(TEXT("已选择符位 %d，点击右侧装配按钮确认。"),SelectedSlotIndex+1)),true);
    }
    else if (Button->Action==TEXT("Unequip"))
    {
        const auto View=Progression->GetNodeView(SelectedSkillId);
        FText Reason;
        const bool bSuccess=Progression->TryUnequip(View.EquippedSlot,Reason);
        RefreshSkillTree();
        SetFeedback(bSuccess ? FText::FromString(TEXT("此符已卸下，修习记录保留。")) : Reason,bSuccess);
    }
    else if (Button->Action==TEXT("Ordinary") || Button->Action==TEXT("Forbidden"))
    {
        SelectSkill(Button->Action==TEXT("Forbidden") ? FName(TEXT("H1")) : FName(TEXT("F1")));
    }
}
