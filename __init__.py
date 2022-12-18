# Jeane Spline Blender Addon
# Copyright (C) 2022 Pierre
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of  MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.

#import blender python libraries
import bpy
import mathutils
import math
import random

#addon info read by Blender
bl_info = {
    "name": "Jeane Spline",
    "author": "Pierre",
    "version": (1, 0, 9),
    "blender": (3, 4, 0),
    "description": "Space Switching Animation Delay Effect",
    "category": "Animation"
    }


#panel class for setting up Jeane Spline
class JSPLINE_PT_SetupPanel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = 'Jeane Spline Setup'
    bl_context = 'objectmode'
    bl_category = 'Jeane Spline'
    #inner working variables
    bpy.context.scene['JSPLINEStopSignal'] = True
    bpy.context.scene['JSPLINEProgressFrame'] = bpy.context.scene.frame_start
    bpy.context.scene['JSPLINEBakeEmpties'] = {}
    bpy.context.scene['JSPLINEMaxFrameDelay'] = 1
    #user control variables
    bpy.types.Scene.JSPLINERotationNoise = bpy.props.FloatProperty(name="Rotation Noise Amount",description="How much noise to bake into empty rotation",default=0,min=0,max=1)
    bpy.types.Scene.JSPLINELocationNoise = bpy.props.FloatProperty(name="Location Noise Amount",description="How much noise to bake into empty location",default=0,min=0,max=1)
    bpy.types.Scene.JSPLINESmoothPosInfluence = bpy.props.FloatProperty(name="Smooth Position Influence",description="Intensity of position smoothing effect",default=0,min=0,max=1)
    bpy.types.Scene.JSPLINESmoothRotInfluence = bpy.props.FloatProperty(name="Smooth Rotation Influence",description="Intensity of rotation smoothing effect",default=0,min=0,max=1)
    bpy.types.Scene.JSPLINEDelayPosInfluence = bpy.props.FloatProperty(name="Delay Position Influence",description="Intensity of position delay effect",default=0.05,min=0,max=1)
    bpy.types.Scene.JSPLINEDelayRotInfluence = bpy.props.FloatProperty(name="Delay Rotation Influence",description="Intensity of rotation delay effect",default=1,min=0,max=1)
    bpy.types.Scene.JSPLINELoopedAnimation = bpy.props.BoolProperty(name="Wrap Frames for Looped Animation",description="Match start and end of animation in timeline range for looping animations",default=False)
    bpy.types.Scene.JSPLINESplitBones = bpy.props.BoolProperty(name="Split Bones for Position Effects",description="Split bones in animated armature so that position smoothing and delay effects work",default=True)
    
    def draw(self, context):
        self.layout.prop(context.scene,"JSPLINESplitBones")
        self.layout.prop(context.scene,"JSPLINELoopedAnimation")
        self.layout.prop(context.scene,"JSPLINERotationNoise",slider=True)
        self.layout.prop(context.scene,"JSPLINELocationNoise",slider=True)
        self.layout.prop(context.scene,"JSPLINESmoothPosInfluence",slider=True)
        self.layout.prop(context.scene,"JSPLINESmoothRotInfluence",slider=True)
        self.layout.prop(context.scene,"JSPLINEDelayPosInfluence",slider=True)
        self.layout.prop(context.scene,"JSPLINEDelayRotInfluence",slider=True)
        self.layout.operator("jspline.applypreset", text ="Preset: Follow Through").presetType = "followthrough"
        self.layout.operator("jspline.applypreset", text ="Preset: Noisy Follow Through").presetType = "noisyfollowthrough"
        self.layout.operator("jspline.applypreset", text ="Preset: Squash and Stretch").presetType = "squashstretch"
        self.layout.operator("jspline.applypreset", text ="Preset: Noisy Smoothing").presetType = "noisysmooth"

