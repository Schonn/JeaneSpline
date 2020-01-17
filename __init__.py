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
    "version": (1, 0, 1),
    "blender": (2, 80, 0),
    "description": "create editable motion paths using curves and apply delay effects",
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
    bpy.types.Scene.EMPATHYMinimumMovePointDistance = bpy.props.FloatProperty(name="Minimum Move Point Distance",description="the closest that two points can be in a movement bezier curve motion path",default=0.2,min=0)
    bpy.types.Scene.EMPATHYMinimumRotatePointDistance = bpy.props.FloatProperty(name="Minimum Rotate Point Distance",description="the closest that two points can be in a rotation bezier curve motion path",default=0.2,min=0)
    bpy.types.Scene.EMPATHYMinimumPolePointDistance = bpy.props.FloatProperty(name="Minimum Pole Point Distance",description="the closest that two points can be in a pole bezier curve motion path",default=0.2,min=0)
    bpy.types.Scene.EMPATHYLoopedAnimation = bpy.props.BoolProperty(name="Loop Motion Path",description="make bezier curve motion path cyclic before smoothing for looping animation",default=False)

    def draw(self, context):
        self.layout.prop(context.scene,"EMPATHYLoopedAnimation")
        self.layout.prop(context.scene,"EMPATHYCaptureInterval",slider=False)
        self.layout.prop(context.scene,"EMPATHYMinimumMovePointDistance",slider=False)
        self.layout.prop(context.scene,"EMPATHYMinimumRotatePointDistance",slider=False)
        self.layout.prop(context.scene,"EMPATHYMinimumPolePointDistance",slider=False)
        self.layout.operator('empathy.placecurvemarker', text ='Place Curve Split Marker At Current Time') 
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
        self.layout.operator('empathy.placecurvemarker', text ='Place Curve Split Marker At Current Time') 
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
        if(context.active_object.mode == 'POSE'):
            isUsingBones = True
            objectsToClear = context.selected_pose_bones_from_active_object
        else:
            objectsToClear = context.selected_objects
        
        #delete associated objects
        for pathedObject in objectsToClear:
            #for bones
            removableCollectionName = None
            if(isUsingBones):
                activeArmature = context.active_object
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
                context.scene.collection.children.link(bpy.data.collections[newCollectionName])
            else:
                bpy.data.collections[context.collection.name].children.link(bpy.data.collections[newCollectionName])

    def assignToCollection(self,context,assignCollectionName,assignObject):
        if(assignObject.name not in bpy.data.collections[assignCollectionName].objects):
            bpy.data.collections[assignCollectionName].objects.link(assignObject)
            if(context.collection.name == "Master Collection"):
                context.scene.collection.objects.unlink(assignObject)
            else:
                bpy.data.collections[context.collection.name].objects.unlink(assignObject)
                
    def setupBezierCurve(self,context,curveName):
        bpy.ops.curve.primitive_nurbs_curve_add(enter_editmode=True, location=(0,0,0))
        pathObject = context.object
        pathObject.name = curveName
        pathObject.data.splines[0].points[0].select = False
        pathObject.show_in_front = True
        bpy.ops.curve.delete(type='VERT')
        bpy.ops.curve.select_all(action='SELECT')
        return pathObject
    
    def computeCurveShape(self,context,captureInterval,minimumDistance,pathToEdit,pathingObject,loopAnimation):
        print("computing curve shape for" + pathingObject.name)
        context.scene.frame_set(context.scene.frame_start)
        maxKeyFrameNumber = int((context.scene.frame_end - context.scene.frame_start) / captureInterval)
        if(maxKeyFrameNumber < 1):
            maxKeyFrameNumber = 1
        print("max key frame number is " + str(maxKeyFrameNumber))
        for recordKeyFramePoint in range(0,maxKeyFrameNumber):
            if(recordKeyFramePoint == maxKeyFrameNumber):
                context.scene.frame_set(context.scene.frame_end)
            elif(recordKeyFramePoint != 0):
                context.scene.frame_set(context.scene.frame_current + captureInterval)
            pathToEdit.data.splines[0].points[0].co.xyz = pathingObject.matrix_world.translation
            print("setting path point" + str(pathingObject.matrix_world.translation))
            if(recordKeyFramePoint != maxKeyFrameNumber):
                bpy.ops.curve.extrude()
                
        bpy.ops.curve.select_all(action='DESELECT')
        currentSpline = pathToEdit.data.splines[0]
        #minimum distance for points to need to exist
        pointDistanceMinimum = minimumDistance
        #iterate through curve points and delete points which are too close
        for curvePointNumber in range(len(currentSpline.points)):
            pointDistanceTooSmall = False
            if(curvePointNumber - 1 >= 0):
                previousPointDistance = currentSpline.points[curvePointNumber].co.xyz - currentSpline.points[curvePointNumber - 1].co.xyz
                distanceDifferenceValue = abs(previousPointDistance[0]) + abs(previousPointDistance[1]) + abs(previousPointDistance[2])
                if(distanceDifferenceValue < pointDistanceMinimum):
                    pointDistanceTooSmall = True
            if(curvePointNumber + 1 <= len(currentSpline.points)-1):
                nextPointDistance = currentSpline.points[curvePointNumber].co.xyz - currentSpline.points[curvePointNumber + 1].co.xyz
                distanceDifferenceValue = abs(nextPointDistance[0]) + abs(nextPointDistance[1]) + abs(nextPointDistance[2])
                if(distanceDifferenceValue < pointDistanceMinimum):
                    pointDistanceTooSmall = True
            #if the distance between points is too small, mark for deletion
            if(pointDistanceTooSmall == True and curvePointNumber != 0):
                currentSpline.points[curvePointNumber].select = True
        #delete points which are too close
        bpy.ops.curve.delete(type='VERT')

        #fix normals and apply loop if required
        bpy.ops.curve.select_all(action='SELECT')
        if(loopAnimation == True):
            bpy.ops.curve.cyclic_toggle()
            bpy.ops.curve.select_all(action='DESELECT')
            currentSpline.points[0].select = True
            bpy.ops.curve.delete(type='VERT')
            bpy.ops.curve.select_all(action='SELECT')
        currentSpline.use_bezier_u = True
        currentSpline.use_bezier_u = False
        currentSpline.order_u = 4
        currentSpline.use_endpoint_u = True
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
        if(context.active_object.mode == 'POSE'):
            print("using bones")
            isUsingBones = True
            objectsForPaths = context.selected_pose_bones_from_active_object
        else:
            objectsForPaths = context.selected_objects
        
        #clear any existing path objects
        bpy.ops.empathy.clearobjectpaths()
        
        
        #for bones
        if(isUsingBones):
            activeArmature = context.active_object
            bpy.ops.object.editmode_toggle()
            for disconnectingBone in context.selected_editable_bones:
                disconnectingBone.use_connect = False
            bpy.ops.object.editmode_toggle()
            
            
        #constants
        copyLocationConstraintName = "EMPATHY_MOVECONSTRAINT"
        cancelRotationConstraintName = "EMPATHY_ROTATECANCELCONSTRAINT"
        followPathConstraintName = "EMPATHY_PATHCONSTRAINT"
        rotatePitchTrackConstraintName = "EMPATHY_ROTATEPITCHTRACKCONSTRAINT"
        rotateYawTrackConstraintName = "EMPATHY_ROTATEYAWTRACKCONSTRAINT"
        poleTrackConstraintName = "EMPATHY_POLETRACKCONSTRAINT"
        poleTrackConstraintName = "EMPATHY_POLETRACKCONSTRAINT"
        
        #step through all selected objects and assign to motion paths
        for pathingObject in objectsForPaths: #may be bones or objects
            #determine how many split markers exist for the pathing object
            splitMarkerList = []
            for splitMarkerName in context.scene.timeline_markers.keys():
                if(context.scene.timeline_markers[splitMarkerName].frame != context.scene.frame_start and
                    context.scene.timeline_markers[splitMarkerName].frame != context.scene.frame_end):
                    #for bones
                    if(isUsingBones):
                        if(activeArmature.name in splitMarkerName and pathingObject.name in splitMarkerName):
                            splitMarkerList.append(context.scene.timeline_markers[splitMarkerName].frame)
                    else:
                        if(pathingObject.name in splitMarkerName):
                            splitMarkerList.append(context.scene.timeline_markers[splitMarkerName].frame)
            print("marker list is " + str(splitMarkerList))
            
            
            bpy.ops.object.select_all(action='DESELECT')
            
            #for bones
            if(isUsingBones):
                objectCollectionName = "EMPATHY_ARMATURECOMPONENTS_" + activeArmature.name + "_" + pathingObject.name
            else:
                objectCollectionName = "EMPATHY_COMPONENTS_" + pathingObject.name
            
            #names for empties incorporating pathing object names
            rotateEmptyName = "EMPATHY_ROTATEEMPTY_" + pathingObject.name
            poleEmptyName = "EMPATHY_POLEEMPTY_" + pathingObject.name
            moveEmptyName = "EMPATHY_MOVEEMPTY_" + pathingObject.name
            
            movePathName = "EMPATHY_MOVEPATH_" +  str(pathingObject.name)
            rotatePathName = "EMPATHY_ROTATEPATH_" +  str(pathingObject.name)
            polePathName = "EMPATHY_POLEPATH_" +  str(pathingObject.name)
            
            #create collection to hold path components for this object
            self.setupCollection(context,objectCollectionName)
            
            
            #create empty for target object to follow along path
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,0,0))
            objectMoveEmpty = context.object
            objectMoveEmpty.name = moveEmptyName
            
            #for bones
            if(isUsingBones):
                emptyTransformConstraint = objectMoveEmpty.constraints.new(type='COPY_TRANSFORMS')
                emptyTransformConstraint.name = "EMPATHY_TEMPTRANSFORMCONSTRAINT"
                emptyTransformConstraint.target = activeArmature
                emptyTransformConstraint.subtarget = pathingObject.name
            else:
                emptyTransformConstraint = objectMoveEmpty.constraints.new(type='COPY_TRANSFORMS')
                emptyTransformConstraint.name = "EMPATHY_TEMPTRANSFORMCONSTRAINT"
                emptyTransformConstraint.target = pathingObject
            
            objectMoveEmpty.show_in_front = True
            self.assignToCollection(context,objectCollectionName,objectMoveEmpty)
            
            #add empty to track the rotation
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,5,0))
            objectRotateEmpty = context.object
            objectRotateEmpty.name = rotateEmptyName
            
            objectRotateEmpty.parent = objectMoveEmpty
                
            objectRotateEmpty.show_in_front = True
            self.assignToCollection(context,objectCollectionName,objectRotateEmpty)
            
            #add empty to track the pole
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,0,5))
            objectPoleEmpty = context.object
            objectPoleEmpty.name = poleEmptyName
            
            objectPoleEmpty.parent = objectMoveEmpty
                
            objectPoleEmpty.show_in_front = True
            self.assignToCollection(context,objectCollectionName,objectPoleEmpty)


            
            #create path segments between each split point by setting the timeline duration to the
            originalTimelineRange = [context.scene.frame_start,context.scene.frame_end]
            splitMarkerList.insert(originalTimelineRange[0],0)
            pathSegmentCount = len(splitMarkerList)+1
            movePathSegmentList = [] #segment lists for joining path segment end points
            rotatePathSegmentList = []
            polePathSegmentList = []
            for pathSegmentNumber in range(1,pathSegmentCount):
                movePathSegmentName = movePathName + "_Segment" + str(pathSegmentNumber)
                rotatePathSegmentName = rotatePathName + "_Segment" + str(pathSegmentNumber)
                polePathSegmentName = polePathName + "_Segment" + str(pathSegmentNumber)
                pathSegmentStartFrame = originalTimelineRange[0]
                pathSegmentEndFrame = originalTimelineRange[1]
                if(pathSegmentCount > 1): #a path segment count of 1 means no usable curve split markers
                    if(pathSegmentNumber == 1): #first path segment is from frame start to marker
                        pathSegmentEndFrame = splitMarkerList[pathSegmentNumber]
                    elif(pathSegmentNumber == len(splitMarkerList)):
                        pathSegmentStartFrame = splitMarkerList[pathSegmentNumber-1]
                        pathSegmentEndFrame = originalTimelineRange[1]
                    else:
                        pathSegmentStartFrame = splitMarkerList[pathSegmentNumber-1]
                        pathSegmentEndFrame = splitMarkerList[pathSegmentNumber]
                print("creating path segment " + movePathSegmentName + " from " + str(pathSegmentStartFrame) + "to" + str(pathSegmentEndFrame))
                context.scene.frame_start = pathSegmentStartFrame
                context.scene.frame_end = pathSegmentEndFrame
                #create and compute paths
                #movement paths
                objectMovePath = self.setupBezierCurve(context,movePathSegmentName)
                self.computeCurveShape(context,captureInterval,minimumMoveDistance,objectMovePath,objectMoveEmpty,loopAnimation)
                self.assignToCollection(context,objectCollectionName,objectMovePath)
                movePathSegmentList.append(objectMovePath)
                
                #rotation paths
                objectRotatePath = self.setupBezierCurve(context,rotatePathSegmentName)
                self.computeCurveShape(context,captureInterval,minimumRotateDistance,objectRotatePath,objectRotateEmpty,loopAnimation)
                self.assignToCollection(context,objectCollectionName,objectRotatePath)
                rotatePathSegmentList.append(objectMovePath)
                
                #pole paths
                objectPolePath = self.setupBezierCurve(context,polePathSegmentName)
                self.computeCurveShape(context,captureInterval,minimumPoleDistance,objectPolePath,objectPoleEmpty,loopAnimation)
                self.assignToCollection(context,objectCollectionName,objectPolePath)
                polePathSegmentList.append(objectMovePath)
            
            #join path segment ends
            #movement paths
            bpy.ops.object.select_all(action='DESELECT')
            for movePathSegment in movePathSegmentList:
                movePathSegment.select_set(True)
            
            bpy.ops.object.editmode_toggle()
            context.scene.tool_settings.transform_pivot_point = 'BOUNDING_BOX_CENTER'
            for curveObjectNumber in range(0,len(bpy.context.selected_objects)):
                if(curveObjectNumber < len(bpy.context.selected_objects)-1):
                    bpy.ops.curve.select_all(action='DESELECT')
                    firstCurvePoint = bpy.context.selected_objects[curveObjectNumber]
                    secondCurvePoint = bpy.context.selected_objects[curveObjectNumber+1]
                    firstCurvePoint.data.splines[0].points[0].select = True
                    secondCurvePoint.data.splines[0].points[-1].select = True
                    bpy.ops.transform.resize(value=(0,0,0))
                    
            
            
            #reset timeline to original length
            context.scene.frame_start = originalTimelineRange[0]
            context.scene.frame_end = originalTimelineRange[1]
            #delete temporary constraint on object move empty
            for constraintToRemove in objectMoveEmpty.constraints:
                if("EMPATHY_" in constraintToRemove.name):
                    objectMoveEmpty.constraints.remove(constraintToRemove)
            
