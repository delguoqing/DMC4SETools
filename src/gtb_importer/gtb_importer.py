# -*- coding: utf8 -*-
import os
import sys
import bmesh
import bpy
import six
import mathutils
import json

BONE_LENGTH = 10.0

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
		
def import_armature(gtb):
	skeleton = gtb["skeleton"]
	parent_list = skeleton["parent"]
	bone_mat_list = convert_to_native_matrix(skeleton["matrix"])
	bone_id = gtb.get("bone_id")
	bone_name_list = skeleton["name"]
	bone_num = len(parent_list)
	
	# for retargeting
	if bone_id is None:
		bone_mapping = dict([(str(i), i) for i in range(bone_num)])
	else:
		bone_mapping = {}
		for idx, _id in enumerate(bone_id):
			bone_mapping[str(_id)] = idx
	
	# calculate local to world matrix
	world_mat_list = [None] * bone_num
	for i in range(bone_num):
		calc_local_to_world_matrix(i, bone_mat_list, parent_list, world_mat_list)
	
	armature_name = "armat"
	
	bpy.ops.object.add(type='ARMATURE', enter_editmode=True)
	obj = bpy.context.object
	obj.show_x_ray = True
	obj.name = armature_name
	obj.select = True
	obj["bone_mapping"] = bone_mapping
	bpy.context.scene.objects.active = obj
	
	armt = obj.data
	armt.name = armature_name
	
	bpy.ops.object.mode_set(mode='EDIT')

	used = [False] * bone_num
	for bone_idx in range(bone_num):
		bone_name = bone_name_list[bone_idx]
		bone = armt.edit_bones.new(bone_name)
		bone.use_connect = False
		world_mat = world_mat_list[bone_idx]
		head = mathutils.Vector([0.0, 0.0, 0.0, 1.0])
		tail = mathutils.Vector([0.0, 1.0 * BONE_LENGTH, 0.0, 1.0])
		head_world = world_mat * head
		tail_world = world_mat * tail
		bone.head = (head_world.x, head_world.z, head_world.y)
		bone.tail = (tail_world.x, tail_world.z, tail_world.y)
		_, rot, _ = world_mat.decompose()
		axis, angle = rot.to_axis_angle()
		bone.roll = -angle
		
	for bone_idx in range(bone_num):
		bone = armt.edit_bones[bone_idx]
		if parent_list[bone_idx] == -1:
			bone.parent = None
		else:
			bone.parent = armt.edit_bones[parent_list[bone_idx]]
	bpy.ops.object.mode_set()
	return obj

# convert flattened array to native blender matrix, i.e. mathutils.Matrix
def convert_to_native_matrix(mat_list):
	matrices = []
	for i in range(0, len(mat_list), 16):
		native_mat = mathutils.Matrix([
			mat_list[i + 0 : i + 4],
			mat_list[i + 4 : i + 8],
			mat_list[i + 8 : i + 12],
			mat_list[i + 12: i + 16],
		])
		# blender uses column major order!
		native_mat.transpose()
		matrices.append(native_mat)
	return matrices

# In blender, head, tail, and axis are specified in world space coordinate, we have
# to calculate the local space to world space matrix.
def calc_local_to_world_matrix(i, local_mat, parent, result):
	if result[i] is not None:
		return
	if parent[i] == -1:
		result[i] = local_mat[i]
		return
	calc_local_to_world_matrix(parent[i], local_mat, parent, result)
	result[i] = result[parent[i]] * local_mat[i]