#panel class for baking Jeane Spline
class JSPLINE_PT_BakingPanel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = 'Jeane Spline Effect Baking'
    bl_context = 'objectmode'
    bl_category = 'Jeane Spline'

    def draw(self, context):
        self.layout.operator('jspline.startbake', text ='Start Baking for Selected')
        self.layout.operator('jspline.stopbake', text ='Stop Baking for Selected')
        self.layout.operator('jspline.removefromselected', text ='Delete Effect from Selected')
     
def JSPLINE_PositionEmptyForCurrentFrame(emptyObject):
    initialMatrix = None
    finalPosition = None
    #position for object or for bone in armature object
    animatedObject = emptyObject['JSPLINE_object']
    if('JSPLINE_bonename' in emptyObject):
        boneName = emptyObject['JSPLINE_bonename']
        #use position of bone with transform of armature object
        #by multiplying object world matrix by bone matrix
        initialMatrix = animatedObject.matrix_world @ animatedObject.pose.bones[boneName].matrix
    else:
        #use position of object
        initialMatrix = animatedObject.matrix_world
    #set initial matrix
    emptyObject.matrix_world = initialMatrix
    #set offsets for offset type empties
    if(('_rot' in emptyObject['JSPLINE_emptyType']) == True):
        #get forward position for rotation
        #by multiplying animated object position by a forward vector
        finalPosition = initialMatrix @ mathutils.Vector([0,emptyObject['JSPLINE_offsetLength'],0])
    elif(('_roll' in emptyObject['JSPLINE_emptyType']) == True):
        #get side position to control roll
        #by multiplying animated object position by a sideways vector
        finalPosition = initialMatrix @ mathutils.Vector([0,0,emptyObject['JSPLINE_offsetLength']])
    else:
        finalPosition = initialMatrix @ mathutils.Vector([0,0,0])
    emptyObject.location = finalPosition
    #only store transform history for delay empties
    if(('delay' in emptyObject['JSPLINE_emptyType']) == True):
        #store transform history
        emptyObject['JSPLINE_locHistory'][str(bpy.context.scene['JSPLINEProgressFrame'])] = emptyObject.location
        emptyObject['JSPLINE_rotHistory'][str(bpy.context.scene['JSPLINEProgressFrame'])] = emptyObject.rotation_quaternion
        #keep only needed history for delay, remove old frame transform history which will be unused
        maxHistoryLength = bpy.context.scene['JSPLINEMaxFrameDelay']+1
        if(len(emptyObject['JSPLINE_locHistory']) > maxHistoryLength):
            emptyObject['JSPLINE_locHistory'].pop(str(bpy.context.scene['JSPLINEProgressFrame']-maxHistoryLength))
            emptyObject['JSPLINE_rotHistory'].pop(str(bpy.context.scene['JSPLINEProgressFrame']-maxHistoryLength))
    #record last frames if animation is to be looped for any empty
    if((bpy.context.scene.JSPLINELoopedAnimation == True) and (bpy.context.scene['JSPLINEProgressFrame'] > bpy.context.scene.frame_end - 2)):
        recordFrameNumber = bpy.context.scene.frame_end-bpy.context.scene['JSPLINEProgressFrame']
        emptyObject['JSPLINE_endLocations'][str(recordFrameNumber)] = emptyObject.location
        emptyObject['JSPLINE_endRotations'][str(recordFrameNumber)] = emptyObject.rotation_quaternion


#limit number between min and max value
def JSPLINE_LimitToRange(numberToLimit,rangeMin,rangeMax):
    if(numberToLimit > rangeMax):
        numberToLimit = rangeMax
    if(numberToLimit < rangeMin):
        numberToLimit = rangeMin
    return numberToLimit