#            #enable rotation tracking on object
#            objectRotateEmpty.parent = None
#            objectRotateEmpty.location = (0,0,0)
#            rotatePathConstraint = objectRotateEmpty.constraints.new(type='FOLLOW_PATH')
#            rotatePathConstraint.name = followPathConstraintName
#            rotatePathConstraint.target = objectRotatePath
#            rotatePathConstraint.use_fixed_location = True
#            
#            #enable pole tracking on object
#            objectPoleEmpty.parent = None
#            objectPoleEmpty.location = (0,0,0)
#            polePathConstraint = objectPoleEmpty.constraints.new(type='FOLLOW_PATH')
#            polePathConstraint.name = followPathConstraintName
#            polePathConstraint.target = objectPolePath
#            polePathConstraint.use_fixed_location = True
#            
#            #motion tracking along path
#            objectMoveEmpty.parent = None
#            objectMoveEmpty.location = (0,0,0)
#            movePathConstraint = objectMoveEmpty.constraints.new(type='FOLLOW_PATH')
#            movePathConstraint.name = followPathConstraintName
#            movePathConstraint.target = objectMovePath
#            movePathConstraint.use_fixed_location = True
#            
##            #prevent object rotating as a result of the original motion
##            cancelRotationConstraint = pathingObject.constraints.new(type='COPY_ROTATION')
##            cancelRotationConstraint.name = cancelRotationConstraintName
##            cancelRotationConstraint.target = objectMoveEmpty
#            
#            #constrain object to movement empty
#            copyMoveLocationConstraint = pathingObject.constraints.new(type='COPY_LOCATION')
#            copyMoveLocationConstraint.name = copyLocationConstraintName
#            copyMoveLocationConstraint.target = objectMoveEmpty
#            copyMoveLocationConstraint.influence = 1
#            
#            #create tracking constraints with pole to follow rotation empties
#            rotatePitchTrackConstraint = pathingObject.constraints.new(type='LOCKED_TRACK')
#            rotatePitchTrackConstraint.name = rotatePitchTrackConstraintName
#            rotatePitchTrackConstraint.target = objectRotateEmpty
#            rotatePitchTrackConstraint.track_axis = 'TRACK_Y'
#            rotatePitchTrackConstraint.lock_axis = 'LOCK_Z'
#            rotatePitchTrackConstraint.influence = 1
#            
#            rotateYawTrackConstraint = pathingObject.constraints.new(type='LOCKED_TRACK')
#            rotateYawTrackConstraint.name = rotateYawTrackConstraintName
#            rotateYawTrackConstraint.target = objectRotateEmpty
#            rotateYawTrackConstraint.track_axis = 'TRACK_Y'
#            rotateYawTrackConstraint.lock_axis = 'LOCK_X'
#            rotateYawTrackConstraint.influence = 1
#            
#            poleTrackConstraint = pathingObject.constraints.new(type='LOCKED_TRACK')
#            poleTrackConstraint.name = poleTrackConstraintName
#            poleTrackConstraint.target = objectPoleEmpty
#            poleTrackConstraint.track_axis = 'TRACK_Z'
#            poleTrackConstraint.lock_axis = 'LOCK_Y'
#            poleTrackConstraint.influence = 1
#            
#            #put path empties in a list for iterating through the creation and adjustment of path follow keyframes
#            controlEmptyList = [objectRotateEmpty,objectMoveEmpty,objectPoleEmpty]
#            
#            for controlEmptyType in controlEmptyList:
#                #create motion keyframes
#                context.scene.frame_set(context.scene.frame_start)
#                controlEmptyType.constraints[followPathConstraintName].offset_factor = 1
#                controlEmptyType.constraints[followPathConstraintName].keyframe_insert(data_path = 'offset_factor')
#                if(loopAnimation == True):
#                    context.scene.frame_set(context.scene.frame_end + 1)
#                else:
#                    context.scene.frame_set(context.scene.frame_end)
#                controlEmptyType.constraints[followPathConstraintName].offset_factor = 0
#                controlEmptyType.constraints[followPathConstraintName].keyframe_insert(data_path = 'offset_factor')
#                
#                #pinch handles on keyframes to make start and end points behave linear
#                for keyframePointNumber in range(0,2):
#                    controlEmptyType.animation_data.action.fcurves[0].keyframe_points[keyframePointNumber].handle_left_type = 'FREE'
#                    controlEmptyType.animation_data.action.fcurves[0].keyframe_points[keyframePointNumber].handle_right_type = 'FREE'
#                    controlEmptyType.animation_data.action.fcurves[0].keyframe_points[keyframePointNumber].handle_left = controlEmptyType.animation_data.action.fcurves[0].keyframe_points[keyframePointNumber].co
#                    controlEmptyType.animation_data.action.fcurves[0].keyframe_points[keyframePointNumber].handle_right = controlEmptyType.animation_data.action.fcurves[0].keyframe_points[keyframePointNumber].co
#                    
        context.scene.tool_settings.use_keyframe_insert_auto = originalKeyframeInsertState
        context.scene.frame_set(originalKeyframePosition)
        
        return {'FINISHED'}
    
