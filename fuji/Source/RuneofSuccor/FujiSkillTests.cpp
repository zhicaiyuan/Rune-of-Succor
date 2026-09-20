#include "FujiSkillSubsystem.h"
#include "FujiSkillTreeWidget.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
#include "Misc/AutomationTest.h"
#include "UObject/StrongObjectPtr.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Widgets/SWidget.h"
#include "Slate/WidgetRenderer.h"
#include "Engine/TextureRenderTarget2D.h"
#include "ImageUtils.h"
#include "Serialization/BufferArchive.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "RenderingThread.h"
#include "AssetCompilingManager.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Image.h"
#include "Engine/Texture2D.h"

namespace FujiSkillTests
{
    void CaptureWidget(UFujiSkillTreeWidget* Widget, const TCHAR* StateName)
    {
        if (!FParse::Param(FCommandLine::Get(),TEXT("FujiSkillScreenshots"))) return;
        const FString Directory=FPaths::ProjectSavedDir()/TEXT("SkillUIIntegration");
        IFileManager::Get().MakeDirectory(*Directory,true);
        // 保持离屏目标为线性颜色，由PNG导出统一执行一次sRGB转换。
        FWidgetRenderer Renderer(false,true);
        FAssetCompilingManager::Get().FinishAllCompilation();
        auto SlateWidget=Widget->TakeWidget();
        SlateWidget->SlatePrepass(1.f);
        UTextureRenderTarget2D* Target=Renderer.DrawWidget(SlateWidget,FVector2D(1920,1080));
        FlushRenderingCommands();
        FImage Capture;
        if (Target && FImageUtils::GetRenderTargetImage(Target,Capture))
        {
            FImageUtils::SaveImageByExtension(*(Directory/FString::Printf(TEXT("skill-ui-%s.png"),StateName)),Capture);
        }
    }

    TStrongObjectPtr<UFujiSkillSubsystem> NewState(int32 Points=24)
    {
        UGameInstance* Owner=NewObject<UGameInstance>(GEngine);
        TStrongObjectPtr<UFujiSkillSubsystem> State(NewObject<UFujiSkillSubsystem>(Owner));
        State->bAutoSave=false;
        FText Reason;
        if (Points>0) State->GrantPoints(Points,Reason);
        return State;
    }

