ABP turn variables (WASD direction change — NOT mouse)

VARIABLES (use these in SM)
---------------------------
bWantsTurn90      bool   Abs angle in [TurnAngle90, TurnAngle180)
bWantsTurn180     bool   Abs angle >= TurnAngle180
bTurnLeft         bool   True = turn left (MoveYawDelta < 0). Swap L/R if mirrored.
MoveYawDelta      float  Signed degrees (-180..180) from previous move dir to current
AbsMoveYawDelta   float  Absolute MoveYawDelta
TurnAngle90       float  Default 60
TurnAngle180      float  Default 135

INTERNAL (usually ignore in SM)
-------------------------------
PrevMoveYaw       float  Last move-input yaw
bHasPrevMoveDir   bool   Had move input last frame
PrevMoveDir       vector UNUSED (broken type) — ignore

STATE MACHINE
-------------
Loop -> Turn180L : bWantsTurn180 AND bTurnLeft
Loop -> Turn180R : bWantsTurn180 AND NOT bTurnLeft
Loop -> Turn90L  : bWantsTurn90 AND bTurnLeft
Loop -> Turn90R  : bWantsTurn90 AND NOT bTurnLeft
Turn* -> Loop    : Automatic Rule (sequence end)
Turn* -> Stop    : bStopInput (optional)

Examples: A then D ~180; A then S ~90. Mouse look does not affect these.