#button to create timeline markers to define the beginning and end of curve segments
class EMPATHY_OT_PlaceCurveSegmentMarker(bpy.types.Operator):
    bl_idname = "empathy.placecurvemarker"
    bl_label = "Place curve split timeline marker for current objects"
    bl_description = "Place a timeline marker at the current time to define a split point in generated curves for the selected objects"
    
    #get the next highest marker number for distinct marker numbering
    def findNextHighestMarkerNumber(self, context):
        maxMarkerNumber = 0 #find next highest marker number
        for timelineMarkerName in context.scene.timeline_markers.keys():
            currentMarkerNumber = timelineMarkerName.split("_")
            if(int(currentMarkerNumber[-1]) > maxMarkerNumber):
                maxMarkerNumber = int(currentMarkerNumber[-1])
        return maxMarkerNumber
    
    def execute(self, context):
        #currently selected objects to place curve segment markers for
        objectsForPaths = None
        #for bones
        isUsingBones = False
        activeArmature = None
        if(context.active_object.mode == 'POSE'):
            print("using bones")
            isUsingBones = True
            objectsForPaths = context.selected_pose_bones_from_active_object
            activeArmature = context.active_object
        else:
            objectsForPaths = context.selected_objects
            
        #step through all selected objects and create a curve segment marker for them at the current time
        for pathingObject in objectsForPaths: #may be bones or objects
            #for bones
            nextMarkerNumber = self.findNextHighestMarkerNumber(context) + 1
            if(isUsingBones == True):
                context.scene.timeline_markers.new(name = "EMP_SPT_" + activeArmature.name + "_" + pathingObject.name + "_" + str(nextMarkerNumber),frame = bpy.context.scene.frame_current)
            else:
                context.scene.timeline_markers.new(name = "EMP_SPT_" + pathingObject.name + "_" + str(nextMarkerNumber),frame = bpy.context.scene.frame_current)
        return {'FINISHED'}

#register and unregister all Empathy classes
empathyClasses = (  EMPATHY_PT_MenuPanel,
                    EMPATHY_PT_MenuPanelPose,
                    EMPATHY_OT_CreateObjectPaths,
                    EMPATHY_OT_ClearPathsFromSelected,
                    EMPATHY_OT_PlaceCurveSegmentMarker)

register, unregister = bpy.utils.register_classes_factory(empathyClasses)

#register this script for debugging
if __name__ == '__main__':
    register()