#add noise to empty object if possible
def JSPLINE_AddNoiseToEmpty(emptyObject):
    canApplyNoise = False
    noiseAmount = 0
    emptyOffsetLength = emptyObject['JSPLINE_offsetLength']
    #apply noise if available
    if((('_rot' in emptyObject['JSPLINE_emptyType']) or ('_roll' in emptyObject['JSPLINE_emptyType'])) and bpy.context.scene.JSPLINERotationNoise > 0):
        canApplyNoise = True
        noiseAmount = bpy.context.scene.JSPLINERotationNoise
    elif((emptyObject['JSPLINE_emptyType'] == 'delay' or emptyObject['JSPLINE_emptyType'] == 'smooth') and bpy.context.scene.JSPLINELocationNoise > 0):
        canApplyNoise = True
        noiseAmount = bpy.context.scene.JSPLINELocationNoise
    if(canApplyNoise == True):
        if(('JSPLINE_posNoiseAdd' in emptyObject) == False):
            emptyObject['JSPLINE_posNoiseAdd'] = mathutils.Vector([0,0,0])
            emptyObject['JSPLINE_posNoiseDirection'] = mathutils.Vector([0,0,0])
        for noiseDimension in range(0,3):
            emptyObject['JSPLINE_posNoiseDirection'][noiseDimension] += random.randrange(-10,10)*0.001
            emptyObject['JSPLINE_posNoiseDirection'][noiseDimension] = JSPLINE_LimitToRange(emptyObject['JSPLINE_posNoiseDirection'][noiseDimension],-0.01*emptyOffsetLength,0.01*emptyOffsetLength)
            emptyObject['JSPLINE_posNoiseAdd'][noiseDimension] += (emptyObject['JSPLINE_posNoiseDirection'][noiseDimension]*(0.4*emptyOffsetLength))*noiseAmount
            emptyObject['JSPLINE_posNoiseAdd'][noiseDimension] = JSPLINE_LimitToRange(emptyObject['JSPLINE_posNoiseAdd'][noiseDimension],-emptyOffsetLength*noiseAmount,emptyOffsetLength*noiseAmount)
        emptyObject.location += mathutils.Vector([emptyObject['JSPLINE_posNoiseAdd'][0],emptyObject['JSPLINE_posNoiseAdd'][1],emptyObject['JSPLINE_posNoiseAdd'][2]])

#delay empties by appropriate frame number
def JSPLINE_DelayEmpty(emptyObject):
    canApplyDelay = False
    #only apply delay if the required delay is smaller than the currently elapsed frames
    if(emptyObject['JSPLINE_framedelay'] < (bpy.context.scene['JSPLINEProgressFrame'] - bpy.context.scene.frame_start)):
        print("apply delay for " + emptyObject.name)
        canApplyDelay = True
        historyFrameNumber = bpy.context.scene['JSPLINEProgressFrame']-emptyObject['JSPLINE_framedelay']
        #print("applying frame " + str(historyFrameNumber) + " at frame " + str(bpy.context.scene['JSPLINEProgressFrame']) + " for delay " + str(emptyObject['JSPLINE_framedelay']))
        emptyObject.location = emptyObject['JSPLINE_locHistory'][str(historyFrameNumber)]
        emptyObject.rotation_quaternion = emptyObject['JSPLINE_rotHistory'][str(historyFrameNumber)]
    return canApplyDelay
        
