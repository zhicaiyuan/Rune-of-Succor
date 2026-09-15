Turn variables — Actor facing vs move input

FORMULA
  InputYaw  = direction of WASD move input (world XY)
  ActorYaw  = character actor rotation yaw
  MoveYawDelta = NormalizeAxis(InputYaw - ActorYaw)
  AbsMoveYawDelta = |MoveYawDelta|

  bWantsTurn180 = hasInput AND Abs >= TurnAngle180   (default 135)
  bWantsTurn90  = hasInput AND Abs >= TurnAngle90 AND Abs < TurnAngle180  (60..135)
  bTurnLeft     = hasInput AND MoveYawDelta < 0

WHY BETTER
  Old: previous input vs current input (1-frame pulse, easy to miss)
  New: body facing vs wanted move dir — stays true until character turns enough

SM (you wire)
  Walk/Run -> Turn180L : bWantsTurn180 AND bTurnLeft
  Walk/Run -> Turn180R : bWantsTurn180 AND NOT bTurnLeft
  Walk/Run -> Turn90L  : bWantsTurn90 AND bTurnLeft
  Walk/Run -> Turn90R  : bWantsTurn90 AND NOT bTurnLeft
  Turn* -> Walk/Run    : Automatic Rule (sequence end)

DEBUG (optional watch in PIE)
  ActorYaw, InputYaw, MoveYawDelta, AbsMoveYawDelta, bWantsTurn180

Tune: TurnAngle90 / TurnAngle180 on AnimBP defaults.
