# Empathy Blender Addon
# Copyright (C) 2019 Pierre
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
    "name": "Empathy",
    "author": "Pierre",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "description": "create editable motion paths using bezier curves and apply delay effects",
    "category": "Animation"
    }


#panel class for the empty motion path menu in object mode
class EMPATHY_PT_MenuPanel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = 'Delayed Motion Paths'
    bl_context = 'objectmode'
    bl_category = 'Empty Motion Path'
    bpy.types.Scene.EMPATHYCaptureInterval = bpy.props.IntProperty(name="Capture Interval",description="how many frames to wait between capturing a location for a bezier curve motion path",default=5,min=1)
    bpy.types.Scene.EMPATHYMinimumMovePointDistance = bpy.props.FloatProperty(name="Minimum Move Point Distance",description="the closest that two points can be in a movement bezier curve motion path",default=0.6,min=0)
    bpy.types.Scene.EMPATHYMinimumRotatePointDistance = bpy.props.FloatProperty(name="Minimum Rotate Point Distance",description="the closest that two points can be in a rotation bezier curve motion path",default=1.5,min=0)
    bpy.types.Scene.EMPATHYMinimumPolePointDistance = bpy.props.FloatProperty(name="Minimum Pole Point Distance",description="the closest that two points can be in a pole bezier curve motion path",default=1.5,min=0)
    bpy.types.Scene.EMPATHYLoopedAnimation = bpy.props.BoolProperty(name="Loop Motion Path",description="make bezier curve motion path cyclic before smoothing for looping animation",default=False)

    def draw(self, context):
        self.layout.prop(context.scene,"EMPATHYLoopedAnimation")
        self.layout.prop(context.scene,"EMPATHYCaptureInterval",slider=False)
        self.layout.prop(context.scene,"EMPATHYMinimumMovePointDistance",slider=False)
        self.layout.prop(context.scene,"EMPATHYMinimumRotatePointDistance",slider=False)
        self.layout.prop(context.scene,"EMPATHYMinimumPolePointDistance",slider=False)
        self.layout.operator('empathy.createobjectpaths', text ='Convert Motion Of Selected To Path') 
        self.layout.operator('empathy.clearobjectpaths', text ='Remove Paths Associated With Selected') 

