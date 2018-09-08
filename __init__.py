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
    "version": (1, 0, 7),
    "blender": (2, 7, 9),
    "description": "Rotation & translation delay effect for armature animation.",
    "category": "Animation"
    }
    
#panel class for delay effect related menu items
class JSPLINE_SpliningPanel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = 'Jeane Spline Effect'
    bl_context = 'posemode'
    bl_category = 'Jeane Spline'

    bpy.types.Scene.JSPLINERotateAmount = bpy.props.FloatProperty(name="Effect Rotation Influence",description="The influence that the rotation delay effect will have on the selected bone",default=1,min=0,max=1)
    bpy.types.Scene.JSPLINETranslateAmount = bpy.props.FloatProperty(name="Effect Translation Influence",description="The influence that the translation delay effect will have on the selected bone",default=0.3,min=0,max=1)
    bpy.types.Scene.JSPLINENoiseAmplitude = bpy.props.FloatProperty(name="Effect Noise Amplitude",description="The amount of rotation and translation noise that will be added to the selected bone",default=0.1,min=0,max=5)
    bpy.types.Scene.JSPLINEPopulateInterval = bpy.props.IntProperty(name="Populate Keyframes Interval",description="The interval between Jeane Spline keyframes when populating the timeline with keyframes for the selected bone at a regular interval. Can be negative to populate backwards",default=3)
    bpy.types.Scene.JSPLINERotationDelay = bpy.props.IntProperty(name="Rotation Delay Add",description="The number of additional keyframes to offset rotation by",default=2)
    bpy.types.Scene.JSPLINETranslationDelay = bpy.props.IntProperty(name="Translation Delay Add",description="The number of additional keyframes to offset translation by",default=1)

    def draw(self, context):
        self.layout.prop(context.scene,"JSPLINERotateAmount",slider=True)
        self.layout.prop(context.scene,"JSPLINETranslateAmount",slider=True)
        self.layout.prop(context.scene,"JSPLINENoiseAmplitude",slider=True)
        self.layout.prop(context.scene,"JSPLINERotationDelay")
        self.layout.prop(context.scene,"JSPLINETranslationDelay")
        self.layout.operator('jspline.smoothbone', text ='Create Keyframe')
        self.layout.operator('jspline.keyframeinfluence', text ='Create Influence Keyframe')
        self.layout.operator('jspline.clearbone', text ='Clear Effect On Selected')
        self.layout.operator('jspline.mutebone', text ='Mute Effect On Selected')
        self.layout.operator('jspline.unmutebone', text ='Unmute Effect On Selected')
        self.layout.operator('jspline.hideempties', text ='Hide All Empties')
        self.layout.operator('jspline.unhideempties', text ='Unhide All Empties')
        self.layout.operator('jspline.selectassociatedempties', text ='Select Associated Empties')
        self.layout.prop(context.scene,"JSPLINEPopulateInterval")
        self.layout.operator('jspline.populatetimeline', text ='Populate Timeline With Keyframes')
   
#button to keyframe the influence of the selected bones at the current time without recreating the Jeane Spline keyframe
class JSPLINEKeyframeInfluence(bpy.types.Operator):
    bl_idname = "jspline.keyframeinfluence"
    bl_label = "Keyframe Influence for Selected Bones"
    bl_description = "Create a keyframe at the current time applying the influences specified in the Jeane Spline menu to the selected bones"
    
    def execute(self, context):
        sceneObjects = bpy.context.scene.objects
        for targetBone in bpy.context.selected_pose_bones:
            if("JSPLINE_TranslateDelayEffect" in targetBone.constraints):
                boneTranslateConstraint = targetBone.constraints["JSPLINE_TranslateDelayEffect"]
                boneTranslateConstraint.influence = bpy.context.scene.JSPLINETranslateAmount
                boneTranslateConstraint.keyframe_insert(data_path="influence",frame=bpy.context.scene.frame_current)
            if("JSPLINE_RotateDelayEffect" in targetBone.constraints):
                boneRotateConstraint = targetBone.constraints["JSPLINE_RotateDelayEffect"]
                boneRotateConstraint.influence = bpy.context.scene.JSPLINERotateAmount
                boneRotateConstraint.keyframe_insert(data_path="influence",frame=bpy.context.scene.frame_current)
        return {'FINISHED'}        

