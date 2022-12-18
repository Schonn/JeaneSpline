Thank you for downloading Jeane Spline 1.0.9 for Blender 3.4.0!

This addon quickly applies space switching effects in object mode to:
-Selected objects
-Selected bones inside of selected armatures

To install:
-Download as zip
-Install zip from Add-Ons section of Blender preferences window
-Make sure add-on is switched on

To access the Jeane Spline menu:
See 'Jeane Spline' tab in right-hand menu of 3D viewport when in object mode.

Jeane Spline can be applied to bones inside of armatures
To apply to an armature:
-Select the bones you wish to apply the effect to in pose mode
-Go to object mode
-Click on 'Start Baking for Selected'

Jeane Spline can be applied to objects
To apply to an object:
-Select the bones you wish to apply the effect to in pose mode
-Go to object mode
-Click on 'Start Baking for Selected'
-Objects will use parent hierarchy to determine delay effect offsets

Jeane Spline can be applied to multiple bones in multiple armatures and multiple objects at once
To apply to multiple objects and armatures at once:
-Select the bones in the armatures you wish to apply the effect to in pose mode
-Go to object mode and select the armatures and the objects you wish to apply the effect to
-Click on 'Start Baking for Selected'

Jeane Spline effects can be deleted from multiple objects and bones in armatures at once
To delete all empties and constraints from multiple objects and armatures at once:
-Select the bones in the armatures you wish to delete the effect from in pose mode
-Go to object mode and select the armatures and the objects you wish to delete the effect from
-Click on 'Delete Effect from Selected'

The start and end of a baked animation can be wrapped with Jeane Spline
To wrap start and end frames for an animation when baking:
-Select 'Wrap Frames for Looped Animation' before clicking 'Start Baking for Selected'

Armature bones can be split automatically by Jeane Spline so that position effects work correctly
To split an armature to allow position effects to work when baking:
-Select 'Split Bones for Position Effects' before clicking 'Start Baking for Selected'

Effect presets create a starting point for setting suitable effect influences
To apply an effect preset:
-Select one of the buttons marked 'Preset:' before clicking 'Start Baking for Selected'
-'Follow Through' may work for general flowing character animation
-'Noisy Follow Through' may work for character animation with ambient movement noise
-'Squash and Stretch' may work for exaggerated character animation with minimal follow through
-'Noisy Smoothing' may work for objects that appear to be hovering

To change the amount of noise added when baking space switching effects:
-Change the values of 'Rotation Noise Amount' and 'Location Noise Amount'
-'Rotation Noise Amount' greater than 0 causes random rotation wobbling
-'Location Noise Amount' greater than 0 causes random position wobbling

To change the influence of smoothing effects:
-Change the values of 'Smooth Position Influence' and 'Smooth Rotation Influence'
-'Smooth Position Influence' helps with movement path arcing by sampling keyframes at large intervals
-'Smooth Rotation Influence' helps with rotation arcing by sampling keyframes at large intervals
-Smoothing effects are overwritten by delay effects if delay effects have higher influence

To change the influence of smoothing effects:
-Change the values of 'Delay Position Influence' and 'Smooth Rotation Influence'
-'Smooth Position Influence' helps with movement path arcing by sampling keyframes at large intervals
-'Smooth Rotation Influence' helps with rotation arcing by sampling keyframes at large intervals
-Smoothing effects are overwritten by delay effects if delay effects have higher influence