#panel class for the empty motion path menu
class EMPATHY_PT_MenuPanelPose(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = 'Delayed Motion Paths'
    bl_context = 'posemode'
    bl_category = 'Empty Motion Path'
    
    def draw(self, context):
        self.layout.prop(context.scene,"EMPATHYLoopedAnimation")
        self.layout.prop(context.scene,"EMPATHYCaptureInterval",slider=False)
        self.layout.prop(context.scene,"EMPATHYMinimumMovePointDistance",slider=False)
        self.layout.prop(context.scene,"EMPATHYMinimumRotatePointDistance",slider=False)
        self.layout.prop(context.scene,"EMPATHYMinimumPolePointDistance",slider=False)
        self.layout.operator('empathy.createobjectpaths', text ='Convert Motion Of Selected To Path') 
        self.layout.operator('empathy.clearobjectpaths', text ='Remove Paths Associated With Selected') 

#button to create a motion path for the objects and attach the objects to the motion paths
class EMPATHY_OT_ClearPathsFromSelected(bpy.types.Operator):
    bl_idname = "empathy.clearobjectpaths"
    bl_label = "Clear motion paths from selected objects"
    bl_description = "Delete the bezier curves and empties which control the selected object"
    
    def execute(self, context):
        #objects to remove path components from
        
        #for bones
        objectsToClear = None
        isUsingBones = False
        activeArmature = None
        if(bpy.context.active_object.mode == 'POSE'):
            isUsingBones = True
            objectsToClear = context.selected_pose_bones_from_active_object
        else:
            objectsToClear = context.selected_objects
        
        #delete associated objects
        for pathedObject in objectsToClear:
            #for bones
            removableCollectionName = None
            if(isUsingBones):
                activeArmature = bpy.context.active_object
                bpy.ops.object.posemode_toggle()
                removableCollectionName = "EMPATHY_ARMATURECOMPONENTS_" + activeArmature.name + "_" + pathedObject.name
            else:
                removableCollectionName = "EMPATHY_COMPONENTS_" + pathedObject.name
            
            if(removableCollectionName in bpy.data.collections):
                targetObjectCollection = bpy.data.collections[removableCollectionName]
                bpy.ops.object.select_all(action='DESELECT')
                for markDeleteObject in targetObjectCollection.objects:
                    markDeleteObject.select_set(True)
                bpy.ops.object.delete(use_global = False, confirm = False)
                bpy.data.collections.remove(targetObjectCollection)
            for constraintToRemove in pathedObject.constraints:
                if("EMPATHY_" in constraintToRemove.name):
                    pathedObject.constraints.remove(constraintToRemove)
                    
        return {'FINISHED'}

#button to create a motion path for the objects and attach the objects to the motion paths
class EMPATHY_OT_CreateObjectPaths(bpy.types.Operator):
    bl_idname = "empathy.createobjectpaths"
    bl_label = "Attach objects to motion paths"
    bl_description = "Create bezier curves for the current objects and constrain the objects to move along the curves"

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
                
    def setupBezierCurve(self,context,curveName):
        bpy.ops.curve.primitive_bezier_curve_add(enter_editmode=True, location=(0,0,0))
        bpy.ops.curve.select_all(action='DESELECT')
        pathObject = bpy.context.object
        pathObject.name = curveName
        pathObject.data.splines[0].bezier_points[0].select_control_point = True
        pathObject.show_in_front = True
        bpy.ops.curve.delete(type='VERT')
        bpy.ops.curve.select_all(action='SELECT')
        return pathObject
    
    def computeCurveShape(self,context,captureInterval,minimumDistance,pathToEdit,pathingObject,loopAnimation):
        context.scene.frame_set(context.scene.frame_start)
        maxKeyFrameNumber = int((context.scene.frame_end - context.scene.frame_start) / captureInterval)
        for recordKeyFramePoint in range(0,maxKeyFrameNumber):
            if(recordKeyFramePoint == maxKeyFrameNumber):
                context.scene.frame_set(context.scene.frame_end)
            elif(recordKeyFramePoint != 0):
                context.scene.frame_set(context.scene.frame_current + captureInterval)
            pathToEdit.data.splines[0].bezier_points[0].co = pathingObject.matrix_world.translation
            if(recordKeyFramePoint != maxKeyFrameNumber):
                bpy.ops.curve.extrude()
                
        bpy.ops.curve.select_all(action='DESELECT')
        currentSpline = pathToEdit.data.splines[0]
        #minimum distance for points to need to exist
        pointDistanceMinimum = minimumDistance
        #iterate through curve points and delete points which are too close
        for curvePointNumber in range(len(currentSpline.bezier_points)):
            pointDistanceTooSmall = False
            if(curvePointNumber - 1 >= 0):
                previousPointDistance = currentSpline.bezier_points[curvePointNumber].co - currentSpline.bezier_points[curvePointNumber - 1].co
                distanceDifferenceValue = abs(previousPointDistance[0]) + abs(previousPointDistance[1]) + abs(previousPointDistance[2])
                if(distanceDifferenceValue < pointDistanceMinimum):
                    pointDistanceTooSmall = True
            if(curvePointNumber + 1 <= len(currentSpline.bezier_points)-1):
                nextPointDistance = currentSpline.bezier_points[curvePointNumber].co - currentSpline.bezier_points[curvePointNumber + 1].co
                distanceDifferenceValue = abs(nextPointDistance[0]) + abs(nextPointDistance[1]) + abs(nextPointDistance[2])
                if(distanceDifferenceValue < pointDistanceMinimum):
                    pointDistanceTooSmall = True
            #if the distance between points is too small, mark for deletion
            if(pointDistanceTooSmall == True and curvePointNumber != 0):
                currentSpline.bezier_points[curvePointNumber].select_control_point = True
                currentSpline.bezier_points[curvePointNumber].select_left_handle = True
                currentSpline.bezier_points[curvePointNumber].select_right_handle = True
        #delete points which are too close
        bpy.ops.curve.delete(type='VERT')

        #iterate through curve points and correct shape
        for curvePointNumber in range(len(currentSpline.bezier_points)):
            pointLocation = currentSpline.bezier_points[curvePointNumber].co
            currentSpline.bezier_points[curvePointNumber].handle_right = (pointLocation[0]+0.1,pointLocation[1],pointLocation[2])
            currentSpline.bezier_points[curvePointNumber].handle_left = (pointLocation[0]-0.1,pointLocation[1],pointLocation[2])
            bpy.ops.curve.select_all(action='DESELECT')
            currentSpline.bezier_points[curvePointNumber].select_control_point = True
            currentSpline.bezier_points[curvePointNumber].select_left_handle = True
            currentSpline.bezier_points[curvePointNumber].select_right_handle = True
            if(curvePointNumber - 1 >= 0 and curvePointNumber + 1 <= len(currentSpline.bezier_points)-1):
                middlePointDistance = currentSpline.bezier_points[curvePointNumber-1].co - currentSpline.bezier_points[curvePointNumber+1].co
                middlePointDistanceValue = (abs(middlePointDistance[0]) + abs(middlePointDistance[1]) + abs(middlePointDistance[2]))
                bpy.ops.transform.resize(value=(1+middlePointDistanceValue,1+middlePointDistanceValue,1+middlePointDistanceValue))
        #fix normals and apply loop if required
        bpy.ops.curve.select_all(action='SELECT')
        if(loopAnimation == True):
            bpy.ops.curve.cyclic_toggle()
        bpy.ops.curve.normals_make_consistent()
        bpy.ops.object.editmode_toggle()
                
    def execute(self, context):
        #currently selected objects which paths need to be made for
        objectsForPaths = None
        #menu properties for creating the motion paths
        captureInterval = context.scene.EMPATHYCaptureInterval
        minimumMoveDistance = context.scene.EMPATHYMinimumMovePointDistance
        minimumRotateDistance = context.scene.EMPATHYMinimumRotatePointDistance
        minimumPoleDistance = context.scene.EMPATHYMinimumPolePointDistance
        loopAnimation = context.scene.EMPATHYLoopedAnimation
        #save menu modes to restore after processing
        originalKeyframeInsertState = context.scene.tool_settings.use_keyframe_insert_auto
        originalKeyframePosition = context.scene.frame_current
        
        #for bones
        isUsingBones = False
        activeArmature = None
        if(bpy.context.active_object.mode == 'POSE'):
            isUsingBones = True
            objectsForPaths = context.selected_pose_bones_from_active_object
        else:
            objectsForPaths = context.selected_objects
        
        #clear any existing path objects
        #bpy.ops.empathy.clearobjectpaths()
        
        #for bones
        if(isUsingBones):
            activeArmature = bpy.context.active_object
            bpy.ops.object.editmode_toggle()
            for disconnectingBone in context.selected_editable_bones:
                disconnectingBone.use_connect = False
            bpy.ops.object.editmode_toggle()
        
        #step through all selected objects and assign to motion paths
        for pathingObject in objectsForPaths: #may be bones or objects
            bpy.ops.object.select_all(action='DESELECT')
            
            #for bones
            if(isUsingBones):
                objectCollectionName = "EMPATHY_ARMATURECOMPONENTS_" + activeArmature.name + "_" + pathingObject.name
            else:
                objectCollectionName = "EMPATHY_COMPONENTS_" + pathingObject.name
            
            rotateEmptyName = "EMPATHY_ROTATEEMPTY_" + pathingObject.name
            poleEmptyName = "EMPATHY_POLEEMPTY_" + pathingObject.name
            moveEmptyName = "EMPATHY_MOVEEMPTY_" + pathingObject.name
            
            copyLocationConstraintName = "EMPATHY_MOVECONSTRAINT"
            cancelRotationConstraintName = "EMPATHY_ROTATECANCELCONSTRAINT"
            followPathConstraintName = "EMPATHY_PATHCONSTRAINT"
            rotateZTrackConstraintName = "EMPATHY_ROTATEZTRACKCONSTRAINT"
            rotateXTrackConstraintName = "EMPATHY_ROTATEXTRACKCONSTRAINT"
            poleTrackConstraintName = "EMPATHY_POLETRACKCONSTRAINT"

            poleTrackConstraintName = "EMPATHY_POLETRACKCONSTRAINT"
            
            movePathName = "EMPATHY_MOVEPATH_" +  str(pathingObject.name)
            rotatePathName = "EMPATHY_ROTATEPATH_" +  str(pathingObject.name)
            polePathName = "EMPATHY_POLEPATH_" +  str(pathingObject.name)
            
            #create collection to hold path components for this object
            self.setupCollection(context,objectCollectionName)
            
            #add empty to track the rotation
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,0,20))
            objectRotateEmpty = bpy.context.object
            objectRotateEmpty.name = rotateEmptyName
            
            #for bones
            if(isUsingBones):
                objectRotateEmpty.parent = activeArmature
                objectRotateEmpty.parent_type = 'BONE'
                objectRotateEmpty.parent_bone = pathingObject.name
            else:
                objectRotateEmpty.parent = pathingObject
                
            objectRotateEmpty.show_in_front = True
            self.assignToCollection(context,objectCollectionName,objectRotateEmpty)
            
            #add empty to track the pole
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,20,0))
            objectPoleEmpty = bpy.context.object
            objectPoleEmpty.name = poleEmptyName
            
            #for bones
            if(isUsingBones):
                objectPoleEmpty.parent = activeArmature
                objectPoleEmpty.parent_type = 'BONE'
                objectPoleEmpty.parent_bone = pathingObject.name
            else:
                objectPoleEmpty.parent = pathingObject
                
            objectPoleEmpty.show_in_front = True
            self.assignToCollection(context,objectCollectionName,objectPoleEmpty)
            
            #create empty for target object to follow along path
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,0,0))
            objectMoveEmpty = bpy.context.object
            objectMoveEmpty.name = moveEmptyName
            
            #for bones
            if(isUsingBones):
                objectMoveEmpty.parent = activeArmature
                objectMoveEmpty.parent_type = 'BONE'
                objectMoveEmpty.parent_bone = pathingObject.name
            else:
                objectMoveEmpty.parent = pathingObject
                
            objectMoveEmpty.show_in_front = True
            self.assignToCollection(context,objectCollectionName,objectMoveEmpty)
            
            #create and compute paths
            objectMovePath = self.setupBezierCurve(context,movePathName)
            self.computeCurveShape(context,captureInterval,minimumMoveDistance,objectMovePath,objectMoveEmpty,loopAnimation)
            self.assignToCollection(context,objectCollectionName,objectMovePath)
            
            objectRotatePath = self.setupBezierCurve(context,rotatePathName)
            self.computeCurveShape(context,captureInterval,minimumRotateDistance,objectRotatePath,objectRotateEmpty,loopAnimation)
            self.assignToCollection(context,objectCollectionName,objectRotatePath)
            
            objectPolePath = self.setupBezierCurve(context,polePathName)
            self.computeCurveShape(context,captureInterval,minimumPoleDistance,objectPolePath,objectPoleEmpty,loopAnimation)
            self.assignToCollection(context,objectCollectionName,objectPolePath)
            
            #enable rotation tracking on object
            objectRotateEmpty.parent = None
            objectRotateEmpty.location = (0,0,0)
            rotatePathConstraint = objectRotateEmpty.constraints.new(type='FOLLOW_PATH')
            rotatePathConstraint.name = followPathConstraintName
            rotatePathConstraint.target = objectRotatePath
            rotatePathConstraint.use_fixed_location = True
            
            #enable pole tracking on object
            objectPoleEmpty.parent = None
            objectPoleEmpty.location = (0,0,0)
            polePathConstraint = objectPoleEmpty.constraints.new(type='FOLLOW_PATH')
            polePathConstraint.name = followPathConstraintName
            polePathConstraint.target = objectPolePath
            polePathConstraint.use_fixed_location = True
            
            #motion tracking along path
            objectMoveEmpty.parent = None
            objectMoveEmpty.location = (0,0,0)
            movePathConstraint = objectMoveEmpty.constraints.new(type='FOLLOW_PATH')
            movePathConstraint.name = followPathConstraintName
            movePathConstraint.target = objectMovePath
            movePathConstraint.use_fixed_location = True
            
            #prevent object rotating as a result of the original motion
            cancelRotationConstraint = pathingObject.constraints.new(type='COPY_ROTATION')
            cancelRotationConstraint.name = cancelRotationConstraintName
            cancelRotationConstraint.target = objectMoveEmpty
            
            #constrain object to movement empty
            copyMoveLocationConstraint = pathingObject.constraints.new(type='COPY_LOCATION')
            copyMoveLocationConstraint.name = copyLocationConstraintName
            copyMoveLocationConstraint.target = objectMoveEmpty
            
            #create tracking constraints with pole to follow rotation empties
            rotateZTrackConstraint = pathingObject.constraints.new(type='LOCKED_TRACK')
            rotateZTrackConstraint.name = rotateZTrackConstraintName
            rotateZTrackConstraint.target = objectRotateEmpty
            rotateZTrackConstraint.track_axis = 'TRACK_Y'
            rotateZTrackConstraint.lock_axis = 'LOCK_Z'
            
            rotateXTrackConstraint = pathingObject.constraints.new(type='LOCKED_TRACK')
            rotateXTrackConstraint.name = rotateXTrackConstraintName
            rotateXTrackConstraint.target = objectRotateEmpty
            rotateXTrackConstraint.track_axis = 'TRACK_Y'
            rotateXTrackConstraint.lock_axis = 'LOCK_X'
            
            poleTrackConstraint = pathingObject.constraints.new(type='LOCKED_TRACK')
            poleTrackConstraint.name = poleTrackConstraintName
            poleTrackConstraint.target = objectPoleEmpty
            poleTrackConstraint.track_axis = 'TRACK_X'
            poleTrackConstraint.lock_axis = 'LOCK_Y'
            
            #put path empties in a list for iterating through the creation and adjustment of path follow keyframes
            controlEmptyList = [objectRotateEmpty,objectMoveEmpty,objectPoleEmpty]
            
            for controlEmptyType in controlEmptyList:
                #create motion keyframes
                context.scene.frame_set(context.scene.frame_start)
                controlEmptyType.constraints[followPathConstraintName].offset_factor = 1
                controlEmptyType.constraints[followPathConstraintName].keyframe_insert(data_path = 'offset_factor')
                if(loopAnimation == True):
                    context.scene.frame_set(context.scene.frame_end + 1)
                else:
                    context.scene.frame_set(context.scene.frame_end)
                controlEmptyType.constraints[followPathConstraintName].offset_factor = 0
                controlEmptyType.constraints[followPathConstraintName].keyframe_insert(data_path = 'offset_factor')
                
                #pinch handles on keyframes to make start and end points behave linear
                for keyframePointNumber in range(0,2):
                    controlEmptyType.animation_data.action.fcurves[0].keyframe_points[keyframePointNumber].handle_left_type = 'FREE'
                    controlEmptyType.animation_data.action.fcurves[0].keyframe_points[keyframePointNumber].handle_right_type = 'FREE'
                    controlEmptyType.animation_data.action.fcurves[0].keyframe_points[keyframePointNumber].handle_left = controlEmptyType.animation_data.action.fcurves[0].keyframe_points[keyframePointNumber].co
                    controlEmptyType.animation_data.action.fcurves[0].keyframe_points[keyframePointNumber].handle_right = controlEmptyType.animation_data.action.fcurves[0].keyframe_points[keyframePointNumber].co
                    
        context.scene.tool_settings.use_keyframe_insert_auto = originalKeyframeInsertState
        context.scene.frame_set(originalKeyframePosition)
        
        return {'FINISHED'}

#register and unregister all Empathy classes
empathyClasses = (  EMPATHY_PT_MenuPanel,
                    EMPATHY_PT_MenuPanelPose,
                    EMPATHY_OT_CreateObjectPaths,
                    EMPATHY_OT_ClearPathsFromSelected)

register, unregister = bpy.utils.register_classes_factory(empathyClasses)

#register this script for debugging
if __name__ == '__main__':
    register()
