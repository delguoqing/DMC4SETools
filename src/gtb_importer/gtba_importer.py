# -*- coding: utf8 -*-
import os
import sys
import bmesh
import bpy
import six
import mathutils
import json
	
def import_gtba(filepath, armature, rotation_resample):
	f = open(filepath, "r")
	gtb = json.load(f)
	f.close()
	
	for motion_name, motion in gtb["animations"].items():
		import_action(motion, armature, motion_name,
					  rotation_resample=rotation_resample)
		
	default_pose = gtb["pose"].get("default")
	if default_pose:
		apply_pose(armature, default_pose)
		
	return {'FINISHED'}

def import_action(motion, armature, motion_name, rotation_resample=False):
	action = bpy.data.actions.get(motion_name)
	if not action:
		action = bpy.data.actions.new(name=motion_name)
		action.use_fake_user = True
	if armature.animation_data is None:
		armature.animation_data_create()
	armature.animation_data.action = action
	bone_mapping = armature["bone_mapping"]
	pose_bones = armature.pose.bones
	for bone_id, v in motion.items():
		loc, rot, scale = v
		bone_index = bone_mapping.get(bone_id)
		if bone_index is None:
			continue
		pose_bone = pose_bones[bone_index]
		if loc is None:
			loc = [[0, 0, 0, 0, 0]]
		for loc_k in loc:
			f = loc_k[0] + 1
			pose_bone.location = mathutils.Vector(loc_k[1:4])
			pose_bone.keyframe_insert("location", index=-1, frame=f)
		if rot is None:
			rot = [[0, 0, 1, 0, 0]]
		prev_f = 1
		for rot_k in rot:
			f = rot_k[0] + 1
			# In blender, quaternion is stored in order of w, x, y, z
			q = mathutils.Quaternion(
				[rot_k[4], rot_k[1], rot_k[2], rot_k[3]]
			)
			if f - prev_f > 1 and rotation_resample:
				prev_q = mathutils.Quaternion(pose_bone.rotation_quaternion)
				step = 1.0 / (f - prev_f)
				fraction = 0.0
				for i in range(f - prev_f):
					fraction += step
					_q = prev_q.slerp(q, fraction)
					pose_bone.rotation_quaternion = _q
					pose_bone.keyframe_insert("rotation_quaternion", index=-1, frame=prev_f + i + 1)
			else:
				pose_bone.rotation_quaternion = q
				pose_bone.keyframe_insert("rotation_quaternion", index=-1, frame=f)
			prev_f = f
		if scale is None:
			scale = [[0, 1, 1, 1, 0]]
		for scale_k in scale:
			f = scale_k[0] + 1
			pose_bone.scale = mathutils.Vector(scale_k[1:4])
			pose_bone.keyframe_insert("scale", index=-1, frame=f)

def apply_pose(armature, pose):
	bone_mapping = armature["bone_mapping"]
	pose_bones = armature.pose.bones
	for bone_id, (loc, rot, scale) in pose.items():
		bone_index = bone_mapping.get(bone_id)
		if bone_index is None:
			continue
		pose_bone = pose_bones[bone_index]
		if loc is not None:
			pose_bone.location = mathutils.Vector(loc[:3])
		else:
			pose_bone.location = mathutils.Vector([0, 0, 0])
		if rot is not None:
			# In blender, quaternion is stored in order of w, x, y, z
			pose_bone.rotation_quaternion = mathutils.Quaternion(
				[rot[3], rot[0], rot[1], rot[2]]
			)
		else:
			pose_bone.rotation_quaternion = mathutils.Quaternion([0, 0, 1, 0])
		if scale is not None:
			pose_bone.scale = mathutils.Vector(scale[:3])
		else:
			pose_bone.scale = mathutils.Vector([1, 1, 1])