Scriptname SeranaAI_CoreScript extends Quest  

; --- CORE ACTOR ALIASES ---
Actor Property DLC1SeranaRef Auto

ReferenceAlias Property SeranaAlias Auto
ReferenceAlias Property TargetAlias Auto 
Float Property PollInterval = 1.0 Auto 

GlobalVariable Property GameHour Auto
GlobalVariable Property SeranaAffinityScore Auto
GlobalVariable Property SeranaAudioPointer Auto

; --- DAWNGUARD MENTAL MODEL INTEGRATION ---
DLC1_NPCMentalModelScript Property DLC1MentalModel Auto
; ------------------------------------------

; --- ENVIRONMENT INTERACTION STATES ---
ReferenceAlias Property InteractAlias Auto
GlobalVariable Property SeranaWaitState Auto 
; -------------------------------------------------------------

; --- DUAL-ENGINE PATHFINDING STATES ---
ReferenceAlias Property SeranaDestAlias Auto      ; Physical Object/Marker Target
LocationAlias Property SeranaDestLocAlias Auto    ; Location/City Target
GlobalVariable Property SeranaGoToState Auto      ; 0=Off, 1=Physical, 2=Location
Float gotoTimeout = 0.0
; --------------------------------------------------------

Topic Property mainTopic Auto 

float lastHour = -1.0
int lastAffinity = -999
Int lastTimeState = 0 
Int lastWeatherState = 0 
Int lastAffinityTier = 0 
Bool wasInCombat = False
Float idleTimer = 0.0
Location lastLocation = None
Bool lastInteriorState = False 

Int affinityState = 0 
Float affinityTimeout = 0.0
Float interactTimeout = 0.0 ; Interaction failsafe timer

Event OnInit()
    SetObjectiveDisplayed(10, True) 
    RegisterForSingleUpdate(PollInterval)
EndEvent

