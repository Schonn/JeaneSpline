# Jeane Spline Blender Addon
# Copyright (C) 2018 Pierre
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
import random
import math
import mathutils

#addon info read by Blender
bl_info = {
    "name": "Jeane Spline",
    "author": "Pierre",
    "version": (1, 0, 8),
    "blender": (2, 80, 0),
    "description": "Animation Delay Effect",
    "category": "Animation"
    }


#panel class for delay effect related menu items
class JSPLINE_PT_SpliningPanel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = 'Delay Effect'
    bl_context = 'posemode'
    bl_category = 'Jeane Spline'
    bpy.types.Scene.JSPLINERotateAmount = bpy.props.FloatProperty(name="Effect Rotation Influence",description="The influence that the rotation delay effect will have on the selected bone(s)",default=1,min=0,max=1)
    bpy.types.Scene.JSPLINETranslateAmount = bpy.props.FloatProperty(name="Effect Translation Influence",description="The influence that the translation delay effect will have on the selected bone(s)",default=0.5,min=0,max=1)
    bpy.types.Scene.JSPLINENoiseAmplitude = bpy.props.FloatProperty(name="Effect Noise Amplitude",description="The amount of rotation and translation noise that will be added to the selected bone(s)",default=0.1,min=0,max=5)
    bpy.types.Scene.JSPLINELooped = bpy.props.BoolProperty(name="Seamless Looping Animation",description="Cut the animation to loop seamlessly in the current timeline region",default=False)
    bpy.types.Scene.JSPLINEEnvelopePercent = bpy.props.IntProperty(name="Looping Envelope Timeline Percent",description="The percentage from the start and end of the timeline that keyframes will be placed to create an influence envelope",default=50,min=1,max=50)
    
    def draw(self, context):
        self.layout.prop(context.scene,"JSPLINELooped")
        self.layout.prop(context.scene,"JSPLINERotateAmount",slider=True)
        self.layout.prop(context.scene,"JSPLINETranslateAmount",slider=True)
        self.layout.prop(context.scene,"JSPLINENoiseAmplitude",slider=True)
        self.layout.operator('jspline.smoothbone', text ='Apply Effect To Selected Bone(s)')
        self.layout.operator('jspline.revertbone', text ='Remove Effect From Selected Bone(s)')
        self.layout.operator('jspline.keyinfluence', text ='Keyframe Influence For Selected Bone(s)')
        self.layout.operator('jspline.keydisable', text ='Keyframe Disable For Selected Bone(s)')
        self.layout.prop(context.scene,"JSPLINEEnvelopePercent",slider=True)
        self.layout.operator('jspline.keyenvelope', text ='Keyframe Envelope For Selected Bone(s)')
        self.layout.operator('jspline.resetdefault', text ='Reset Effect Settings To Default')        


#button to reset Jeane Spline to default settings    
class JSPLINE_OT_ResetDefaults(bpy.types.Operator):
    bl_idname = "jspline.resetdefault"
    bl_label = "Reset Effect Settings To Default Values"
    bl_description = "Reset Rotation Influence, Translation Influence and Noise Amplitude sliders to their default values."
    def execute(self, context):
        context.scene.JSPLINERotateAmount = 1 #set the rotate influence to full by default
        context.scene.JSPLINETranslateAmount = 0.5 #reduce the amount of translation delay by default
        context.scene.JSPLINENoiseAmplitude = 0.1 #reduce the amount of noise by default
        context.scene.JSPLINEEnvelopePercent = 50 #triangular shaped envelope by default
        return {'FINISHED'}