#create empties to space switch
def JSPLINE_CreateEmptySet(selectedObject,selectedBoneName):
    emptyArray = []
    emptyNameBase = "JSPLINE_EMPTY_" + selectedObject.name
    #if added to a bone, add bone name to empty name
    if(selectedBoneName != None):
        emptyNameBase += "_" + selectedBoneName
    #make empties of each required type
    emptyTypeNames = ['delay','delay_rot','delay_roll','smooth','smooth_rot','smooth_roll']
    for emptyNumber in range(0,len(emptyTypeNames)):
        emptyNameFinal = emptyNameBase + "_" + emptyTypeNames[emptyNumber]
        #make a new empty if it doesn't exist, otherwise get the existing named empty
        if((emptyNameFinal in bpy.context.scene.objects) == False):
            emptyArray.append(bpy.data.objects.new(emptyNameFinal,None))
            emptyArray[emptyNumber]['JSPLINE_emptyType'] = emptyTypeNames[emptyNumber]
            #record in the empty if it is controlling a bone or an object
            if(selectedBoneName != None):
                emptyArray[emptyNumber]['JSPLINE_object'] = selectedObject
                emptyArray[emptyNumber]['JSPLINE_bonename'] = selectedBoneName
                emptyArray[emptyNumber]['JSPLINE_offsetLength'] = selectedObject.data.bones[selectedBoneName].length
            else:
                emptyArray[emptyNumber]['JSPLINE_object'] = selectedObject
                #determine how far out to put empties on objects by dimension average
                #zero dimension defaults to distance of 2
                dimensionTotal = selectedObject.dimensions[0] + selectedObject.dimensions[1] + selectedObject.dimensions[2]
                dimensionAverage = 2
                if(dimensionTotal > 0):
                    dimensionAverage = dimensionTotal / 3
                emptyArray[emptyNumber]['JSPLINE_offsetLength'] = dimensionAverage
            bpy.data.collections['JSPLINEComponents'].objects.link(emptyArray[emptyNumber])
        else: #append the named empty if it already exists
            emptyArray.append(bpy.context.scene.objects[emptyNameFinal])
        #only set up delay frame counts for delay empties
        if(('delay' in emptyArray[emptyNumber]['JSPLINE_emptyType']) == True):
            #set up a clear history for location and rotation
            emptyArray[emptyNumber]['JSPLINE_locHistory'] = {}
            emptyArray[emptyNumber]['JSPLINE_rotHistory'] = {}
            #determine frame delay for bone or object based on selected parents
            remainingSelectedChain = False
            parentName = None
            parentObject = None
            delayFrameNumber = 1
            #get delay frames for bones
            if(selectedBoneName != None):
                #add delay count for any parent bone that is selected
                if(selectedObject.pose.bones[selectedBoneName].parent != None):
                    if(selectedObject.pose.bones[selectedBoneName].parent.bone.select == True):
                        remainingSelectedChain = True
                        parentName = selectedObject.pose.bones[selectedBoneName].parent.name
                while remainingSelectedChain == True:
                    remainingSelectedChain = False
                    if(selectedObject.pose.bones[parentName].parent != None):
                        if(selectedObject.pose.bones[selectedBoneName].parent.bone.select == True):
                            delayFrameNumber += 1
                            remainingSelectedChain = True
                            parentName = selectedObject.pose.bones[parentName].parent.name
            else:
                #get delay frames for objects
                if(selectedObject.parent != None):
                    if(selectedObject.parent.select_get() == True):
                        remainingSelectedChain = True
                        parentObject = selectedObject.parent
                while remainingSelectedChain == True:
                    remainingSelectedChain = False
                    if(parentObject.parent != None):
                        if(parentObject.parent.select_get() == True):
                            delayFrameNumber += 1
                            remainingSelectedChain = True
                            parentObject = parentObject.parent
            #set max frame delay that Jeane Spline will need to keep history for to do this delay
            if(delayFrameNumber > bpy.context.scene['JSPLINEMaxFrameDelay']):
                bpy.context.scene['JSPLINEMaxFrameDelay'] = delayFrameNumber
            #store frame delay in empty
            emptyArray[emptyNumber]['JSPLINE_framedelay'] = delayFrameNumber
        #set up clear end frame transform record if animation is to be looped
        emptyArray[emptyNumber]['JSPLINE_endLocations'] = {}
        emptyArray[emptyNumber]['JSPLINE_endRotations'] = {}
        #clear any existing empty animation before new bake
        emptyArray[emptyNumber].animation_data_clear()
        #store empty to be baked
        bpy.context.scene['JSPLINEBakeEmpties'][emptyArray[emptyNumber].name] = emptyArray[emptyNumber]
        #set to use quaternion rotation
        emptyArray[emptyNumber].rotation_mode = 'QUATERNION'
        #position empty for frame
        JSPLINE_PositionEmptyForCurrentFrame(emptyArray[emptyNumber])
    #return empty array for further use
    return emptyArray