Event OnUpdate()
    If (SeranaAlias.GetReference() == None)
        SeranaAlias.ForceRefTo(DLC1SeranaRef)
        TargetAlias.Clear() 
    EndIf

    Actor SeranaRef = SeranaAlias.GetActorRef()
    
    If (SeranaRef == None)
        RegisterForSingleUpdate(PollInterval)
        Return
    EndIf

    float currentHour = GameHour.GetValue()
    int currentAffinity = SeranaAffinityScore.GetValueInt()

    If (lastAffinityTier == 0)
        lastAffinityTier = GetAffinityTier(currentAffinity)
    EndIf

    If (currentHour != lastHour || currentAffinity != lastAffinity)
        JsonUtil.SetFloatValue("SeranaContext.json", "GameHour", currentHour)
        JsonUtil.SetIntValue("SeranaContext.json", "AffinityScore", currentAffinity)
        JsonUtil.Save("SeranaContext.json")
        lastHour = currentHour
        lastAffinity = currentAffinity
    EndIf

    Int currentPointer = SeranaAudioPointer.GetValueInt()
    If (currentPointer == 8 || currentPointer == 9)
        affinityTimeout += PollInterval
        
        If (SeranaRef.IsInDialogueWithPlayer())
            If (affinityState != 2)
                affinityState = 2
            EndIf
            affinityTimeout = 0.0 
            
        ElseIf (affinityState == 2 && !SeranaRef.IsInDialogueWithPlayer())
            ResetAffinityForceGreet(SeranaRef)
            
        ElseIf (affinityTimeout > 45.0) 
            ResetAffinityForceGreet(SeranaRef)
        EndIf
        
        RegisterForSingleUpdate(PollInterval)
        Return 
    EndIf

    ; =========================================================
    ; --- PATHFINDING AUTONOMY (DUAL-SCANNER) ---
    ; =========================================================
    Int goToMode = 0
    If (SeranaGoToState != None)
        goToMode = SeranaGoToState.GetValueInt()
    EndIf

    ; --- ENGINE 1: PHYSICAL REFERENCE / XMARKER TRACKING ---
    If (goToMode == 1)
        ObjectReference DestObj = SeranaDestAlias.GetReference()
        If (DestObj)
            If (gotoTimeout >= 1.0)
                Float dist = SeranaRef.GetDistance(DestObj)
                
                If (dist <= 180.0)
                    SeranaGoToState.SetValueInt(0)
                    
                    If (DLC1MentalModel)
                        DLC1MentalModel.Wait()
                    EndIf
                    
                    If (DestObj.GetBaseObject().GetFormID() == 0x0000003B)
                        DestObj.Delete()
                    EndIf
                    
                    gotoTimeout = -1.0 
                    SeranaDestAlias.Clear()
                    SeranaRef.EvaluatePackage()
                    
                ElseIf (gotoTimeout > 300.0) ; 5-Minute Failsafe Timeout
                    SeranaGoToState.SetValueInt(0)
                    
                    If (DestObj.GetBaseObject().GetFormID() == 0x0000003B)
                        DestObj.Delete()
                    EndIf
                    
                    gotoTimeout = 0.0
                    SeranaDestAlias.Clear()
                    SeranaRef.EvaluatePackage()
                EndIf
            ElseIf (gotoTimeout >= 0.0)
                gotoTimeout += PollInterval
            EndIf
        Else
            SeranaGoToState.SetValueInt(0)
            gotoTimeout = 0.0
        EndIf
        
    ; --- ENGINE 2: LOCATION TRACKING ---
    ElseIf (goToMode == 2)
        Location DestLoc = SeranaDestLocAlias.GetLocation()
        If (DestLoc)
            If (gotoTimeout >= 1.0)
                If (SeranaRef.IsInLocation(DestLoc))
                    SeranaGoToState.SetValueInt(0)
                    
                    If (DLC1MentalModel)
                        DLC1MentalModel.Wait()
                    EndIf
                    
                    gotoTimeout = -1.0 
                    SeranaDestLocAlias.Clear()
                    SeranaRef.EvaluatePackage()
                    
                ElseIf (gotoTimeout > 300.0) ; 5-Minute Failsafe Timeout
                    SeranaGoToState.SetValueInt(0)
                    gotoTimeout = 0.0
                    SeranaDestLocAlias.Clear()
                    SeranaRef.EvaluatePackage()
                EndIf
            ElseIf (gotoTimeout >= 0.0)
                gotoTimeout += PollInterval
            EndIf
        Else
            SeranaGoToState.SetValueInt(0)
            gotoTimeout = 0.0
        EndIf
    EndIf
    ; =========================================================

    ; =========================================================
    ; --- PHYSICAL INTERACTION (PROXIMITY SCANNER) ---
    ; =========================================================
    If (SeranaWaitState != None && SeranaWaitState.GetValueInt() == 2)
        ObjectReference TargetObj = InteractAlias.GetReference()
        If (TargetObj)
            If (interactTimeout >= 0.0)
                interactTimeout += PollInterval
                Float dist = SeranaRef.GetDistance(TargetObj)
                
                If (dist <= 160.0)
                    SeranaWaitState.SetValueInt(0)
                    If (DLC1MentalModel)
                        DLC1MentalModel.Wait()
                    EndIf
                    Utility.Wait(1.0)
                    TargetObj.Activate(SeranaRef)
                    interactTimeout = -1.0 
                    InteractAlias.Clear()
                    SeranaRef.EvaluatePackage()
                    
                ElseIf (interactTimeout > 30.0)
                    SeranaWaitState.SetValueInt(0)
                    interactTimeout = 0.0
                    InteractAlias.Clear()
                    SeranaRef.EvaluatePackage()
                EndIf
            EndIf
        Else
            SeranaWaitState.SetValueInt(0)
            interactTimeout = 0.0
        EndIf
    EndIf
    ; =========================================================

    If (TargetAlias.GetReference() != None)
        Actor CurrentTarget = TargetAlias.GetActorReference()
        If (CurrentTarget.IsDead())
            TargetAlias.Clear() 
            SeranaRef.SetGhost(False) 
            
            Utility.Wait(0.15)
            SeranaRef.EvaluatePackage() 
        Else
            Actor CurrentHavokTarget = SeranaRef.GetCombatTarget()
            If (CurrentHavokTarget != CurrentTarget && CurrentHavokTarget != None)
                CurrentHavokTarget.StopCombat() 
                SeranaRef.StartCombat(CurrentTarget)
            EndIf
        EndIf
    EndIf

    JsonUtil.Unload("SeranaCommand.json")
    String currentIntent = JsonUtil.GetStringValue("SeranaCommand.json", "intent")
    
    If currentIntent != ""
        String targetPlugin = JsonUtil.GetStringValue("SeranaCommand.json", "target_plugin")
        Int targetFormID = JsonUtil.GetIntValue("SeranaCommand.json", "target_formid")
        String currentSentiment = JsonUtil.GetStringValue("SeranaCommand.json", "sentiment")
        String targetName = JsonUtil.GetStringValue("SeranaCommand.json", "target_name")
        Int audioFormID = JsonUtil.GetIntValue("SeranaCommand.json", "audio_formid")
        Int sentimentShift = JsonUtil.GetIntValue("SeranaCommand.json", "sentiment_shift")
        
        DistributeLogic(currentIntent, targetPlugin, targetFormID, currentSentiment, targetName)
        
        If (audioFormID != 0)
            SeranaAudioPointer.SetValueInt(audioFormID)
            UpdateCurrentInstanceGlobal(SeranaAudioPointer)
            Utility.Wait(0.25)
            If (mainTopic)
                SeranaRef.Say(mainTopic)
            EndIf
        EndIf

        If (sentimentShift != 0)
            Int currentScore = SeranaAffinityScore.GetValueInt()
            Int newScore = currentScore + sentimentShift
            If (newScore > 100)
                newScore = 100
            ElseIf (newScore < -100)
                newScore = -100
            EndIf
            SeranaAffinityScore.SetValueInt(newScore)

            Int newTier = GetAffinityTier(newScore)
            If (newTier != lastAffinityTier)
                If (newTier > lastAffinityTier)
                    SeranaAudioPointer.SetValueInt(8)
                Else
                    SeranaAudioPointer.SetValueInt(9)
                EndIf
                
                UpdateCurrentInstanceGlobal(SeranaAudioPointer)
                lastAffinityTier = newTier
                affinityState = 1 
                affinityTimeout = 0.0
                
                Utility.Wait(0.1)
                SeranaRef.EvaluatePackage()
            EndIf
        EndIf
        
        JsonUtil.SetStringValue("SeranaCommand.json", "intent", "")
        JsonUtil.SetStringValue("SeranaCommand.json", "target_plugin", "")
        JsonUtil.SetIntValue("SeranaCommand.json", "target_formid", 0)
        JsonUtil.SetStringValue("SeranaCommand.json", "sentiment", "")
        JsonUtil.SetStringValue("SeranaCommand.json", "target_name", "")
        JsonUtil.SetIntValue("SeranaCommand.json", "audio_formid", 0)
        JsonUtil.SetIntValue("SeranaCommand.json", "sentiment_shift", 0)
        JsonUtil.SetStringValue("SeranaCommand.json", "tactical_mode", "")
        JsonUtil.Save("SeranaCommand.json")
        
        RegisterForSingleUpdate(PollInterval)
        Return 
    EndIf

    If (SeranaRef != None && !SeranaRef.IsInDialogueWithPlayer())
        Int signalCode = 0

        Int currentTimeState = 0
        If (currentHour >= 6.0 && currentHour < 12.0)
            currentTimeState = 1
        ElseIf (currentHour >= 12.0 && currentHour < 19.0)
            currentTimeState = 2
        Else
            currentTimeState = 3
        EndIf

        If (currentTimeState != lastTimeState)
            lastTimeState = currentTimeState
            signalCode = currentTimeState
        EndIf

        Weather cw = Weather.GetCurrentWeather()
        Int currentWeatState = 1 
        If (cw && cw.GetClassification() == 2)
            currentWeatState = 2
        EndIf
        If (currentWeatState != lastWeatherState && currentWeatState == 2)
            signalCode = 4
        EndIf
        lastWeatherState = currentWeatState

        Location currentLocation = SeranaRef.GetCurrentLocation()
        Bool isInteriorNow = SeranaRef.GetParentCell().IsInterior()
        
        If (currentLocation != lastLocation || isInteriorNow != lastInteriorState)
            lastLocation = currentLocation
            lastInteriorState = isInteriorNow
            
            If (isInteriorNow && currentLocation && currentLocation.HasKeyword(Keyword.GetKeyword("LocTypeDungeon")))
                Utility.Wait(3.0) 
                If (SeranaRef.Is3DLoaded())
                    signalCode = 5
                EndIf
            EndIf
        EndIf

        Bool isInCombat = SeranaRef.IsInCombat()
        If (wasInCombat && !isInCombat)
            signalCode = 6
        EndIf
        wasInCombat = isInCombat

        If (!isInCombat && SeranaRef.GetDistance(Game.GetPlayer()) < 1500.0)
            idleTimer += PollInterval
            If (idleTimer >= 60.0) 
                idleTimer = 0.0
                If (signalCode == 0) 
                    signalCode = 7
                EndIf
            EndIf
        Else
            idleTimer = 0.0
        EndIf

        If (signalCode != 0)
            If (signalCode == 6)
                Utility.Wait(2.0)
            Else
                Utility.Wait(2.5)
            EndIf

            SeranaAudioPointer.SetValueInt(signalCode)
            UpdateCurrentInstanceGlobal(SeranaAudioPointer)
            If (mainTopic)
                SeranaRef.Say(mainTopic)
            EndIf
        EndIf
    EndIf
    
    RegisterForSingleUpdate(PollInterval)