#button to apply the delay effect to the selected bone(s)
class JSPLINE_OT_SmoothBone(bpy.types.Operator):
    bl_idname = "jspline.smoothbone"
    bl_label = "Apply Delay To Selected Bone(s)"
    bl_description = "Apply or update the delay effect on the selected bone(s) using the specified rotate and translate influence."
    
    #snap to a frame and create a keyframe based on the location of the object
    def createKeyframeOnFrame(self,context,frameNumber,targetObject):
        context.scene.frame_set(frameNumber)
        bpy.ops.object.select_all(action='DESELECT')
        targetObject.select_set(True)
        context.view_layer.objects.active = targetObject
        bpy.ops.anim.keyframe_insert_menu(type='Location')
    
    #delete frames in a given region
    def deleteFramesRegion(self,context,frameFrom,frameTo,targetObject):
        for frameNumber in range(frameFrom,frameTo):
            targetObject.keyframe_delete(data_path="location",frame=frameNumber)
            targetObject.keyframe_delete(data_path="rotation_quaternion",frame=frameNumber)
            targetObject.keyframe_delete(data_path="scale",frame=frameNumber)
            
    #delete frames in a given region for bones
    def deleteFramesRegionBones(self,context,frameFrom,frameTo,targetObject):
        for frameNumber in range(frameFrom,frameTo):
            targetObject.keyframe_delete(data_path="location",frame=frameNumber)
            targetObject.keyframe_delete(data_path="rotation_quaternion",frame=frameNumber)
    
    #duplicate a location from one frame to another
    def duplicateLocationFrameData(self,context,frameFrom,frameTo,targetObject):
        context.scene.frame_set(frameFrom)
        targetObject.keyframe_insert(data_path="location",frame=frameTo)
    
    #duplicate a rotation from one frame to another
    def duplicateRotationFrameData(self,context,frameFrom,frameTo,targetObject):
        context.scene.frame_set(frameFrom)
        targetObject.keyframe_insert(data_path="rotation_quaternion",frame=frameTo)
        
    def delayFcurves(self,context,animationFcurves,delayFrames,keyFrame):
        animationFcurves.keyframe_points[keyFrame].co.x += delayFrames
        animationFcurves.keyframe_points[keyFrame].co.y += (animationFcurves.keyframe_points[keyFrame-1].co.y - animationFcurves.keyframe_points[keyFrame].co.y)
        animationFcurves.update()
    
    def addFcurveNoise(self,context,animationFcurves,noiseStrength):
        fcurvesNoise = animationFcurves.modifiers.new(type='NOISE')
        fcurvesNoise.blend_type = "REPLACE"
        fcurvesNoise.scale = random.randint(15,40)
        fcurvesNoise.strength = noiseStrength
        fcurvesNoise.phase = random.randint(1,100)
        fcurvesNoise.offset = random.randint(1,30)
        
    def setupCollection(self,context,newCollectionName):
        if(newCollectionName not in bpy.data.collections.keys()):
            bpy.ops.collection.create(name=newCollectionName)
            if(context.collection.name == "Master Collection"):
                bpy.context.scene.collection.children.link(bpy.data.collections[newCollectionName])
            else:
                bpy.data.collections[context.collection.name].children.link(bpy.data.collections[newCollectionName])

    def assignToCollection(self,context,assignCollectionName,assignObject):
        if(assignObject.name not in bpy.data.collections[assignCollectionName].objects):
            bpy.data.collections[assignCollectionName].objects.link(assignObject)
            if(context.collection.name == "Master Collection"):
                bpy.context.scene.collection.objects.unlink(assignObject)
            else:
                bpy.data.collections[context.collection.name].objects.unlink(assignObject)
        
    def execute(self, context):
        #make sure empties are enabled to avoid null error
        originalEmptyVisibility = context.space_data.show_object_viewport_empty
        context.space_data.show_object_viewport_empty = True
        
        #clear any existing effects
        bpy.ops.jspline.revertbone()
        #store settings for effects
        sceneObjects = context.scene.objects
        rotateInfluence = context.scene.JSPLINERotateAmount
        translateInfluence = context.scene.JSPLINETranslateAmount
        loopedAnimation = context.scene.JSPLINELooped
        noiseAmplitude = context.scene.JSPLINENoiseAmplitude
        #original timeline duration for looping animations
        originalTimeStart = context.scene.frame_start
        originalTimeEnd = context.scene.frame_end
        #how many times to loop the animation to extract a seamless loop
        loopTimes = 8
        #speed up processing by setting simplify
        context.scene.render.use_simplify = True
        context.scene.render.simplify_subdivision = 0
        #iterate through all selected bones in pose mode to perform effects
        for bone in range(len(context.selected_pose_bones)):
            #store the current selected bone in the iteration
            targetBone = context.selected_pose_bones[bone]
            #switch to object mode and create empties for delaying location, rotation and pole
            bpy.ops.object.mode_set(mode='OBJECT')
            #store the current selected armature
            targetArmature = context.view_layer.objects.active
            if(loopedAnimation == True):
                self.deleteFramesRegionBones(context,originalTimeEnd,originalTimeEnd+(10*(originalTimeEnd-originalTimeStart)),targetBone)
                context.scene.frame_end *= loopTimes
                for fcurve in range(0,len(targetArmature.animation_data.action.fcurves)):
                    keyframeSet = len(targetArmature.animation_data.action.fcurves[fcurve].keyframe_points)
                    for keyframe in range(0,keyframeSet):
                        currentKeyFrame = targetArmature.animation_data.action.fcurves[fcurve].keyframe_points[keyframe]
                        #don't insert keyframes further than necessary
                        if(currentKeyFrame.co.x <= originalTimeEnd + ((originalTimeEnd-originalTimeStart)*(loopTimes-1))):
                            context.scene.frame_set(currentKeyFrame.co.x)
                            originalAnimationLength = (originalTimeEnd - originalTimeStart) + 1
                            for repeatNumber in range (1,loopTimes-1):
                                    targetBone.keyframe_insert(data_path="location",frame=(currentKeyFrame.co.x) + (originalAnimationLength*repeatNumber))
                                    targetBone.keyframe_insert(data_path="rotation_quaternion",frame=(currentKeyFrame.co.x) + (originalAnimationLength*repeatNumber))
                context.scene.frame_end = originalTimeEnd + ((originalTimeEnd-originalTimeStart)*loopTimes-1)
            bpy.ops.object.select_all(action='DESELECT')
            bpy.ops.object.empty_add(type='PLAIN_AXES',location=(0,0,0))
            context.object.name = "JSPLINE_TransformSmoothAxes" 
            transformSmoothObject = context.object
            bpy.ops.object.select_all(action='DESELECT')
            bpy.ops.object.empty_add(type='PLAIN_AXES',location=(0,10,0))
            context.object.name = "JSPLINE_RotateSmoothAxes" 
            rotateSmoothObject = context.object
            bpy.ops.object.select_all(action='DESELECT')
            bpy.ops.object.empty_add(type='PLAIN_AXES',location=(0,10,0))
            context.object.name = "JSPLINE_PoleSmoothAxes" 
            poleSmoothObject = context.object
            #manage collections
            self.setupCollection(context,"JSPLINEEmpties_" + targetArmature.name)
            self.assignToCollection(context,"JSPLINEEmpties_" + targetArmature.name,transformSmoothObject)
            self.assignToCollection(context,"JSPLINEEmpties_" + targetArmature.name,rotateSmoothObject)
            self.assignToCollection(context,"JSPLINEEmpties_" + targetArmature.name,poleSmoothObject)
            #set rotations to quaternion to avoid gimbal lock
            sceneObjects["JSPLINE_RotateSmoothAxes"].rotation_mode = 'QUATERNION'
            sceneObjects["JSPLINE_TransformSmoothAxes"].rotation_mode = 'QUATERNION'
            sceneObjects["JSPLINE_PoleSmoothAxes"].rotation_mode = 'QUATERNION'
            #snap the empties to the desired locations on each bone, with a long distance to improve rotation smoothing effects
            positionEmptiesConstraint = bpy.data.objects["JSPLINE_TransformSmoothAxes"].constraints.new('COPY_TRANSFORMS')
            positionEmptiesConstraint.target = targetArmature
            positionEmptiesConstraint.subtarget = targetBone.name
            sceneObjects["JSPLINE_RotateSmoothAxes"].parent = targetArmature
            sceneObjects["JSPLINE_RotateSmoothAxes"].parent_type = 'BONE'
            sceneObjects["JSPLINE_RotateSmoothAxes"].parent_bone = targetBone.name
            sceneObjects["JSPLINE_RotateSmoothAxes"].location = [0,10,0]
            sceneObjects["JSPLINE_PoleSmoothAxes"].parent = targetArmature
            sceneObjects["JSPLINE_PoleSmoothAxes"].parent_type = 'BONE'
            sceneObjects["JSPLINE_PoleSmoothAxes"].parent_bone = targetBone.name
            sceneObjects["JSPLINE_PoleSmoothAxes"].location = [10,0,0]
            #bake the motion of each empty so that it can be delayed
            bpy.ops.object.select_all(action='DESELECT')
            sceneObjects["JSPLINE_TransformSmoothAxes"].select_set(True)
            context.view_layer.objects.active = sceneObjects["JSPLINE_TransformSmoothAxes"]
            #offset start for keyframes
            keyframeOffsetStart = 1
            #delay x,y,z position
            if(loopedAnimation == True):
                bpy.ops.nla.bake(frame_start=context.scene.frame_start,frame_end=context.scene.frame_end,step=3,only_selected=True,visual_keying=True,clear_constraints=True,clear_parents=True,use_current_action=True,bake_types={'OBJECT'})
            else:
                bpy.ops.nla.bake(frame_start=context.scene.frame_start,frame_end=context.scene.frame_end,step=1,only_selected=True,visual_keying=True,clear_constraints=True,clear_parents=True,use_current_action=True,bake_types={'OBJECT'})
            for fcurve in range(0,3):
                for keyframe in reversed(range(keyframeOffsetStart,len(sceneObjects["JSPLINE_TransformSmoothAxes"].animation_data.action.fcurves[fcurve].keyframe_points))):
                    animationFcurves = sceneObjects["JSPLINE_TransformSmoothAxes"].animation_data.action.fcurves[fcurve]
                    self.delayFcurves(context,animationFcurves,1,keyframe)
                    #don't add noise to looped animations
                    if(loopedAnimation == False):
                        self.addFcurveNoise(context,animationFcurves,noiseAmplitude*0.1)
            bpy.ops.object.select_all(action='DESELECT')
            sceneObjects["JSPLINE_RotateSmoothAxes"].select_set(True)
            context.view_layer.objects.active = sceneObjects["JSPLINE_RotateSmoothAxes"]
            #delay x,y,z ik rotation smoothing and pole smoothing separately
            if(loopedAnimation == True):
                bpy.ops.nla.bake(frame_start=context.scene.frame_start,frame_end=context.scene.frame_end,step=3,only_selected=True,visual_keying=True,clear_constraints=True,clear_parents=True,use_current_action=True,bake_types={'OBJECT'})
            else:
                bpy.ops.nla.bake(frame_start=context.scene.frame_start,frame_end=context.scene.frame_end,step=1,only_selected=True,visual_keying=True,clear_constraints=True,clear_parents=True,use_current_action=True,bake_types={'OBJECT'})
            for fcurve in range(0,3):
                for keyframe in reversed(range(keyframeOffsetStart,len(sceneObjects["JSPLINE_RotateSmoothAxes"].animation_data.action.fcurves[fcurve].keyframe_points))):
                    animationFcurves = sceneObjects["JSPLINE_RotateSmoothAxes"].animation_data.action.fcurves[fcurve]
                    #don't add noise or too much rotation delay to looped animations
                    if(loopedAnimation == True):
                        self.delayFcurves(context,animationFcurves,1,keyframe)
                    else:
                        self.delayFcurves(context,animationFcurves,2,keyframe)
                        self.addFcurveNoise(context,animationFcurves,noiseAmplitude)
            bpy.ops.object.select_all(action='DESELECT')
            sceneObjects["JSPLINE_PoleSmoothAxes"].select_set(True)
            context.view_layer.objects.active = sceneObjects["JSPLINE_PoleSmoothAxes"]
            #baking for pole smooth
            if(loopedAnimation == True):
                bpy.ops.nla.bake(frame_start=context.scene.frame_start,frame_end=context.scene.frame_end,step=3,only_selected=True,visual_keying=True,clear_constraints=True,clear_parents=True,use_current_action=True,bake_types={'OBJECT'})
            else:
                bpy.ops.nla.bake(frame_start=context.scene.frame_start,frame_end=context.scene.frame_end,step=1,only_selected=True,visual_keying=True,clear_constraints=True,clear_parents=True,use_current_action=True,bake_types={'OBJECT'})
            for fcurve in range(0,3):
                for keyframe in reversed(range(keyframeOffsetStart,len(sceneObjects["JSPLINE_PoleSmoothAxes"].animation_data.action.fcurves[fcurve].keyframe_points))):
                    animationFcurves = sceneObjects["JSPLINE_PoleSmoothAxes"].animation_data.action.fcurves[fcurve]
                    self.delayFcurves(context,animationFcurves,1,keyframe)
                    #don't add noise to looped animations
                    if(loopedAnimation == False):
                        self.addFcurveNoise(context,animationFcurves,noiseAmplitude)
            #if the animation is intended to be looped, shift the baked animation to make it happen
            if(loopedAnimation == True):
                #iterate over axes types to save lines
                axesTypes = ["JSPLINE_PoleSmoothAxes","JSPLINE_RotateSmoothAxes","JSPLINE_TransformSmoothAxes"]
                originalAnimationLength = originalTimeEnd - originalTimeStart
                for axesType in range(len(axesTypes)):
                    for fcurve in range(len(sceneObjects[axesTypes[axesType]].animation_data.action.fcurves)):
                        animationFcurves = sceneObjects[axesTypes[axesType]].animation_data.action.fcurves[fcurve]
                        for keyframe in range(0,len(sceneObjects[axesTypes[axesType]].animation_data.action.fcurves[fcurve].keyframe_points)):
                            animationFcurves.keyframe_points[keyframe].co.x -= originalAnimationLength
                            animationFcurves.update()
            boneTranslateConstraint = targetBone.constraints.new('COPY_LOCATION')
            boneTranslateConstraint.target = sceneObjects["JSPLINE_TransformSmoothAxes"]
            boneTranslateConstraint.name = "JSPLINE_TranslateDelayEffect"
            boneTranslateConstraint.influence = translateInfluence
            boneRotateConstraint = targetBone.constraints.new('IK')
            boneRotateConstraint.chain_count = 1
            boneRotateConstraint.target = sceneObjects["JSPLINE_RotateSmoothAxes"]
            boneRotateConstraint.pole_target = sceneObjects["JSPLINE_PoleSmoothAxes"]
            boneRotateConstraint.name = "JSPLINE_RotateDelayEffect"
            boneRotateConstraint.influence = rotateInfluence
            sceneObjects["JSPLINE_TransformSmoothAxes"].name = "JSPLINE_" + targetArmature.name + "_" + targetBone.name + "_TransformEffect"
            sceneObjects["JSPLINE_RotateSmoothAxes"].name = "JSPLINE_" + targetArmature.name + "_" + targetBone.name + "_RotateEffect"
            sceneObjects["JSPLINE_PoleSmoothAxes"].name = "JSPLINE_" + targetArmature.name + "_" + targetBone.name + "_PoleEffect"
            #if the animation is looped, return the frame end to the original value
            if(loopedAnimation == True):
                context.scene.frame_end = originalTimeEnd
            #return to pose mode with the originally selected bones
            bpy.ops.object.select_all(action='DESELECT')
            targetArmature.select_set(True)
            context.view_layer.objects.active = targetArmature
            bpy.ops.object.posemode_toggle()
        #if it's a looping animation, reset the frame region to the original length
        if(loopedAnimation == True):
            context.scene.frame_start = originalTimeStart
            context.scene.frame_end = originalTimeEnd
        #go to edit mode to make selected bones not connected to enable translation effect
        bpy.ops.object.mode_set(mode='EDIT')
        for bone in range(len(context.selected_editable_bones)):
            targetEditBone = context.selected_editable_bones[bone]
            targetEditBone.use_connect = False
        bpy.ops.object.posemode_toggle()
        #turn off simplify after processing
        context.scene.render.use_simplify = False
        
        #return empty visibility to user set state after processing
        context.space_data.show_object_viewport_empty = originalEmptyVisibility
        
        return {'FINISHED'}

