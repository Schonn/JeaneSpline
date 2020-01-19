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
        self.layout.operator('empathy.markcurvesplitframe', text ='Mark Curve Split Frame For Selected') 
        self.layout.operator('empathy.clearcurvesplitframes', text ='Remove Curve Split Frames For Selected')
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
        self.layout.operator('empathy.markcurvesplitframe', text ='Mark Curve Split Frame For Selected') 
        self.layout.operator('empathy.clearcurvesplitframes', text ='Remove Curve Split Frames For Selected') 
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
    
    #get the longest distance between two points in a path
    def getLongestPathPointDistance(self, context, currentSpline):
        longestPointDistance = 0
        #iterate through curve points and delete points which are too close
        for curvePointNumber in range(len(currentSpline.points)):
            if(curvePointNumber - 1 >= 0):
                previousPointDistance = currentSpline.points[curvePointNumber].co.xyz - currentSpline.points[curvePointNumber - 1].co.xyz
                distanceDifferenceValue = abs(previousPointDistance[0]) + abs(previousPointDistance[1]) + abs(previousPointDistance[2])
                if(distanceDifferenceValue > longestPointDistance):
                    longestPointDistance = distanceDifferenceValue
            if(curvePointNumber + 1 <= len(currentSpline.points)-1):
                nextPointDistance = currentSpline.points[curvePointNumber].co.xyz - currentSpline.points[curvePointNumber + 1].co.xyz
                distanceDifferenceValue = abs(nextPointDistance[0]) + abs(nextPointDistance[1]) + abs(nextPointDistance[2])
                if(distanceDifferenceValue > longestPointDistance):
                    longestPointDistance = distanceDifferenceValue
        return longestPointDistance
    
    def computeCurveShape(self,context,captureInterval,minimumDistance,pathToEdit,pathingObject,loopAnimation):
        #print("computing curve shape for" + pathingObject.name)
        context.scene.frame_set(context.scene.frame_start)
        maxKeyFrameNumber = int((context.scene.frame_end - context.scene.frame_start) / captureInterval)
        if(maxKeyFrameNumber <= 1): # do not allow a keyframe capture interval that is too big resulting in no keyframes captured
            captureInterval = 2
            maxKeyFrameNumber = int((context.scene.frame_end - context.scene.frame_start) / captureInterval)
        #print("max key frame number is " + str(maxKeyFrameNumber))
        for recordKeyFramePoint in range(0,maxKeyFrameNumber):
            if(recordKeyFramePoint == maxKeyFrameNumber):
                context.scene.frame_set(context.scene.frame_end)
            elif(recordKeyFramePoint != 0):
                context.scene.frame_set(context.scene.frame_current + captureInterval)
            pathToEdit.data.splines[0].points[0].co.xyz = pathingObject.matrix_world.translation
            #print("setting path point" + str(pathingObject.matrix_world.translation))
            if(recordKeyFramePoint != maxKeyFrameNumber):
                bpy.ops.curve.extrude()
                
        bpy.ops.curve.select_all(action='DESELECT')
        currentSpline = pathToEdit.data.splines[0]
        #minimum distance for points to need to exist
        pointDistanceMinimum = minimumDistance
        #make sure that the minimum path point distance is small enough to retain points
        longestPathPointDistance = self.getLongestPathPointDistance(context, currentSpline)
        if(longestPathPointDistance <= pointDistanceMinimum):
            pointDistanceMinimum = longestPathPointDistance
        print(str(longestPathPointDistance) + " with minimum " + str(pointDistanceMinimum))
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
        currentSpline.points[-1].select = False
        currentSpline.points[1].select = False
        #delete points which are too close
        bpy.ops.curve.delete(type='VERT')

        #fix normals and apply loop if required
        bpy.ops.curve.select_all(action='SELECT')
        currentSpline.use_bezier_u = True
        currentSpline.use_bezier_u = False
        currentSpline.order_u = 4
        currentSpline.use_endpoint_u = True
        bpy.ops.object.editmode_toggle()
    
    #pinch together the ends of motion curve segments
    def joinCurveSegments(self, context, pathSegmentList, loopingAnimation):
        bpy.ops.object.select_all(action='DESELECT')
        for selectPathSegment in pathSegmentList:
            selectPathSegment.select_set(True)
            
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
        if(loopingAnimation == True):
            bpy.ops.curve.select_all(action='DESELECT')
            bpy.context.selected_objects[-1].data.splines[0].points[0].select = True
            bpy.context.selected_objects[0].data.splines[0].points[-1].select = True
            bpy.ops.transform.resize(value=(0,0,0))
        bpy.ops.object.editmode_toggle()
    
    #animate follow path constraints for a given empty and set of curves
    def constrainAndAnimateCurveSegments(self, context, pathConstraintName, controlEmpty, pathSegmentNumber, pathSegmentObject, originalTimelineRange):
        #motion tracking along path
        pathConstraint = controlEmpty.constraints.new(type='FOLLOW_PATH')
        pathConstraint.name = pathConstraintName + "_Segment" + str(pathSegmentNumber)
        pathConstraint.target = pathSegmentObject
        pathConstraint.use_fixed_location = True
        context.scene.frame_set(context.scene.frame_start-1)
        pathConstraint.mute=True
        pathConstraint.keyframe_insert(data_path = 'mute') #make constraint start muted
        context.scene.frame_set(context.scene.frame_start)
        pathConstraint.mute=False
        pathConstraint.offset_factor = 1
        pathConstraint.keyframe_insert(data_path = 'offset_factor')
        pathConstraint.keyframe_insert(data_path = 'mute') #make constraint start at path start unmuted
        context.scene.frame_set(context.scene.frame_end-1)
        pathConstraint.mute=False
        pathConstraint.keyframe_insert(data_path = 'mute')#make sure that muting is switched on and off at correct time
        context.scene.frame_set(context.scene.frame_end)
        pathConstraint.offset_factor = 0
        #do not mute constraint if the end of this curve segment frame range is the end of the whole animation
        if(context.scene.frame_end != originalTimelineRange[1]): 
            pathConstraint.mute=True
            pathConstraint.keyframe_insert(data_path = 'offset_factor')
        else:
            pathConstraint.mute=False
            pathConstraint.keyframe_insert(data_path = 'offset_factor',frame=context.scene.frame_current+1)
        pathConstraint.keyframe_insert(data_path = 'mute') #mute after end of path segment to allow next path segment to take over
        #pinch handles on keyframes to make start and end points behave linear
        for fcurveData in controlEmpty.animation_data.action.fcurves:
            for keyframePoint in fcurveData.keyframe_points:
                keyframePoint.handle_left_type = 'FREE'
                keyframePoint.handle_right_type = 'FREE'
                keyframePoint.handle_left = keyframePoint.co
                keyframePoint.handle_right = keyframePoint.co
                
    #create curves from motion
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
            #print("using bones")
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
            #determine how many split frames exist for the object
            #if none, do a basic split setup
            if not("EMP_SPLIT_FRAMES" in pathingObject):
                context.scene.frame_set(int(context.scene.frame_end/2))
                bpy.ops.empathy.markcurvesplitframe()
            pathingObject["EMP_SPLIT_FRAMES"] = sorted(pathingObject["EMP_SPLIT_FRAMES"].to_list())
            splitMarkerList = sorted(pathingObject["EMP_SPLIT_FRAMES"].to_list())
            
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
            #print("split marker list is " + str(splitMarkerList))
            pathSegmentCount = len(splitMarkerList)
            movePathSegmentList = [] #segment lists for joining path segment end points
            rotatePathSegmentList = []
            polePathSegmentList = []
            for pathSegmentNumber in range(0,pathSegmentCount-1):
                movePathSegmentName = movePathName + "_Segment" + str(pathSegmentNumber)
                rotatePathSegmentName = rotatePathName + "_Segment" + str(pathSegmentNumber)
                polePathSegmentName = polePathName + "_Segment" + str(pathSegmentNumber)
                pathSegmentStartFrame = splitMarkerList[pathSegmentNumber]
                pathSegmentEndFrame = splitMarkerList[pathSegmentNumber+1]
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
                rotatePathSegmentList.append(objectRotatePath)
                
                #pole paths
                objectPolePath = self.setupBezierCurve(context,polePathSegmentName)
                self.computeCurveShape(context,captureInterval,minimumPoleDistance,objectPolePath,objectPoleEmpty,loopAnimation)
                self.assignToCollection(context,objectCollectionName,objectPolePath)
                polePathSegmentList.append(objectPolePath)
                
                
                #create constraints and animations for paths
                
                #movement paths
                self.constrainAndAnimateCurveSegments(context, followPathConstraintName, objectMoveEmpty, pathSegmentNumber, objectMovePath, originalTimelineRange)
               
                #rotation paths
                self.constrainAndAnimateCurveSegments(context, followPathConstraintName, objectRotateEmpty, pathSegmentNumber, objectRotatePath, originalTimelineRange)
                
                #pole paths
                self.constrainAndAnimateCurveSegments(context, followPathConstraintName, objectPoleEmpty, pathSegmentNumber, objectPolePath, originalTimelineRange)
                
 
            #join path segment ends
            #movement paths
            self.joinCurveSegments(context, movePathSegmentList, loopAnimation)
            #rotation paths
            self.joinCurveSegments(context, rotatePathSegmentList, loopAnimation)
            #pole paths
            self.joinCurveSegments(context, polePathSegmentList, loopAnimation)
            
            
            
            #reset timeline to original length
            context.scene.frame_start = originalTimelineRange[0]
            context.scene.frame_end = originalTimelineRange[1]
            #delete temporary constraint on object move empty
            for constraintToRemove in objectMoveEmpty.constraints:
                if("EMPATHY_TEMPTRANSFORMCONSTRAINT" in constraintToRemove.name):
                    objectMoveEmpty.constraints.remove(constraintToRemove)
                    
            #clear parents for rotation and pole to make them stick to their paths
            objectRotateEmpty.parent = None
            objectRotateEmpty.location = (0,0,0)
            objectPoleEmpty.parent = None
            objectPoleEmpty.location = (0,0,0)
                       
            #prevent object rotating as a result of the original motion
            cancelRotationConstraint = pathingObject.constraints.new(type='COPY_ROTATION')
            cancelRotationConstraint.name = cancelRotationConstraintName
            cancelRotationConstraint.target = objectMoveEmpty
            
            #constrain object to movement empty
            copyMoveLocationConstraint = pathingObject.constraints.new(type='COPY_LOCATION')
            copyMoveLocationConstraint.name = copyLocationConstraintName
            copyMoveLocationConstraint.target = objectMoveEmpty
            copyMoveLocationConstraint.influence = 1
            
            #create tracking constraints with pole to follow rotation empties
            rotatePitchTrackConstraint = pathingObject.constraints.new(type='LOCKED_TRACK')
            rotatePitchTrackConstraint.name = rotatePitchTrackConstraintName
            rotatePitchTrackConstraint.target = objectRotateEmpty
            rotatePitchTrackConstraint.track_axis = 'TRACK_Y'
            rotatePitchTrackConstraint.lock_axis = 'LOCK_Z'
            rotatePitchTrackConstraint.influence = 1
            
            rotateYawTrackConstraint = pathingObject.constraints.new(type='LOCKED_TRACK')
            rotateYawTrackConstraint.name = rotateYawTrackConstraintName
            rotateYawTrackConstraint.target = objectRotateEmpty
            rotateYawTrackConstraint.track_axis = 'TRACK_Y'
            rotateYawTrackConstraint.lock_axis = 'LOCK_X'
            rotateYawTrackConstraint.influence = 1
            
            poleTrackConstraint = pathingObject.constraints.new(type='LOCKED_TRACK')
            poleTrackConstraint.name = poleTrackConstraintName
            poleTrackConstraint.target = objectPoleEmpty
            poleTrackConstraint.track_axis = 'TRACK_Z'
            poleTrackConstraint.lock_axis = 'LOCK_Y'
            poleTrackConstraint.influence = 1
         
        context.scene.tool_settings.use_keyframe_insert_auto = originalKeyframeInsertState
        context.scene.frame_set(originalKeyframePosition)
        
        return {'FINISHED'}
    