EndEvent

Int Function GetAffinityTier(Int score)
    If (score <= -50)
        Return 1
    ElseIf (score <= -1)
        Return 2
    ElseIf (score <= 49)
        Return 3
    ElseIf (score <= 89)
        Return 4
    Else
        Return 5
    EndIf
EndFunction

Function ResetAffinityForceGreet(Actor SeranaRef)
    SeranaAudioPointer.SetValueInt(0)
    UpdateCurrentInstanceGlobal(SeranaAudioPointer)
    affinityState = 0
    affinityTimeout = 0.0
    SeranaRef.EvaluatePackage() 
EndFunction

Function DistributeLogic(String intentValue, String targetPlugin, Int targetFormID, String sentimentValue, String targetName)
    Actor SeranaRef = SeranaAlias.GetActorRef()
    
    If (SeranaRef == None)
        Return 
    EndIf

    If (sentimentValue == "Positive")
        SeranaRef.SetExpressionOverride(10, 50) 
    ElseIf (sentimentValue == "Negative")
        SeranaRef.SetExpressionOverride(8, 60)  
    Else
        SeranaRef.ClearExpressionOverride() 
    EndIf

    If (intentValue == "Social_Chat")
        ; Handled externally via LLM/Voice processing
    ElseIf (intentValue == "Social_Status")
        ; Kept for structural integrity
    ElseIf (intentValue == "Movement_GoTo")
        HandleMovement(targetPlugin, targetFormID)
    ElseIf (intentValue == "Combat_Attack")
        HandleCombat(targetPlugin, targetFormID, targetName)
    ElseIf (intentValue == "Inventory_Trade")
        HandleTrade()
    ElseIf (intentValue == "Movement_Wait") 
        HandleWait()
    ElseIf (intentValue == "Movement_Follow") 
        HandleFollow()
    ElseIf (intentValue == "Interact_Environment") 
        HandleInteract(targetPlugin, targetFormID)
    ElseIf (intentValue == "System_Dismiss") 
        HandleDismiss()
    ElseIf (intentValue == "Combat_Tactical") 
        HandleTactical()
    EndIf