#button to remove the delay effect from the selected bone(s)
class JSPLINE_OT_RevertBone(bpy.types.Operator):
    bl_idname = "jspline.revertbone"
    bl_label = "Remove Delay From Selected Bone(s)"
    bl_description = "Remove the delay effect from the selected bone(s)."
            
    def execute(self, context):
        #make sure empties are enabled to avoid null error
        originalEmptyVisibility = context.space_data.show_object_viewport_empty
        context.space_data.show_object_viewport_empty = True
        
        #speed up processing by setting simplify
        context.scene.render.use_simplify = True
        context.scene.render.simplify_subdivision = 0
        sceneObjects = context.scene.objects
        #iterate through all selected bones
        for bone in range(len(context.selected_pose_bones)):
            #store the current selected bone in the iteration
            targetBone = context.selected_pose_bones[bone]
            #switch to object mode and remove all empties and constraints if they exist
            bpy.ops.object.mode_set(mode='OBJECT')
            #store the current selected armature
            targetArmature = context.view_layer.objects.active
            bpy.ops.object.select_all(action='DESELECT')
            if("JSPLINE_TranslateDelayEffect" in targetBone.constraints):
                targetBone.constraints.remove(targetBone.constraints["JSPLINE_TranslateDelayEffect"])
            if("JSPLINE_RotateDelayEffect" in targetBone.constraints):
                targetBone.constraints.remove(targetBone.constraints["JSPLINE_RotateDelayEffect"])
            transformSmoothName = "JSPLINE_" + targetArmature.name + "_" + targetBone.name + "_TransformEffect"
            rotateSmoothName = "JSPLINE_" + targetArmature.name + "_" + targetBone.name + "_RotateEffect"
            poleSmoothName = "JSPLINE_" + targetArmature.name + "_" + targetBone.name + "_PoleEffect"
            if(transformSmoothName in sceneObjects):
                sceneObjects[transformSmoothName].select_set(True)
            if(rotateSmoothName in sceneObjects):
                sceneObjects[rotateSmoothName].select_set(True)
            if(poleSmoothName in sceneObjects):
                sceneObjects[poleSmoothName].select_set(True)
            bpy.ops.object.delete()
            #return to pose mode with the originally selected bones
            bpy.ops.object.select_all(action='DESELECT')
            targetArmature.select_set(True)
            context.view_layer.objects.active = targetArmature
            bpy.ops.object.posemode_toggle()
        #turn off simplify after processing
        context.scene.render.use_simplify = False
        
        #return empty visibility to user set state after processing
        context.space_data.show_object_viewport_empty = originalEmptyVisibility
        
        return {'FINISHED'}
    