#button to create Jeane Spline keyframes at a regular interval to populate the timeline
class JSPLINEPopulateTimeline(bpy.types.Operator):
    bl_idname = "jspline.populatetimeline"
    bl_label = "Populate Timeline With Keyframes"
    bl_description = "Create Jeane Spline keyframes at a regular interval"
    
    def execute(self, context):
        bpy.ops.jspline.smoothbone()
        originalCurrentFrame = bpy.context.scene.frame_current
        if(abs(bpy.context.scene.JSPLINEPopulateInterval) < 2):
            if(bpy.context.scene.JSPLINEPopulateInterval >= 0):
                bpy.context.scene.JSPLINEPopulateInterval = 2
            elif(bpy.context.scene.JSPLINEPopulateInterval < 0):
                bpy.context.scene.JSPLINEPopulateInterval = -2
        while (bpy.context.scene.frame_current + bpy.context.scene.JSPLINEPopulateInterval >= bpy.context.scene.frame_start) and (bpy.context.scene.frame_current + bpy.context.scene.JSPLINEPopulateInterval <= bpy.context.scene.frame_end):
            bpy.ops.jspline.smoothbone()
            bpy.context.scene.frame_set(bpy.context.scene.frame_current + bpy.context.scene.JSPLINEPopulateInterval)
        bpy.context.scene.frame_set(originalCurrentFrame)
        return {'FINISHED'}        

#button to hide Jeane Spline empties
class JSPLINEHideEmpties(bpy.types.Operator):
    bl_idname = "jspline.hideempties"
    bl_label = "Hide Jeane Spline empties"
    bl_description = "Hide the empties used to create the Jeane Spline effect"
   
    def execute(self, context):
        sceneObjects = bpy.context.scene.objects
        for sceneObject in sceneObjects:
            if('JSPLINE,' in sceneObject.name):
                sceneObject.hide = True
        bpy.context.scene.frame_set(bpy.context.scene.frame_current)
        return {'FINISHED'}
    
#button to hide Jeane Spline empties
class JSPLINEUnhideEmpties(bpy.types.Operator):
    bl_idname = "jspline.unhideempties"
    bl_label = "Unhide Jeane Spline empties"
    bl_description = "Unhide the empties used to create the Jeane Spline effect"
   
    def execute(self, context):
        sceneObjects = bpy.context.scene.objects
        for sceneObject in sceneObjects:
            if('JSPLINE,' in sceneObject.name):
                sceneObject.hide = False
        bpy.context.scene.frame_set(bpy.context.scene.frame_current)
        return {'FINISHED'}
    
#button to select associated Jeane Spline empties
class JSPLINESelectAssociated(bpy.types.Operator):
    bl_idname = "jspline.selectassociatedempties"
    bl_label = "Select associated Jeane Spline empties"
    bl_description = "Select all Jeane Spline empties associated with the selected bone"
   
    def execute(self, context):
        targetBone = bpy.context.selected_pose_bones[0]
        sceneObjects = bpy.context.scene.objects
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        for sceneObject in sceneObjects:
            if('JSPLINE,' in sceneObject.name and targetBone.name in sceneObject.name):
                sceneObject.select = True
        return {'FINISHED'}
       
#button to mute Jeane Spline effect on selected bones
class JSPLINEMuteBone(bpy.types.Operator):
    bl_idname = "jspline.mutebone"
    bl_label = "Mute Jeane Spline effect on selected"
    bl_description = "Mute Jeane Spline constraints on the selected bones"
   
    def execute(self, context):
        for targetBone in bpy.context.selected_pose_bones:
            for constraintInstance in targetBone.constraints:
                if('JSPLINE_' in constraintInstance.name):
                    targetBone.constraints[constraintInstance.name].mute = True
        bpy.context.scene.frame_set(bpy.context.scene.frame_current)
        return {'FINISHED'}
    
#button to unmute Jeane Spline effect on selected bones
class JSPLINEUnmuteBone(bpy.types.Operator):
    bl_idname = "jspline.unmutebone"
    bl_label = "Unmute Jeane Spline effect on selected"
    bl_description = "Unmute Jeane Spline constraints on the selected bones"
   
    def execute(self, context):
        for targetBone in bpy.context.selected_pose_bones:
            for constraintInstance in targetBone.constraints:
                if('JSPLINE_' in constraintInstance.name):
                    targetBone.constraints[constraintInstance.name].mute = False
        bpy.context.scene.frame_set(bpy.context.scene.frame_current)
        return {'FINISHED'}

