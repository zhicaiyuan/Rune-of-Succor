Turn + Run Pivot — setup_turn_runpivot.py

DONE BY SCRIPT
  - SwordRTG: Turn_90/180 + Run_Fast_Turn (retargeted)
  - AnimBP turn vars: bWantsTurn90/180, bTurnLeft, MoveYawDelta...
  - Turn state SequencePlayers -> *_RTG assets

YOU WIRE IN EDITOR (Locomotion SM)
  Draw transitions if missing, then set rules:

  Walk/Run -> Turn180L
    bWantsTurn180 AND bTurnLeft AND GroundSpeed < 40

  Walk/Run -> Turn180R
    bWantsTurn180 AND NOT bTurnLeft AND GroundSpeed < 40

  Walk/Run -> Turn90L / Turn90R
    bWantsTurn90 AND left/right AND GroundSpeed < 40

  Walk/Run -> RunTurnL
    bWantsTurn180 AND bTurnLeft AND GroundSpeed >= 40
    Priority HIGHER than Turn180 (lower number)

  Walk/Run -> RunTurnR
    bWantsTurn180 AND NOT bTurnLeft AND GroundSpeed >= 40

  Turn* / RunTurn* -> Walk/Run
    Automatic Rule (sequence finished)
    Do NOT exit on NOT bWantsTurn*

CHARACTER (optional, if script wired TO_* nodes)
  During turn: OrientRotationToMovement OFF
  Turn ended: SetActorRotation to input yaw, Orient ON

TEST
  1) Stand still A->D : Turn180
  2) Run A->D : RunTurn (not Turn180)
  3) If facing off 90 after turn: tweak end snap or mesh -90 offset
