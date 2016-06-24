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
	
	default_pose = gtb["pose"].get("default")
	if default_pose:
		apply_pose(armature, default_pose)
	return {'FINISHED'}

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