    bool InvestTen(UFujiSkillSubsystem* State, const TCHAR* Prefix)
    {
        FText Reason;
        const FString P(Prefix);
        bool Result=true;
        for (const TCHAR* Suffix : {TEXT("2"),TEXT("3"),TEXT("P1"),TEXT("P1"),TEXT("P2"),TEXT("P2"),TEXT("P3"),TEXT("P3")})
            Result=State->TryLearn(FName(P+Suffix),Reason) && Result;
        return Result;
    }
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FFujiSkillLearningTest,"Fuji.Skills.LearningAndLoadout",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FFujiSkillLearningTest::RunTest(const FString& Parameters)
{
    auto State=FujiSkillTests::NewState();
    FText Reason;
    TestEqual(TEXT("完整36节点目录"),State->GetAllSkills().Num(),36);
    TestEqual(TEXT("三道基础符免费"),State->GetLearnedRank(TEXT("F1"))+State->GetLearnedRank(TEXT("W1"))+State->GetLearnedRank(TEXT("M1")),3);
    TestFalse(TEXT("不能跳过炎龙前置"),State->TryLearn(TEXT("F5"),Reason));
    TestEqual(TEXT("失败不扣点"),State->GetAvailablePoints(),24);
    TestTrue(TEXT("学习赤锋"),State->TryLearn(TEXT("F2"),Reason));
    TestTrue(TEXT("学习焚地"),State->TryLearn(TEXT("F3"),Reason));
    TestFalse(TEXT("购买本技能的费用不能凑前置投入"),State->TryLearn(TEXT("F5"),Reason));
    TestEqual(TEXT("失败仍保留20点"),State->GetAvailablePoints(),20);
    TestTrue(TEXT("余烬一级"),State->TryLearn(TEXT("FP1"),Reason));
    TestTrue(TEXT("余烬二级"),State->TryLearn(TEXT("FP1"),Reason));
    TestFalse(TEXT("被动不能超过二级"),State->TryLearn(TEXT("FP1"),Reason));
    TestTrue(TEXT("满足6投入且前置不必装备"),State->TryLearn(TEXT("F5"),Reason));
    TestEqual(TEXT("学习炎龙只扣3点"),State->GetAvailablePoints(),15);
    TestFalse(TEXT("重复点击主动不能二次学习"),State->TryLearn(TEXT("F5"),Reason));
    TestEqual(TEXT("重复点击不扣点"),State->GetAvailablePoints(),15);
    TestTrue(TEXT("焦锋使投入到10"),State->TryLearn(TEXT("FP2"),Reason));
    TestTrue(TEXT("天陨前置OR，仅炎龙即可"),State->TryLearn(TEXT("F6"),Reason));
    TestTrue(TEXT("装备炎龙"),State->TryEquip(TEXT("F5"),0,Reason));
    TestTrue(TEXT("移动炎龙符位"),State->TryEquip(TEXT("F5"),2,Reason));
    TestTrue(TEXT("原符位清空无重复"),State->GetEquippedSlots()[0].IsNone());
    TestFalse(TEXT("被动不占主动符位"),State->TryEquip(TEXT("FP1"),1,Reason));
    TestFalse(TEXT("拒绝越界符位"),State->TryEquip(TEXT("F1"),5,Reason));
    State->SetBuildChangesAllowed(false);
    TestFalse(TEXT("构筑锁同时阻止学习"),State->TryLearn(TEXT("W2"),Reason));
    TestFalse(TEXT("构筑锁同时阻止装配"),State->TryEquip(TEXT("W1"),4,Reason));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FFujiSkillForbiddenTest,"Fuji.Skills.ForbiddenAndMastery",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FFujiSkillForbiddenTest::RunTest(const FString& Parameters)
{
    auto State=FujiSkillTests::NewState();
    FText Reason;
    for (const TCHAR* Id : {TEXT("F2"),TEXT("F3"),TEXT("W2"),TEXT("W3"),TEXT("M2"),TEXT("M3")})
        TestTrue(TEXT("混搭初阶学习"),State->TryLearn(Id,Reason));
    TestFalse(TEXT("0费用不代表自动发现禁术"),State->TryLearn(TEXT("H1"),Reason));
    TestTrue(TEXT("发现蒸天劫"),State->DiscoverSkill(TEXT("H1"),Reason));
    TestTrue(TEXT("发现烬木葬"),State->DiscoverSkill(TEXT("H2"),Reason));
    TestTrue(TEXT("满足火水投入可学蒸天劫"),State->TryLearn(TEXT("H1"),Reason));
    TestTrue(TEXT("满足火木投入可学烬木葬"),State->TryLearn(TEXT("H2"),Reason));
    TestEqual(TEXT("禁术学习不额外扣修习点"),State->GetAvailablePoints(),12);
    TestTrue(TEXT("装备一道禁术"),State->TryEquip(TEXT("H1"),0,Reason));
    TestFalse(TEXT("拒绝装备第二道禁术"),State->TryEquip(TEXT("H2"),1,Reason));
    TestTrue(TEXT("允许替换已有禁术"),State->TryEquip(TEXT("H2"),0,Reason));
    TestTrue(TEXT("发现太初寂灭"),State->DiscoverSkill(TEXT("H6"),Reason));
    TestFalse(TEXT("太初即使三系投入足够仍须精通"),State->TryLearn(TEXT("H6"),Reason));

    auto Mastery=FujiSkillTests::NewState();
    TestTrue(TEXT("火投入10"),FujiSkillTests::InvestTen(Mastery.Get(),TEXT("F")));
    TestTrue(TEXT("水投入10"),FujiSkillTests::InvestTen(Mastery.Get(),TEXT("W")));
    TestFalse(TEXT("精通需定道试炼"),Mastery->TryLearn(TEXT("FM"),Reason));
    TestTrue(TEXT("剧情开放定道"),Mastery->SetMasteryUnlocked(true,Reason));
    TestTrue(TEXT("选择燎原"),Mastery->TryLearn(TEXT("FM"),Reason));
    TestEqual(TEXT("选精通后用尽24点"),Mastery->GetAvailablePoints(),0);
    TestEqual(TEXT("精通4点不计入火投入"),Mastery->GetSchoolInvestment(EFujiSkillSchool::Fire),10);
    TestTrue(TEXT("0余额可用原费用抵回改修"),Mastery->TryLearn(TEXT("WM"),Reason));
    TestEqual(TEXT("改修不重复扣费"),Mastery->GetAvailablePoints(),0);
    TestEqual(TEXT("旧精通不再生效"),Mastery->GetLearnedRank(TEXT("FM")),0);
    TestEqual(TEXT("仅一个当前精通"),Mastery->GetSelectedMastery(),FName(TEXT("WM")));
    TestTrue(TEXT("改修后构筑可达且可保存"),Mastery->ValidateSaveData(Mastery->GetSaveData(),Reason));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FFujiSkillSaveTest,"Fuji.Skills.SaveValidation",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FFujiSkillSaveTest::RunTest(const FString& Parameters)
{
    auto State=FujiSkillTests::NewState();
    FText Reason;
    TestTrue(TEXT("学习用于存档的节点"),State->TryLearn(TEXT("F2"),Reason));
    const FFujiSkillSaveData Valid=State->GetSaveData();
    auto Copy=FujiSkillTests::NewState(0);
    TestTrue(TEXT("有效数据可导入"),Copy->TryImportSaveData(Valid,Reason));
    TestEqual(TEXT("导入保持余额"),Copy->GetAvailablePoints(),22);
    FFujiSkillSaveData Bad=Valid;
    Bad.LearnedRanks.Add(TEXT("F5"),1);
    Bad.LearnedRanks.Add(TEXT("FP2"),1);
    TestFalse(TEXT("拒绝高阶节点互相凑门槛的不可达存档"),Copy->TryImportSaveData(Bad,Reason));
    TestEqual(TEXT("坏档不覆盖当前状态"),Copy->GetAvailablePoints(),22);
    Bad=Valid; Bad.LearnedRanks.Add(TEXT("Unknown"),1);
    TestFalse(TEXT("拒绝未知ID"),Copy->ValidateSaveData(Bad,Reason));
    Bad=Valid; Bad.EquippedSlots[0]=TEXT("F2"); Bad.EquippedSlots[1]=TEXT("F2");
    TestFalse(TEXT("拒绝重复符位"),Copy->ValidateSaveData(Bad,Reason));
    Bad=Valid; Bad.SaveVersion=999;
    TestFalse(TEXT("拒绝未来版本"),Copy->ValidateSaveData(Bad,Reason));
    Bad=Valid; Bad.GrantedPoints=1;
    TestFalse(TEXT("拒绝超预算"),Copy->ValidateSaveData(Bad,Reason));

    // 独立随机测试槽，不读取或覆盖玩家的正式存档。
    const FString TestSlot=TEXT("FujiSkillTest_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    State->SaveSlotName=TestSlot; Copy->SaveSlotName=TestSlot;
    TestFalse(TEXT("随机测试槽必须不存在"),UGameplayStatics::DoesSaveGameExist(TestSlot,0));
    TestTrue(TEXT("写入真实SaveGame文件"),State->SaveToSlot(Reason));
    TestTrue(TEXT("读取真实SaveGame文件"),Copy->LoadFromSlot(Reason));
    TestEqual(TEXT("读档恢复技能等级"),Copy->GetLearnedRank(TEXT("F2")),1);
    TStrongObjectPtr<UFujiSkillSaveGame> Corrupt(NewObject<UFujiSkillSaveGame>());
    Corrupt->Data=Valid; Corrupt->Data.SaveVersion=999;
    TestTrue(TEXT("仅在测试槽构造不兼容档"),UGameplayStatics::SaveGameToSlot(Corrupt.Get(),TestSlot,0));
    TestFalse(TEXT("实际读档拒绝不兼容版本"),Copy->LoadFromSlot(Reason));
    TestTrue(TEXT("坏档后阻止覆盖"),Copy->bSaveWriteBlocked);
    TestFalse(TEXT("手动保存也不覆盖坏档"),Copy->SaveToSlot(Reason));
    TestEqual(TEXT("读档失败保留内存构筑"),Copy->GetAvailablePoints(),22);
    TestTrue(TEXT("清理本测试创建的随机槽"),UGameplayStatics::DeleteGameInSlot(TestSlot,0));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FFujiSkillWidgetTest,"Fuji.Skills.ActualWidgetInteraction",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FFujiSkillWidgetTest::RunTest(const FString& Parameters)
{
    auto* Defaults=GetMutableDefault<UFujiSkillSubsystem>();
    const FString OriginalSlot=Defaults->SaveSlotName;
    const bool OriginalAutoSave=Defaults->bAutoSave;
    Defaults->SaveSlotName=TEXT("FujiWidgetTest_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    Defaults->bAutoSave=false;
    TStrongObjectPtr<UGameInstance> GI(NewObject<UGameInstance>(GEngine));
    GI->InitializeStandalone();
    Defaults->SaveSlotName=OriginalSlot;
    Defaults->bAutoSave=OriginalAutoSave;
    auto* State=GI->GetSubsystem<UFujiSkillSubsystem>();
    State->bAutoSave=false;
    // 重置仅作用于本测试的临时GameInstance。
    auto Fixture=FujiSkillTests::NewState();
    FText Reason;
    State->TryImportSaveData(Fixture->GetSaveData(),Reason);
    UClass* WidgetClass=LoadClass<UFujiSkillTreeWidget>(nullptr,TEXT("/Game/UI/技能界面/WBP_技能界面.WBP_技能界面_C"));
    UFujiSkillTreeWidget* Widget=WidgetClass ? CreateWidget<UFujiSkillTreeWidget>(GI.Get(),WidgetClass) : nullptr;
    if (TestNotNull(TEXT("实际技能蓝图继承原生界面"),Widget))
    {
        TSharedPtr<SWidget> SlateWidget=Widget->TakeWidget();
        TestEqual(TEXT("六张实际图集已绑定"),Widget->IconAtlases.Num(),6);
        auto* Locked=Cast<UFujiSkillActionButton>(Widget->GetSkillButton(TEXT("F5")));
        if (TestNotNull(TEXT("炎龙节点存在"),Locked))
        {
            TestTrue(TEXT("未解锁节点仍可点击"),Locked->GetIsEnabled());
            Locked->Invoke();
            TestEqual(TEXT("锁定点击打开正确详情"),Widget->SelectedSkillId,FName(TEXT("F5")));
            TestFalse(TEXT("只有修习按钮禁用"),Widget->GetLearnButton()->GetIsEnabled());
            TestTrue(TEXT("详情明确显示前置技能名称"),Widget->GetDisplayedRequirements().ToString().Contains(TEXT("赤锋")));
            FujiSkillTests::CaptureWidget(Widget,TEXT("locked"));
            for (const TCHAR* Id : {TEXT("F2"),TEXT("F3"),TEXT("FP1"),TEXT("FP1")}) State->TryLearn(Id,Reason);
            TestTrue(TEXT("事件驱动刷新解锁，无需重开页面"),Widget->GetLearnButton()->GetIsEnabled());
            FujiSkillTests::CaptureWidget(Widget,TEXT("learnable"));
            CastChecked<UFujiSkillActionButton>(Widget->GetLearnButton())->Invoke();
            TestEqual(TEXT("真实按钮回调学习"),State->GetLearnedRank(TEXT("F5")),1);
            TestEqual(TEXT("真实按钮回调扣费正确"),State->GetAvailablePoints(),15);
            CastChecked<UFujiSkillActionButton>(Widget->GetLearnButton())->Invoke();
            TestEqual(TEXT("禁用后的重复点击不扣点"),State->GetAvailablePoints(),15);
            Widget->SelectedSlotIndex=3;
            Widget->EquipSelectedSkill();
            TestEqual(TEXT("装备动作关联成长状态"),State->GetEquippedSlots()[3],FName(TEXT("F5")));
            UFujiSkillActionButton* Reset=nullptr;
            UFujiSkillActionButton* Cancel=nullptr;
            UFujiSkillActionButton* EquippedSlot=nullptr;
            UFujiGlyphPreview* Glyph=nullptr;
            Widget->WidgetTree->ForEachWidget([&](UWidget* Child)
            {
                if (auto* Button=Cast<UFujiSkillActionButton>(Child))
                {
                    if (Button->Action==TEXT("Reset")) Reset=Button;
                    if (Button->Action==TEXT("CancelReset")) Cancel=Button;
                    if (Button->Action==TEXT("Slot") && Button->SlotIndex==3) EquippedSlot=Button;
                }
                if (auto* Preview=Cast<UFujiGlyphPreview>(Child)) Glyph=Preview;
            });
            if (TestNotNull(TEXT("装备符位存在"),EquippedSlot))
            {
                TestEqual(TEXT("符位关联装备技能"),EquippedSlot->SkillId,FName(TEXT("F5")));
                TestNotNull(TEXT("符位显示实际技能图集"),EquippedSlot->Icon->GetBrush().GetResourceObject());
            }
            TestNotNull(TEXT("印头图集已绑定"),Widget->SealAtlas.Get());
            if (TestNotNull(TEXT("符形预览存在"),Glyph)) TestEqual(TEXT("详情只画符身闪电"),Glyph->Shape,FString(TEXT("闪电")));
            FujiSkillTests::CaptureWidget(Widget,TEXT("equipped"));
            // 检查所有印头的映射，防止圆替换后又被门形替换覆盖。
            for (const TCHAR* Prefix : {TEXT("F"),TEXT("W"),TEXT("M"),TEXT("H")})
            {
                const TCHAR* Expected[]={TEXT("一"),TEXT("竖线"),TEXT("×"),TEXT("○"),TEXT("闪电"),TEXT("螺旋")};
                for (int32 Index=0; Index<6; ++Index)
                {
                    Widget->SelectSkill(FName(FString::Printf(TEXT("%s%d"),Prefix,Index+1)));
                    if (Glyph) TestEqual(TEXT("四系符形与新概念一致"),Glyph->Shape,FString(Expected[Index]));
                }
            }
            Widget->SelectSkill(TEXT("F2"));
            FujiSkillTests::CaptureWidget(Widget,TEXT("vertical"));
            Widget->SelectSkill(TEXT("F4"));
            FujiSkillTests::CaptureWidget(Widget,TEXT("circle"));
            Widget->SelectSkill(TEXT("H1"));
            TestNotNull(TEXT("禁术页动态节点存在"),Widget->GetSkillButton(TEXT("H1")));
            TestFalse(TEXT("未发现禁术仍不可学习"),Widget->GetLearnButton()->GetIsEnabled());
            FujiSkillTests::CaptureWidget(Widget,TEXT("hidden"));
            State->DiscoverSkill(TEXT("H1"),Reason);
            State->SetMasteryUnlocked(true,Reason);
            if (TestNotNull(TEXT("重置按钮存在"),Reset) && TestNotNull(TEXT("取消按钮存在"),Cancel))
            {
                Reset->Invoke();
                TestEqual(TEXT("首次点击不扣改数据"),State->GetAvailablePoints(),15);
                Cancel->Invoke();
                TestEqual(TEXT("取消保留装备"),State->GetEquippedSlots()[3],FName(TEXT("F5")));
                Reset->Invoke(); Reset->Invoke();
                TestEqual(TEXT("确认返还全部已花费点数"),State->GetAvailablePoints(),24);
                TestEqual(TEXT("清除已修技能"),State->GetLearnedRank(TEXT("F5")),0);
                TestEqual(TEXT("保留基础技能"),State->GetLearnedRank(TEXT("F1")),1);
                TestTrue(TEXT("保留剧情发现"),State->IsHiddenSkillDiscovered(TEXT("H1")));
                TestTrue(TEXT("保留定道资格"),State->IsMasteryUnlocked());
                TestTrue(TEXT("装备槽清空"),State->GetEquippedSlots()[3].IsNone());
                if (EquippedSlot) TestNull(TEXT("重置移除旧图标"),EquippedSlot->Icon->GetBrush().GetResourceObject());
                State->SetBuildChangesAllowed(false);
                TestFalse(TEXT("禁止调整构筑时重置按钮禁用"),Reset->GetIsEnabled());
            }
        }
        Widget->RemoveFromParent();
        SlateWidget.Reset();
        Widget->ReleaseSlateResources(true);
    }
    UWorld* World=GI->GetWorld();
    GI->Shutdown();
    GEngine->DestroyWorldContext(World);
    World->DestroyWorld(false);
    return true;
}
#endif