#button to remove jeane spline effect from selected bones
class JSPLINEClearBone(bpy.types.Operator):
    bl_idname = "jspline.clearbone"
    bl_label = "Clear Jeane Spline effect from selected"
    bl_description = "Delete all Jeane Spline constraints and keyframes from the selected bones"
   
    def selectAndActivate(self,sceneObjects,selectObject):
        bpy.ops.object.select_all(action='DESELECT')
        selectObject.select = True
        bpy.context.scene.objects.active = selectObject
   
    def execute(self, context):
        sceneObjects = bpy.context.scene.objects
        for targetBone in bpy.context.selected_pose_bones:
            for constraintInstance in targetBone.constraints:
                if('JSPLINE_' in constraintInstance.name):
                    targetBone.constraints.remove(targetBone.constraints[constraintInstance.name])
                bpy.ops.object.mode_set(mode='OBJECT')
                targetArmature = bpy.context.object
                armatureFcurves = targetArmature.animation_data.action.fcurves
                for targetFcurve in armatureFcurves:
                    if("influence" in targetFcurve.data_path and "JSPLINE_" in targetFcurve.data_path and targetBone.name in targetFcurve.data_path):
                        armatureFcurves.remove(targetFcurve)
                bpy.ops.object.select_all(action='DESELECT')
                emptyNameTypes = [",RotateEffect",",TranslateEffect",",PoleEffect"]
                for emptyName in range(len(emptyNameTypes)):
                    emptyNameTypes[emptyName] = "JSPLINE," + targetArmature.name + "," + targetBone.name + emptyNameTypes[emptyName]
                    if(emptyNameTypes[emptyName] in sceneObjects):
                        sceneObjects[emptyNameTypes[emptyName]].select = True
                bpy.ops.object.delete(use_global=False)
                self.selectAndActivate(sceneObjects,targetArmature)
                bpy.ops.object.mode_set(mode='POSE')
        return {'FINISHED'}

#button to apply the delay effect to all bones
class JSPLINESmoothBone(bpy.types.Operator):
    bl_idname = "jspline.smoothbone"
    bl_label = "Create Jeane Spline keyframe"
    bl_description = "Create a Jeane Spline keyframe at the current time for the first bone in the currently selected bones"

    def selectAndActivate(self,sceneObjects,selectObject):
        bpy.ops.object.select_all(action='DESELECT')
        selectObject.select = True
        bpy.context.scene.objects.active = selectObject
        
    def createNamedEmpty(self,sceneObjects,emptyName):
        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        bpy.context.object.name = emptyName
        
    def positionOnBoneLocation(self,sceneObjects,targetEmpty,targetArmature,targetBone,desiredLocation,originalCurrentFrame):
            targetEmpty.parent = targetArmature
            targetEmpty.parent_type = 'BONE'
            targetEmpty.parent_bone = targetBone.name
            targetEmpty.location = desiredLocation
            self.selectAndActivate(sceneObjects,targetEmpty)
            bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
            for fcurve in range(0,3):
                if(targetEmpty.name.find(",TranslateEffect") != -1): #translate
                    frameInsertPosition = bpy.context.scene.frame_current+fcurve+bpy.context.scene.JSPLINETranslationDelay
                elif(targetEmpty.name.find(",PoleEffect") != -1): 
                    frameInsertPosition = (bpy.context.scene.frame_current-1)+fcurve+bpy.context.scene.JSPLINERotationDelay
                else:
                    frameInsertPosition = ((bpy.context.scene.frame_current)+fcurve*1)+bpy.context.scene.JSPLINERotationDelay
                targetEmpty.keyframe_insert(data_path="location",index=fcurve,frame=frameInsertPosition)
                animationFcurves = targetEmpty.animation_data.action.fcurves[fcurve]
                if(len(animationFcurves.modifiers) == 0):
                    fcurvesNoise = animationFcurves.modifiers.new(type='NOISE')
                    fcurvesNoise.blend_type = "REPLACE"
                    fcurvesNoise.scale = random.randint(15,20)
                    fcurvesNoise.strength = bpy.context.scene.JSPLINENoiseAmplitude
                    fcurvesNoise.phase = random.randint(1,100)
                    fcurvesNoise.offset = random.randint(1,30)
                else:
                    fcurvesNoise = animationFcurves.modifiers[0]
                    fcurvesNoise.strength = bpy.context.scene.JSPLINENoiseAmplitude
                    
                    
    def addBoneConstraints(self,sceneObjects,targetBone,rotateEmptyObject,translateEmptyObject,poleEmptyObject):
        if("JSPLINE_TranslateDelayEffect" not in targetBone.constraints):
            boneTranslateConstraint = targetBone.constraints.new('COPY_LOCATION')
            boneTranslateConstraint.target = translateEmptyObject
            boneTranslateConstraint.name = "JSPLINE_TranslateDelayEffect"
            boneTranslateConstraint.influence = bpy.context.scene.JSPLINETranslateAmount
            boneTranslateConstraint.keyframe_insert(data_path="influence",frame=bpy.context.scene.frame_current)
        else:
            boneTranslateConstraint = targetBone.constraints["JSPLINE_TranslateDelayEffect"]
            boneTranslateConstraint.influence = bpy.context.scene.JSPLINETranslateAmount
            boneTranslateConstraint.keyframe_insert(data_path="influence",frame=bpy.context.scene.frame_current)
        if("JSPLINE_RotateDelayEffect" not in targetBone.constraints):
            boneRotateConstraint = targetBone.constraints.new('IK')
            boneRotateConstraint.chain_count = 1
            boneRotateConstraint.target = rotateEmptyObject
            boneRotateConstraint.pole_target = poleEmptyObject
            boneRotateConstraint.name = "JSPLINE_RotateDelayEffect"
            boneRotateConstraint.influence = bpy.context.scene.JSPLINERotateAmount
            boneRotateConstraint.keyframe_insert(data_path="influence",frame=bpy.context.scene.frame_current)
        else:
            boneRotateConstraint = targetBone.constraints["JSPLINE_RotateDelayEffect"]
            boneRotateConstraint.influence = bpy.context.scene.JSPLINERotateAmount
            boneRotateConstraint.keyframe_insert(data_path="influence",frame=bpy.context.scene.frame_current)
        
    def muteConstraints(self,muteConstraint,targetBone):
        for constraintInstance in targetBone.constraints:
            targetBone.constraints[constraintInstance.name].mute = muteConstraint

    def applyEffect(self):
        sceneObjects = bpy.context.scene.objects
        targetBone = bpy.context.selected_pose_bones[0]
        originalCurrentFrame = bpy.context.scene.frame_current
        bpy.ops.object.mode_set(mode='OBJECT')
        targetArmature = bpy.context.object
        emptyNameTypes = [",RotateEffect",",TranslateEffect",",PoleEffect"]
        for emptyName in range(len(emptyNameTypes)):
            emptyNameTypes[emptyName] = "JSPLINE," + targetArmature.name + "," + targetBone.name + emptyNameTypes[emptyName]
            if(not emptyNameTypes[emptyName] in sceneObjects):
                self.createNamedEmpty(sceneObjects,emptyNameTypes[emptyName])
        delayEmptyObjects = [sceneObjects[emptyNameTypes[0]],sceneObjects[emptyNameTypes[1]],sceneObjects[emptyNameTypes[2]]]
        self.muteConstraints(True,targetBone)
        self.positionOnBoneLocation(sceneObjects,delayEmptyObjects[0],targetArmature,targetBone,[0,targetBone.length*20,0],originalCurrentFrame) #rotate
        self.positionOnBoneLocation(sceneObjects,delayEmptyObjects[1],targetArmature,targetBone,[0,-targetBone.length,0],originalCurrentFrame) #translate
        self.positionOnBoneLocation(sceneObjects,delayEmptyObjects[2],targetArmature,targetBone,[targetBone.length*5,0,0],originalCurrentFrame) #pole
        self.addBoneConstraints(sceneObjects,targetBone,delayEmptyObjects[0],delayEmptyObjects[1],delayEmptyObjects[2]) #rotate, translate, pole
        self.muteConstraints(False,targetBone)
        self.selectAndActivate(sceneObjects,targetArmature)
        bpy.ops.object.mode_set(mode='POSE')
        
    def execute(self, context):
        self.applyEffect()
        return {'FINISHED'}