EndFunction

; =========================================================
; --- HYBRID PATHFINDING ROUTER ---
; =========================================================
Function HandleMovement(String targetPlugin, Int targetFormID)
    Actor SeranaRef = SeranaAlias.GetActorRef()
    Actor PlayerRef = Game.GetPlayer()
    ObjectReference FinalTarget = None
    Location FinalLocation = None

    ; 1. NLU SMART SPLITTER (Location vs Reference)
    If (targetPlugin != "" && targetPlugin != "GENERIC" && targetFormID != 0)
        Form nluForm = Game.GetFormFromFile(targetFormID, targetPlugin)
        If (nluForm)
            ; LAYER 1A: Attempt Location Cast
            FinalLocation = nluForm as Location
            If (!FinalLocation)
                ; LAYER 1B: Attempt Exact Reference Cast
                ObjectReference exactRef = nluForm as ObjectReference
                If (exactRef)
                    FinalTarget = exactRef
                Else
                    ; LAYER 1C: Base Object Proximity Search (10000 units)
                    FinalTarget = Game.FindClosestReferenceOfTypeFromRef(nluForm, PlayerRef, 10000.0)
                EndIf
            EndIf
        EndIf
    EndIf

    ; 2. CROSSHAIR FALLBACK SENSOR
    If (FinalLocation == None && FinalTarget == None)
        ObjectReference CrossRef = Game.GetCurrentCrosshairRef()
        If (CrossRef)
            FinalTarget = CrossRef
        EndIf
    EndIf

    ; 3. TACTICAL ANCHOR PROJECTION (Math-based XMarker)
    If (FinalLocation == None && FinalTarget == None)
        Float angleZ = PlayerRef.GetAngleZ()
        Float targetX = PlayerRef.GetPositionX() + (Math.Sin(angleZ) * 1500.0)
        Float targetY = PlayerRef.GetPositionY() + (Math.Cos(angleZ) * 1500.0)
        Float targetZ = PlayerRef.GetPositionZ()
        
        Form XMarkerBase = Game.GetForm(0x0000003B) 
        ObjectReference InvisibleAnchor = PlayerRef.PlaceAtMe(XMarkerBase)
        InvisibleAnchor.SetPosition(targetX, targetY, targetZ)
        
        FinalTarget = InvisibleAnchor
    EndIf

    ; 4. HAVOK ENGINE EXECUTION
    If (FinalLocation)
        If (SeranaDestLocAlias != None)
            SeranaDestLocAlias.ForceLocationTo(FinalLocation)
        EndIf
        gotoTimeout = 0.0 
        If (SeranaGoToState != None)
            SeranaGoToState.SetValueInt(2) ; ENGAGE MODE 2 (LOCATION)
        EndIf
        SeranaRef.EvaluatePackage()
        
    ElseIf (FinalTarget)
        If (SeranaDestAlias != None)
            SeranaDestAlias.ForceRefTo(FinalTarget)
        EndIf
        gotoTimeout = 0.0 
        If (SeranaGoToState != None)
            SeranaGoToState.SetValueInt(1) ; ENGAGE MODE 1 (REFERENCE)
        EndIf
        SeranaRef.EvaluatePackage()
        
    Else
        If (SeranaGoToState != None)
            SeranaGoToState.SetValueInt(0)
        EndIf
        SeranaRef.EvaluatePackage()
    EndIf