#create constraints for a bone or object
def JSPLINE_createAnimatedObjectConstraints(animatedObject,emptyArray):
    #names for constraints when constraining animated objects or bones to empties
    constraintNames = ['JSPLINE_delaypos','JSPLINE_delayrot','JSPLINE_delayroll','JSPLINE_smoothpos','JSPLINE_smoothrot','JSPLINE_smoothroll']
    smoothPosInfluence = bpy.context.scene.JSPLINESmoothPosInfluence
    smoothRotInfluence = bpy.context.scene.JSPLINESmoothRotInfluence
    DelayPosInfluence = bpy.context.scene.JSPLINEDelayPosInfluence
    DelayRotInfluence = bpy.context.scene.JSPLINEDelayRotInfluence
    constraintInfluences = [DelayPosInfluence,DelayRotInfluence,DelayRotInfluence,smoothPosInfluence,smoothRotInfluence,smoothRotInfluence]
    constructedConstraints = []
    if((constraintNames[0] in animatedObject.constraints) == False):
        constraintTypes = ['COPY_LOCATION','DAMPED_TRACK','LOCKED_TRACK','COPY_LOCATION','DAMPED_TRACK','LOCKED_TRACK']
        for constraintNumber in range(0,len(constraintNames)):
            emptyConstraint = animatedObject.constraints.new(constraintTypes[constraintNumber])
            emptyConstraint.name = constraintNames[constraintNumber]
            emptyConstraint.target = emptyArray[constraintNumber]
            constructedConstraints.append(emptyConstraint)
    #set specifics for each constraint
    constructedConstraints[2].track_axis = 'TRACK_Y'
    constructedConstraints[2].lock_axis = 'LOCK_Y'
    constructedConstraints[5].track_axis = 'TRACK_Y'
    constructedConstraints[5].lock_axis = 'LOCK_Y'
    for constraintNumber in range(0,len(constraintNames)):
        #constraints to be turned off initially, wether new or pre-existing
        animatedObject.constraints[constraintNames[constraintNumber]].enabled = False
        #set constraint influences based on type
        animatedObject.constraints[constraintNames[constraintNumber]].influence = constraintInfluences[constraintNumber]
        
#enable all constraints for an animated object
def JSPLINE_enableAnimatedObjectConstraints(emptyObject):
    animatedObject = None
    if('JSPLINE_bonename' in emptyObject):
        animatedObject = emptyObject['JSPLINE_object'].pose.bones[emptyObject['JSPLINE_bonename']]
    else:
        animatedObject = emptyObject['JSPLINE_object']
    for possibleConstraint in animatedObject.constraints:
        if('JSPLINE_' in possibleConstraint.name):
            possibleConstraint.enabled = True

#remove all effect constraints and empties from selected
def JSPLINE_removeFromSelected():
    nameVariants = ["_delay","_delay_roll","_delay_rot","_smooth","_smooth_roll","_smooth_rot"]
    #remove all empties tied to selected objects
    for possibleModifiedObject in bpy.context.selected_objects:
        emptyNameBase = "JSPLINE_EMPTY_" + possibleModifiedObject.name
        if(possibleModifiedObject.type == 'ARMATURE'):
            for possibleSelectedBone in possibleModifiedObject.pose.bones:
                if(possibleSelectedBone.bone.select == True):
                    #get empties by name in scene and delete from data
                    emptyWithBoneName = emptyNameBase + "_" + possibleSelectedBone.name
                    for nameVariantNumber in range(0,len(nameVariants)):
                        if(emptyWithBoneName + nameVariants[nameVariantNumber] in bpy.context.scene.objects):
                            bpy.data.objects.remove(bpy.context.scene.objects[emptyWithBoneName + nameVariants[nameVariantNumber]])
                    #remove constraints from bones
                    for possibleEffectConstraint in possibleSelectedBone.constraints:
                        if("JSPLINE_" in possibleEffectConstraint.name):
                            possibleSelectedBone.constraints.remove(possibleEffectConstraint)
        elif(possibleModifiedObject.type == 'MESH'):
            for nameVariantNumber in range(0,len(nameVariants)):
                if(emptyNameBase + nameVariants[nameVariantNumber] in bpy.context.scene.objects):
                    bpy.data.objects.remove(bpy.context.scene.objects[emptyNameBase + nameVariants[nameVariantNumber]])
            #remove constraints from object
            for possibleEffectConstraint in possibleModifiedObject.constraints:
                if("JSPLINE_" in possibleEffectConstraint.name):
                    possibleModifiedObject.constraints.remove(possibleEffectConstraint)