#button to add frames to the selected object's split frame array for splitting the generated curves
class EMPATHY_OT_MarkCurveSplitFrame(bpy.types.Operator):
    bl_idname = "empathy.markcurvesplitframe"
    bl_label = "Mark curve split at current time"
    bl_description = "Add the current frame as a point where the curve will be split for the selected object"

    def addValueToPropListIfNotExists(self,context,newValue,objectWithList):
        if not(newValue in objectWithList["EMP_SPLIT_FRAMES"]):
            splitFrameList = objectWithList["EMP_SPLIT_FRAMES"].to_list()
            splitFrameList.append(newValue)
            splitFrameList = sorted(splitFrameList)
            objectWithList["EMP_SPLIT_FRAMES"] = splitFrameList
    
    def execute(self, context):
        #currently selected objects to place curve segment markers for
        objectsForPaths = None
        #for bones
        isUsingBones = False
        activeArmature = None
        if(context.active_object.mode == 'POSE'):
            #print("using bones")
            isUsingBones = True
            objectsForPaths = context.selected_pose_bones_from_active_object
            activeArmature = context.active_object
        else:
            objectsForPaths = context.selected_objects
            
        #step through all selected objects and create a curve segment marker for them at the current time
        for pathingObject in objectsForPaths: #may be bones or objects
            if not("EMP_SPLIT_FRAMES" in pathingObject): #set up split frame list if not created
                pathingObject["EMP_SPLIT_FRAMES"] = []
            #add start, end and current frame to split frame list if not already added
            self.addValueToPropListIfNotExists(context,context.scene.frame_start,pathingObject)
            self.addValueToPropListIfNotExists(context,context.scene.frame_end,pathingObject)
            self.addValueToPropListIfNotExists(context,context.scene.frame_current,pathingObject)

        return {'FINISHED'}
    