#register all Jeane Spline classes when Jeane Spline is loaded
def register():
    bpy.utils.register_class(JSPLINE_SpliningPanel)
    bpy.utils.register_class(JSPLINESmoothBone)
    bpy.utils.register_class(JSPLINEClearBone)
    bpy.utils.register_class(JSPLINEMuteBone)
    bpy.utils.register_class(JSPLINEUnmuteBone)
    bpy.utils.register_class(JSPLINEHideEmpties)
    bpy.utils.register_class(JSPLINEUnhideEmpties)
    bpy.utils.register_class(JSPLINEPopulateTimeline)
    bpy.utils.register_class(JSPLINESelectAssociated)
    bpy.utils.register_class(JSPLINEKeyframeInfluence)
#unregister all Jeane Spline classes when Jeane Spline is removed
def unregister():
    bpy.utils.unregister_class(JSPLINE_SpliningPanel)
    bpy.utils.unregister_class(JSPLINESmoothBone)
    bpy.utils.unregister_class(JSPLINEClearBone)
    bpy.utils.unregister_class(JSPLINEMuteBone)
    bpy.utils.unregister_class(JSPLINEUnmuteBone)
    bpy.utils.unregister_class(JSPLINEHideEmpties)
    bpy.utils.unregister_class(JSPLINEUnhideEmpties)
    bpy.utils.unregister_class(JSPLINEPopulateTimeline)
    bpy.utils.unregister_class(JSPLINESelectAssociated)
    bpy.utils.unregister_class(JSPLINEKeyframeInfluence)
#allow debugging for this addon in the Blender text editor
if __name__ == '__main__':
    register()