EndFunction

Function HandleWait()
    If (DLC1MentalModel)
        DLC1MentalModel.Wait()
    EndIf
EndFunction

Function HandleFollow()
    Actor SeranaRef = SeranaAlias.GetActorRef()
    
    If (DLC1MentalModel)
        If (DLC1MentalModel.IsWaiting)
            DLC1MentalModel.StopWaiting()
        EndIf
        
        If (!DLC1MentalModel.IsFollowing || DLC1MentalModel.IsDismissed)
            DLC1MentalModel.EngageFollowBehavior(True)
        EndIf
        
        If (SeranaWaitState != None)
            SeranaWaitState.SetValueInt(0)
        EndIf
        If (InteractAlias != None)
            InteractAlias.Clear()
        EndIf
        
        ; RESET ALL GOTO ENGINES
        If (SeranaGoToState != None)
            SeranaGoToState.SetValueInt(0)
        EndIf
        If (SeranaDestAlias != None)
            SeranaDestAlias.Clear()
        EndIf
        If (SeranaDestLocAlias != None)
            SeranaDestLocAlias.Clear()
        EndIf
        
        SeranaRef.EvaluatePackage()
    EndIf
EndFunction

Function HandleDismiss()
    If (DLC1MentalModel)
        DLC1MentalModel.Dismiss()
    EndIf
EndFunction

Function HandleTrade()
    Actor SeranaRef = SeranaAlias.GetActorRef()
    SeranaRef.OpenInventory(True)
EndFunction