#function to begin modal running
class JSPLINE_OT_StartBake(bpy.types.Operator):
    bl_idname = "jspline.startbake"
    bl_label = "Start Baking Selected"
    bl_description = "Start baking space switching delay effect on selected. Effect will be applied to selected bones of selected armatures and to selected objects."
    
    #timer for running modal
    JSPLINETimer = None
    
    #repeated while running
    def modal(self, context, event):
        #stop modal timer if the stop signal is activated
        if(bpy.context.scene['JSPLINEStopSignal'] == True):
            context.window_manager.event_timer_remove(self.JSPLINETimer)
            #enable all constraints
            for bakedEmptyName in list(bpy.context.scene['JSPLINEBakeEmpties']):
                bakedEmpty = bpy.context.scene['JSPLINEBakeEmpties'][bakedEmptyName]
                JSPLINE_enableAnimatedObjectConstraints(bakedEmpty)
            self.report({'INFO'},"Jeane Spline baking stopped.")
            return {'CANCELLED'}
        else: 
            #step through frames in scene
            if(bpy.context.scene['JSPLINEProgressFrame'] <= bpy.context.scene.frame_end):
                #record keyframe for each empty to be baked
                for bakingEmptyName in list(bpy.context.scene['JSPLINEBakeEmpties']):
                    bakingEmpty = bpy.context.scene['JSPLINEBakeEmpties'][bakingEmptyName]
                    JSPLINE_PositionEmptyForCurrentFrame(bakingEmpty)
                    canRecordKeyFrame = True
                    locationRecordInterval = 3
                    rotationRecordInterval = 4
                    #only delay if it is an empty of delay type
                    if(('delay' in bakingEmpty['JSPLINE_emptyType']) == True):
                        #if the required delay is more than the elapsed frames, no keyframe can be recorded yet
                        #delay function will determine this
                        canRecordKeyFrame = JSPLINE_DelayEmpty(bakingEmpty)
                        #record closer intervals for delay empties
                        locationRecordInterval = 2
                        rotationRecordInterval = 2
                    #add empty noise if possible
                    JSPLINE_AddNoiseToEmpty(bakingEmpty)
                    #don't record a keyframe if looped is enabled and it's close to the end of the animation
                    if(bpy.context.scene.JSPLINELoopedAnimation == True):
                        if(bpy.context.scene['JSPLINEProgressFrame'] > bpy.context.scene.frame_end - 4):
                            canRecordKeyFrame = False
                    #don't record keyframe if not appropriate
                    if(canRecordKeyFrame == True):
                        #keyframe in intervals for smoothing
                        if(bpy.context.scene['JSPLINEProgressFrame'] % locationRecordInterval == 0):
                            bakingEmpty.keyframe_insert("location")
                        if(bpy.context.scene['JSPLINEProgressFrame'] % rotationRecordInterval == 0):
                            bakingEmpty.keyframe_insert("rotation_quaternion")
                    #prepare last frame for wrap-around if looping animation is selected
                    if((bpy.context.scene.JSPLINELoopedAnimation == True) and (bpy.context.scene['JSPLINEProgressFrame'] == bpy.context.scene.frame_end)):
                        bakingEmpty.location = bakingEmpty['JSPLINE_endLocations']['0']
                        bakingEmpty.rotation_quaternion = bakingEmpty['JSPLINE_endRotations']['0']
                        bakingEmpty.keyframe_insert("location")
                        bakingEmpty.keyframe_insert("rotation_quaternion")
                bpy.context.scene['JSPLINEProgressFrame'] += 1
                bpy.context.scene.frame_set(bpy.context.scene['JSPLINEProgressFrame'])
                return {'PASS_THROUGH'}
            else:
                #stop baking when last frame reached
                context.window_manager.event_timer_remove(self.JSPLINETimer)
                bpy.context.scene['JSPLINEStopSignal'] = True
                #return to frame 1 for wrapping changes if loop is enabled
                if(bpy.context.scene.JSPLINELoopedAnimation == True):
                    bpy.context.scene.frame_set(bpy.context.scene.frame_start)
                #iterate all empties for final changes
                for bakedEmptyName in list(bpy.context.scene['JSPLINEBakeEmpties']):
                    bakedEmpty = bpy.context.scene['JSPLINEBakeEmpties'][bakedEmptyName]
                    #wrap animation for empty if looping animation is selected
                    if(bpy.context.scene.JSPLINELoopedAnimation == True):
                        bakedEmpty.location = bakedEmpty['JSPLINE_endLocations']['1']
                        bakedEmpty.rotation_quaternion = bakedEmpty['JSPLINE_endRotations']['1']
                        bakedEmpty.keyframe_insert("location")
                        bakedEmpty.keyframe_insert("rotation_quaternion")
                    #enable all constraints
                    JSPLINE_enableAnimatedObjectConstraints(bakedEmpty)
                self.report({'INFO'},"Jeane Spline baking completed.")
                return {'CANCELLED'}
            
        
    #first setup
    def execute(self, context):
        #stop if encountering stop signal
        if(bpy.context.scene['JSPLINEStopSignal'] == True):
            bpy.context.scene['JSPLINEStopSignal'] = False
            
            #cancelling currently playing animation seems only possible with an operator
            bpy.ops.screen.animation_cancel()
            #remove existing constraints and empties from selected for best results
            JSPLINE_removeFromSelected()
            #set frame to start, ready to begin stepping through all frames
            bpy.context.scene.frame_set(bpy.context.scene.frame_start)
            bpy.context.scene['JSPLINEProgressFrame'] = bpy.context.scene.frame_start
            
            #new bake empties dictionary for new bake
            bpy.context.scene['JSPLINEBakeEmpties'] = {}
            
            
            #make sure collection exists to put empties
            if(('JSPLINEComponents' in bpy.data.collections) == False):
                newCollection = bpy.data.collections.new('JSPLINEComponents')
                bpy.context.scene.collection.children.link(newCollection)
            
            #create empties for objects that are to be baked
            for possibleBakeObject in bpy.context.selected_objects:
                if(possibleBakeObject.type == 'ARMATURE'):
                    for possibleSelectedBone in possibleBakeObject.pose.bones:
                        if(possibleSelectedBone.bone.select == True):
                            #split bone if allowed
                            if(bpy.context.scene.JSPLINESplitBones == True):
                                boneName = possibleSelectedBone.name
                                #ops appears to be the only way to do this
                                bpy.ops.object.select_all(action='DESELECT')
                                possibleBakeObject.select_set(True)
                                bpy.context.view_layer.objects.active = possibleBakeObject
                                bpy.ops.object.mode_set(mode='EDIT', toggle=False)
                                possibleBakeObject.data.edit_bones[boneName].use_connect = False
                                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
                            #create empties
                            emptyArray = JSPLINE_CreateEmptySet(possibleBakeObject,possibleSelectedBone.name)
                            #create bone constraints
                            JSPLINE_createAnimatedObjectConstraints(possibleSelectedBone,emptyArray)
                elif(possibleBakeObject.type == 'MESH'):
                    #create empties
                    emptyArray = JSPLINE_CreateEmptySet(possibleBakeObject,None)
                    #create object constraints
                    JSPLINE_createAnimatedObjectConstraints(possibleBakeObject,emptyArray)
            self.report({'INFO'},"Started baking space-switch delay effect for selected with Jeane Spline.")
            
            #set up timer and handler last, errors generated in execute may cause a crash otherwise  
            self.JSPLINETimer = context.window_manager.event_timer_add(0.1, window=context.window)
            context.window_manager.modal_handler_add(self)  
            return {'RUNNING_MODAL'}
        else:
            #warning if start is pressed while already running
            self.report({'WARNING'},"Jeane Spline is already baking. Please Stop Baking before pressing start.")
            return {'FINISHED'}
        
        
