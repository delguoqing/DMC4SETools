# -*- coding: utf8 -*-
import os
import sys
import bmesh
import bpy
import six
import mathutils
import json
	
def import_gtba(filepath, armature):
	f = open(filepath, "r")
	gtb = json.load(f)
	f.close()
	
	for motion_name, motion in gtb["animations"].items():
		import_action(motion, armature, motion_name)
		
	default_pose = gtb["pose"].get("default")
	if default_pose:
		apply_pose(armature, default_pose)
	return {'FINISHED'}

def import_action(motion, armature, motion_name):
	action = bpy.data.actions.new(name=motion_name)
	action.use_fake_user = True
	armature.animation_data_create()
	armature.animation_data.action = action
	bone_mapping = armature["bone_mapping"]
	pose_bones = armature.pose.bones
	for bone_id, v in motion.items():
		print(bone_id)
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
		for rot_k in rot:
			f = rot_k[0] + 1
			# In blender, quaternion is stored in order of w, x, y, z
			pose_bone.rotation_quaternion = mathutils.Quaternion(
				[rot_k[4], rot_k[1], rot_k[2], rot_k[3]]
			)
			pose_bone.keyframe_insert("rotation_quaternion", index=-1, frame=f)
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
		if rot is not None:
			# In blender, quaternion is stored in order of w, x, y, z
			pose_bone.rotation_quaternion = mathutils.Quaternion(
				[rot[3], rot[0], rot[1], rot[2]]
			)
		if scale is not None:
			pose_bone.scale = mathutils.Vector(scale[:3])