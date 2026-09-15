# -*- coding: utf-8 -*-
import os, re

root = r"E:\游戏\符济\Rune-of-Succor\符济"
char = os.path.join(root, r"Content\ThirdPerson\Blueprints\BP_ThirdPersonCharacter.uasset")
d = open(char, "rb").read()
print("=== Character paths ===")
for p in sorted(set(re.findall(rb"/Game/[A-Za-z0-9_/\.]+", d))):
    print(p.decode())
print("ABP_Strafe", b"ABP_StrafeLocomotion" in d)
print("ABP_Unarmed", b"ABP_Unarmed" in d)

gm = os.path.join(root, r"Content\ThirdPerson\Blueprints\BP_ThirdPersonGameMode.uasset")
g = open(gm, "rb").read()
print("\n=== GameMode paths ===")
for p in sorted(set(re.findall(rb"/Game/[A-Za-z0-9_/\.]+", g))):
    print(p.decode())

ext = os.path.join(root, r"Content\__ExternalActors__\ThirdPerson\Lvl_ThirdPerson")
for dp, _, fns in os.walk(ext):
    for fn in fns:
        if not fn.endswith(".uasset"):
            continue
        p = os.path.join(dp, fn)
        data = open(p, "rb").read()
        if b"PlayerStart" in data:
            print("\nPlayerStart:", p)

log = os.path.join(root, r"Saved\Logs\符济.log")
if os.path.isfile(log):
    text = open(log, "rb").read().decode("utf-8", "ignore")
    keys = ("PIE", "spawn", "Pawn", "AnimBlueprint", "ABP_Strafe", "Error", "Ensure", "failed", "Possess", "GameMode")
    print("\n=== Log hits (last 80 matching) ===")
    hits = []
    for line in text.splitlines():
        if any(k.lower() in line.lower() for k in keys):
            if "AutomationTest" in line:
                continue
            hits.append(line)
    for line in hits[-80:]:
        print(line)