#button to clear the object's curve split frame array
class EMPATHY_OT_ClearCurveSplitFrames(bpy.types.Operator):
    bl_idname = "empathy.clearcurvesplitframes"
    bl_label = "Clear curve split frames from object"
    bl_description = "Remove all curve split frames from the selected object"

    def execute(self, context):
        #currently selected objects to remove curve segment frames from
        objectsForPaths = None
        #for bones
        isUsingBones = False
        activeArmature = None
        if(context.active_object.mode == 'POSE'):
            #print("using bones")
            isUsingBones = True
            objectsForPaths = context.selected_pose_bones_from_active_object
            activeArmature = context.active_object
        else:
            objectsForPaths = context.selected_objects
            
        #step through all selected objects and delete all curve split frame data
        for pathingObject in objectsForPaths: #may be bones or objects
            pathingObject["EMP_SPLIT_FRAMES"] = [context.scene.frame_start,context.scene.frame_end]
        return {'FINISHED'}
    
#register and unregister all Empathy classes
empathyClasses = (  EMPATHY_PT_MenuPanel,
                    EMPATHY_PT_MenuPanelPose,
                    EMPATHY_OT_CreateObjectPaths,
                    EMPATHY_OT_ClearPathsFromSelected,
                    EMPATHY_OT_MarkCurveSplitFrame,
                    EMPATHY_OT_ClearCurveSplitFrames)

register, unregister = bpy.utils.register_classes_factory(empathyClasses)

#register this script for debugging
if __name__ == '__main__':
    register()
