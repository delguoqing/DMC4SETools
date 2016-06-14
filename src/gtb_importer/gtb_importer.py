# -*- coding: utf8 -*-
import os
import sys
import bmesh
import bpy
import six
import mathutils
import json

def ENSURE_LUT(v):
	if hasattr(v, "ensure_lookup_table"):
		v.ensure_lookup_table()
	v.index_update()
	
def import_gtb(filepath):
	f = open(filepath, "r")
	gtb = json.load(f)
	f.close()
	# import armature
	has_skeleton = bool(gtb.get("skeleton"))
	if has_skeleton:
		armature = import_armature(gtb)
	# import mesh
	for name, msh in gtb["objects"].items():
		msh_obj = import_mesh(name, msh, gtb)
		if has_skeleton:
			mod = msh_obj.modifiers.new("gen_armt", 'ARMATURE')
			mod.object = armature
			mod.use_bone_envelopes = False
			mod.use_vertex_groups = True
	return {'FINISHED'}

def import_mesh(name, msh, gtb):
	has_skeleton = bool(gtb.get("skeleton"))
	# bmesh start
	bm = bmesh.new()
	# vertices
	for i in range(msh["vertex_num"]):
		x, y, z = msh["position"][i * 3: i * 3 + 3]
		bm.verts.new((x, z, y))
	ENSURE_LUT(bm.verts)
	# faces
	used_faces = set()
	def NEW_FACE(idxs):
		if idxs[0] == idxs[1] or idxs[0] == idxs[2] or idxs[1] == idxs[2]:
			return
		dup_face = tuple(sorted(idxs))
		# in case Blender complains about face already exists
		# in case we have duplicated face, we duplicate vertices
		if dup_face in used_faces:
			for idx in idxs:
				co = bm.verts[idx].co
				bm.verts.new((co.x, co.y, co.z))
				ENSURE_LUT(bm.verts)
			face = [ bm.verts[-3], bm.verts[-2], bm.verts[-1] ]
			bm.faces.new(face)
		else:
			used_faces.add(dup_face)
			face = [ bm.verts[idx] for idx in idxs ]
			bm.faces.new(face)
	for i in range(0, msh["index_num"], 3):
		NEW_FACE( msh["indices"][i: i + 3] )
	ENSURE_LUT(bm.faces)
	# bmesh -> mesh
	blend_mesh = bpy.data.meshes.new(name=name)
	bm.to_mesh(blend_mesh)
	# create object
	obj = bpy.data.objects.new(name, blend_mesh)
	bpy.context.scene.objects.link(obj)		
	bpy.context.scene.objects.active = obj
	obj.select = True
	if msh.get("shade_smooth"):
		bpy.ops.object.shade_smooth()
	if msh.get("flip_normals"):
		bpy.ops.object.editmode_toggle()
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.mesh.flip_normals()
		bpy.ops.object.mode_set()
	if msh.get("double_sided"):
		pass
	if msh.get("flip_v"):
		pass
	obj.select = False
	# create vertex groups for skinning
	max_involved_joint = msh.get("max_involved_joint", 0)
	if not has_skeleton or max_involved_joint <= 0:
		return obj
	for bone_name in gtb["skeleton"]["name"]:
		obj.vertex_groups.new(bone_name)
	# assign vertex weights
	for i in range(msh["vertex_num"]):
		joints = msh["joints"][i * max_involved_joint: (i + 1) * max_involved_joint]
		weights = msh["weights"][i * max_involved_joint: (i + 1) * max_involved_joint]
		for joint, weight in zip(joints, weights):
			if not weight:
				continue
			joint_name = gtb["skeleton"]["name"][joint]
			group = obj.vertex_groups[joint_name]
			group.add([i], weight, "REPLACE")
	return obj

def apply_bind_pose_matrix(armt, bone_idx, used, parent_list, bone_mat_list):
	bone = armt.edit_bones[bone_idx]
	if used[bone_idx]:
		return bone
	x, y, z = bone_mat_list[16 * bone_idx + 12: 16 * bone_idx + 15]
	if parent_list[bone_idx] == -1:
		bone.head = (x, z, y)
	else:
		parent_bone = apply_bind_pose_matrix(armt, parent_list[bone_idx], used,
											 parent_list, bone_mat_list)
		bone.head = (x + parent_bone.head[0], z + parent_bone.head[1],
					 y + parent_bone.head[2])
	bone.tail = bone.head
	bone.use_connect = False
	used[bone_idx] = True
	return bone

def import_armature(gtb):	
	skeleton = gtb["skeleton"]
	parent_list = skeleton["parent"]
	bone_mat_list = skeleton["matrix"]
	bone_name_list = skeleton["name"]
	bone_num = len(parent_list)
	
	armature_name = "armat"
	
	bpy.ops.object.add(type='ARMATURE', enter_editmode=True)
	obj = bpy.context.object
	obj.show_x_ray = True
	obj.name = armature_name
	obj.select = True
	bpy.context.scene.objects.active = obj
	
	armt = obj.data
	armt.name = armature_name
	
	bpy.ops.object.mode_set(mode='EDIT')

	# TODO: need to apply the full matrix
	used = [False] * bone_num
	for bone_idx in range(bone_num):
		bone_name = bone_name_list[bone_idx]
		bone = armt.edit_bones.new(bone_name)
	for i in range(bone_num):
		apply_bind_pose_matrix(armt, i, used, parent_list, bone_mat_list)
		
	is_leaf = [True] * bone_num
	for bidx, pidx in enumerate(parent_list):
		bone = armt.edit_bones[bidx]
		if pidx == -1:
			bone.parent = None
		else:
			bone.parent = armt.edit_bones[pidx]
			bone.parent.tail = bone.head
			is_leaf[pidx] = False
	for bidx in range(bone_num):
		bone = armt.edit_bones[bidx]
		if is_leaf[bidx]:
			parent = armt.edit_bones[parent_list[bidx]]
			d = parent.tail - parent.head
			d.normalize()
			bone.tail = bone.head + d * 0.1
	for bidx in range(bone_num):
		bone = armt.edit_bones[bidx]
		if bone.head == bone.tail:
			bone.tail += mathutils.Vector((0.0, -0.1, 0.0))
	bpy.ops.object.mode_set()
	return obj