#button to keyframe the selected influence for the selected bone(s) at the current time
class JSPLINE_OT_KeyInfluence(bpy.types.Operator):
    bl_idname = "jspline.keyinfluence"
    bl_label = "Keyframe Influence For Selected Bone(s)"
    bl_description = "Keyframe the specified effect influence for the selected bone(s) at the current time."
    def execute(self, context):
        for bone in range(len(context.selected_pose_bones)):
            targetBone = context.selected_pose_bones[bone]
            if("JSPLINE_TranslateDelayEffect" in targetBone.constraints):
                targetBone.constraints["JSPLINE_TranslateDelayEffect"].influence = context.scene.JSPLINETranslateAmount
                targetBone.constraints["JSPLINE_TranslateDelayEffect"].keyframe_insert(data_path="influence",frame=context.scene.frame_current)
            if("JSPLINE_RotateDelayEffect" in targetBone.constraints):
                targetBone.constraints["JSPLINE_RotateDelayEffect"].influence = context.scene.JSPLINERotateAmount
                targetBone.constraints["JSPLINE_RotateDelayEffect"].keyframe_insert(data_path="influence",frame=context.scene.frame_current)
        return {'FINISHED'}
    
#button to keyframe no effect for the selected bone(s) at the current time
class JSPLINE_OT_KeyDisable(bpy.types.Operator):
    bl_idname = "jspline.keydisable"
    bl_label = "Keyframe No Effect For Selected Bone(s)"
    bl_description = "Insert a keyframe to disable the effect on the selected bone(s) at the current time."
    def execute(self, context):
        for bone in range(len(context.selected_pose_bones)):
            targetBone = context.selected_pose_bones[bone]
            if("JSPLINE_TranslateDelayEffect" in targetBone.constraints):
                targetBone.constraints["JSPLINE_TranslateDelayEffect"].influence = 0
                targetBone.constraints["JSPLINE_TranslateDelayEffect"].keyframe_insert(data_path="influence",frame=context.scene.frame_current)
            if("JSPLINE_RotateDelayEffect" in targetBone.constraints):
                targetBone.constraints["JSPLINE_RotateDelayEffect"].influence = 0
                targetBone.constraints["JSPLINE_RotateDelayEffect"].keyframe_insert(data_path="influence",frame=context.scene.frame_current)
        return {'FINISHED'}
    