Function HandleCombat(String targetPlugin, Int targetFormID, String targetName)
    Actor SeranaRef = SeranaAlias.GetActorRef()
    Actor TargetActor = None
    Actor PlayerRef = Game.GetPlayer()

    If (targetPlugin != "GENERIC" && targetPlugin != "nearest_enemy" && targetFormID != 0)
        TargetActor = Game.GetFormFromFile(targetFormID, targetPlugin) as Actor
    Else
        If (targetPlugin == "GENERIC")
            ObjectReference CrossRef = Game.GetCurrentCrosshairRef()
            If (CrossRef)
                Actor CrossActor = CrossRef as Actor
                If (CrossActor && StringUtil.Find(CrossActor.GetBaseObject().GetName(), targetName) != -1)
                    TargetActor = CrossActor
                EndIf
            EndIf
        EndIf

        If (TargetActor == None)
            Float pX = PlayerRef.GetPositionX()
            Float pY = PlayerRef.GetPositionY()
            Float pZ = PlayerRef.GetPositionZ()
            
            Int scanCount = 0
            While (scanCount < 15 && TargetActor == None)
                Actor FoundActor = Game.FindRandomActor(pX, pY, pZ, 2000.0)
                If (FoundActor)
                    If (targetPlugin == "GENERIC")
                        If (StringUtil.Find(FoundActor.GetBaseObject().GetName(), targetName) != -1)
                            TargetActor = FoundActor
                        EndIf
                    ElseIf (targetPlugin == "nearest_enemy")
                        If (FoundActor.IsHostileToActor(PlayerRef) || FoundActor.GetCombatTarget() == PlayerRef)
                            TargetActor = FoundActor
                        EndIf
                    EndIf
                EndIf
                scanCount += 1
            EndWhile
        EndIf
    EndIf

    If (TargetActor)
        TargetAlias.Clear() 
        SeranaRef.SetGhost(False) 
        SeranaRef.EvaluatePackage()
        
        Utility.Wait(0.1) 

        TargetAlias.ForceRefTo(TargetActor)
        SeranaRef.SetGhost(True) 
        SeranaRef.EvaluatePackage() 
        SeranaRef.StartCombat(TargetActor)
    EndIf
EndFunction

Function HandleInteract(String targetPlugin, Int targetFormID)
    Actor SeranaRef = SeranaAlias.GetActorRef()
    ObjectReference FinalTarget = None

    If (targetPlugin != "" && targetPlugin != "GENERIC" && targetFormID != 0)
        Form nluForm = Game.GetFormFromFile(targetFormID, targetPlugin)
        If (nluForm)
            FinalTarget = Game.FindClosestReferenceOfTypeFromRef(nluForm, Game.GetPlayer(), 2500.0)
        EndIf
    EndIf

    If (FinalTarget == None)
        ObjectReference CrossRef = Game.GetCurrentCrosshairRef()
        If (CrossRef)
            FinalTarget = CrossRef
        EndIf
    EndIf

    If (FinalTarget)
        If (InteractAlias != None)
            InteractAlias.ForceRefTo(FinalTarget)
        EndIf
        interactTimeout = 0.0 
        If (SeranaWaitState != None)
            SeranaWaitState.SetValueInt(2)
        EndIf
        SeranaRef.EvaluatePackage()
    Else
        If (SeranaWaitState != None)
            SeranaWaitState.SetValueInt(0)
        EndIf
        If (InteractAlias != None)
            InteractAlias.Clear()
        EndIf
        SeranaRef.EvaluatePackage()
    EndIf
EndFunction

Function HandleTactical()
    Actor SeranaRef = SeranaAlias.GetActorRef()
    
    If (SeranaRef == None)
        Return
    EndIf
    
    ActorBase SeranaBase = SeranaRef.GetActorBase()
    String tacticalMode = JsonUtil.GetStringValue("SeranaCommand.json", "tactical_mode")
    
    String myModPlugin = "SeranaAI_Core.esp" 
    
    If (tacticalMode == "magic")
        CombatStyle magicStyle = Game.GetFormFromFile(0x06D48A, myModPlugin) as CombatStyle
        If (magicStyle)
            SeranaBase.SetCombatStyle(magicStyle)
        EndIf
        
    ElseIf (tacticalMode == "melee")
        CombatStyle meleeStyle = Game.GetFormFromFile(0x06D48B, myModPlugin) as CombatStyle
        If (meleeStyle)
            SeranaBase.SetCombatStyle(meleeStyle)
        EndIf
        
    ElseIf (tacticalMode == "default")
        CombatStyle defaultStyle = Game.GetFormFromFile(0x011F34, "Dawnguard.esm") as CombatStyle
        If (defaultStyle)
            SeranaBase.SetCombatStyle(defaultStyle)
        EndIf
    EndIf
    
    SeranaRef.EvaluatePackage()
EndFunction