#function to stop modal running
class JSPLINE_OT_StopBake(bpy.types.Operator):
    bl_idname = "jspline.stopbake"
    bl_label = "Stop Baking Selected"
    bl_description = "Stop baking space-switch delay effect on selected."
    
    #turn on the stop signal switch
    def execute(self, context):
        bpy.context.scene['JSPLINEStopSignal'] = True
        return {'FINISHED'}
    
#function to remove Jeane Spline effects from selected
class JSPLINE_OT_RemoveFromSelected(bpy.types.Operator):
    bl_idname = "jspline.removefromselected"
    bl_label = "Remove Jeane Spline Effects Selected"
    bl_description = "Remove delay and smoothing constraints and empties connected to selected"
    
    #remove effect
    def execute(self, context):
        JSPLINE_removeFromSelected()
        self.report({'INFO'},"Cleared all Jeane Spline effects from selected.")
        return {'FINISHED'}
    
#function to apply a preset to Jeane Spline setup
class JSPLINE_OT_ApplyPreset(bpy.types.Operator):
    bl_idname = "jspline.applypreset"
    bl_label = "Apply Jeane Spline Settings Preset"
    bl_description = "Apply preset values to Jeane Spline settings for a specific effect type"
    presetType: bpy.props.StringProperty(name="presetTypeString")
   
    #apply preset values
    def execute(self, context):
        if(self.presetType == "followthrough"):
            bpy.context.scene.JSPLINERotationNoise = 0
            bpy.context.scene.JSPLINELocationNoise = 0
            bpy.context.scene.JSPLINESmoothPosInfluence = 0
            bpy.context.scene.JSPLINESmoothRotInfluence = 0
            bpy.context.scene.JSPLINEDelayPosInfluence = 0.05
            bpy.context.scene.JSPLINEDelayRotInfluence = 1
        elif(self.presetType == "noisyfollowthrough"):
            bpy.context.scene.JSPLINERotationNoise = 0.2
            bpy.context.scene.JSPLINELocationNoise = 0.05
            bpy.context.scene.JSPLINESmoothPosInfluence = 0
            bpy.context.scene.JSPLINESmoothRotInfluence = 0
            bpy.context.scene.JSPLINEDelayPosInfluence = 0.05
            bpy.context.scene.JSPLINEDelayRotInfluence = 1
        elif(self.presetType == "squashstretch"):
            bpy.context.scene.JSPLINERotationNoise = 0
            bpy.context.scene.JSPLINELocationNoise = 0
            bpy.context.scene.JSPLINESmoothPosInfluence = 0
            bpy.context.scene.JSPLINESmoothRotInfluence = 0
            bpy.context.scene.JSPLINEDelayPosInfluence = 0.6
            bpy.context.scene.JSPLINEDelayRotInfluence = 0.2
        elif(self.presetType == "noisysmooth"):
            bpy.context.scene.JSPLINERotationNoise = 0.3
            bpy.context.scene.JSPLINELocationNoise = 0.2
            bpy.context.scene.JSPLINESmoothPosInfluence = 1
            bpy.context.scene.JSPLINESmoothRotInfluence = 1
            bpy.context.scene.JSPLINEDelayPosInfluence = 0
            bpy.context.scene.JSPLINEDelayRotInfluence = 0
        self.report({'INFO'},"Applied a Jeane Spline preset to settings.")
        return {'FINISHED'}

    
#register and unregister panels and operators
addonClasses = (  JSPLINE_PT_SetupPanel,
                    JSPLINE_PT_BakingPanel,
                    JSPLINE_OT_ApplyPreset,
                    JSPLINE_OT_StartBake,
                    JSPLINE_OT_StopBake,
                    JSPLINE_OT_RemoveFromSelected
                    )

register, unregister = bpy.utils.register_classes_factory(addonClasses)

if __name__ == '__main__':
    register()