#button to create looping animation influence envelope
class JSPLINE_OT_KeyInfluenceEnvelope(bpy.types.Operator):
    bl_idname = "jspline.keyenvelope"
    bl_label = "Keyframe Envelope For Selected Bone(s)"
    bl_description = "Create keyframes with no influence at the start and end of the timeline, with one or two full influence keys in between for looping animations. Uses the 'Looping Envelope Timeline Percent' to determine keyframe placement"
    def execute(self, context):
        envelopePercent = context.scene.JSPLINEEnvelopePercent / 100
        originalTimelinePosition = context.scene.frame_current
        timelineLength = context.scene.frame_end - context.scene.frame_start
        startEnvelopeKeyframe = context.scene.frame_start + math.ceil(timelineLength * envelopePercent)
        endEnvelopeKeyframe = context.scene.frame_end - math.ceil(timelineLength * envelopePercent)
        context.scene.frame_set(context.scene.frame_start)
        bpy.ops.jspline.keydisable()
        context.scene.frame_set(context.scene.frame_end)
        bpy.ops.jspline.keydisable()
        context.scene.frame_set(startEnvelopeKeyframe)
        bpy.ops.jspline.keyinfluence()
        context.scene.frame_set(endEnvelopeKeyframe)
        bpy.ops.jspline.keyinfluence()
        return {'FINISHED'}

#register and unregister all Jeane Spline classes
jsplineClasses = (  JSPLINE_PT_SpliningPanel,
                    JSPLINE_OT_ResetDefaults,
                    JSPLINE_OT_SmoothBone,
                    JSPLINE_OT_RevertBone,
                    JSPLINE_OT_KeyInfluence,
                    JSPLINE_OT_KeyDisable,
                    JSPLINE_OT_KeyInfluenceEnvelope)

register, unregister = bpy.utils.register_classes_factory(jsplineClasses)

#register this script for debugging
if __name__ == '__main__':
    register()
