import zlib
import os
import glob
import shutil
import sys
import numpy
import random
import math
import json
import util
import input_layout
import collada

from d3d10 import dxgi_format_parse

DUMP_TYPE_NONE = 0
DUMP_TYPE_OBJ = 1
DUMP_TYPE_COLLADA = 2
DUMP_TYPE_GTB = 3

DUMP_NORMAL = True
DUMP_UV = True

IS_SUPPORT_ROOT_BONE_ANIMATION = True

IA_D3D10 = None
IA_GAME = None

COMPRESS = True

class CDpInfo(object):
	def __init__(self, n1_block_start_index):
		self.n1_block_start_index = n1_block_start_index
		self.n1_block_end_index = 0
		
	def read(self, getter):
		# vertex count
		self.vertex_num = getter.get("H", offset=0x2)
		# fvf_size
		self.fvf_size = getter.get("B", offset=0xA)
		# fvf & 0xFFF
		# fvf & 0xFFFFF
		# ib offset
		self.ib_offset = getter.get("I", offset=0x18)
		self.ib_size = getter.get("I")
		# vb offset
		self.vb_offset = getter.get("I", offset=0x10)
		# fvf flags: I don't know what is this...
		self.fvf = getter.get("I", offset=0x14)
		self.input_layout_index = self.fvf & 0xFFF
		# index min max
		self.index_min = getter.get("H", offset=0x28)
		self.index_max = getter.get("H")
		# 	index min duplicated?
		index_min_dup = getter.get("I", offset=0xc)
		assert index_min_dup == self.index_min, "0x%x vs 0x%x" % (self.index_min, index_min_dup)
		
		# dword @0x4 can be used to generate some kind of hash,
		# will be replaced in memory with the value after hash
		# but after hash, this value if identical to the value before hash
		self.unk1 = getter.get("I", offset=0x4)
		self.material_index = (self.unk1 >> 12) & 0xFFF
		self.bounding_box_id = (self.unk1 & 0xFFF)
		
		self.unk2 = getter.get("B", offset=0xB)
		unk2 = self.unk2 & 0x3F
		assert unk2 == 3	# always 3 in DMC4SE	
		
		# cmp id
		self.cmp_id = (self.fvf, self.vb_offset, self.material_index, unk2, self.fvf_size)
		# not used
		reserved = getter.get("I", offset=0x2c)	# will point to a n1 block when reading model
		
		self.n1_block_count = getter.get("B", offset=0x25)
		self.n1_block_end_index = self.n1_block_start_index + self.n1_block_count
		
		# no use, will be assigned at runtime
		self.batch_id = getter.get("H", offset=0x26)
		
		self.unknowns = []
		self.unknowns.append(getter.get("H", offset=0x0))	# size ok
		v = getter.get("I", offset=0x4)
		self.unknowns.append(v >> 24)						# size ok
		self.unknowns.append(getter.get("B", offset=0x8))	# size ok
		self.unknowns.append(getter.get("B", offset=0x9))
		v = getter.get("B", offset=0xB)
		self.unknowns.append(v >> 6)
		self.unknowns.append(getter.get("I", offset=0x20))
		self.unknowns.append(getter.get("B", offset=0x24))

	def __eq__(self, o):
		if self.fvf != o.fvf:
			return False
		if self.vb_offset != o.vb_offset:
			return False
		if (self.unk1 ^ o.unk1) & 0xFFF000:
			return False
		if (self.unk2 ^ o.unk2) & 0x3F:
			return False
		return self.fvf_size == o.fvf_size
	
	def __ne__(self, o):
		return not self.__eq__(o)
	
	def print_unknowns(self):
		#print "bb_id:", self.bounding_box_id,
		print("n1_idx:[%d, %d)" % (self.n1_block_start_index, self.n1_block_end_index), end=' ')
		#print "cmp_id_", map(hex, self.cmp_id),
		print("unknowns:", list(map(hex, self.unknowns)))
		
	def __str__(self):
		return "vb_offset = 0x%x, fvf_size=0x%x, fvf=0x%x, vertex_num=%d" % (
			self.vb_offset, self.fvf_size, self.fvf, self.vertex_num
		)
	
class CModel(object):
	
	def __init__(self):
		self.material_names = []
		self.header = None
		self.cur_n1_block_index = 0
		self.id_2_bounding_box = {}
		
	def read(self, mod):
		header = mod.block(0x80)
		
		# 0x0 ~ 0x6
		# fourcc or version or mask verification
		FOURCC = header.get("4s", offset=0x0)
		assert FOURCC == "MOD\x00", "invalid FOURCC %s" % FOURCC
		field_4 = header.get("H", offset=0x4)
		assert field_4 == 0xd2, "invalid MOD file!"
		
		# 0x6 ~ 0x40
		# nums and sizes
		self.bone_num = header.get("H", offset=0x6)
		self.dp_num = header.get("H", 0x8)
		self.material_num = header.get("H", offset=0xa)		
		vertex_num = header.get("I", offset=0xc)
		self.index_num = header.get("I", offset=0x10)
		polygon_num = header.get("I", offset=0x14)
		# DMC4SE uses only TRIANGLE_LIST as its primitive type
		assert polygon_num * 3 == self.index_num		
		self.vb_size = header.get("I", offset=0x18)
		reserved_0 = header.get("I", offset=0x1c)
		assert reserved_0 == 0
		self.n2 = header.get("I", offset=0x20)
		
		# 0x24 ~ 0x40
		# offsets for various sub blocks
		self.bone_info_offset = header.get("I", offset=0x24)
		self.n2_array_offset = header.get("I", offset=0x28)
		self.material_names_offset = header.get("I", offset=0x2c)
		self.primitives_offset = header.get("I", offset=0x30)
		self.vb_offset = header.get("I", offset=0x34)
		self.ib_offset = header.get("I", offset=0x38)
		self.unk_offset = header.get("I", offset=0x3c)	# not useful in this game
		
		# 0x40 ~ 0x80
		# floating point block
		self.bounding_center = header.get("3f", offset=0x40)
		self.world_scale_factor = header.get("f", offset=0x4c)		# ?
		self.base_y = self.world_scale_factor #?
		print("world_scale_factor:", self.world_scale_factor)
		print()
		
		# bounding box
		self.min_x = header.get("f", offset=0x50)
		self.min_y = header.get("f", offset=0x54)
		self.min_z = header.get("f", offset=0x58)
		reserved_1 = header.get("I", offset=0x5c)
		assert reserved_1 == 0
		self.max_x = header.get("f", offset=0x60)
		self.max_y = header.get("f", offset=0x64)
		self.max_z = header.get("f", offset=0x68)
		reserved_2 = header.get("I", offset=0x6c)
		assert reserved_2 == 0
		self.bounding_box = (self.min_x, self.min_y, self.min_z, \
							 self.max_x, self.max_y, self.max_z)
		print("bounding box: (%f, %f, %f) - (%f, %f, %f)" % self.bounding_box)
		print("bounding center:", self.bounding_center)
		print()
		# 0x70 ~ 0x80
		# not used
		
		# 0x84
		self.n1 = mod.get("I")
		
		self.read_bone(mod)
		# seems like this data block is not used in the game
		self.read_bounding_box(mod)
		self.read_material_names(mod)
		self.read_dp(mod)
		# looks like constant buffer
		self.read_unknown1(mod)
		self.read_vb(mod)	
		self.read_ib(mod)
		self.read_not_used(mod)
		mod.assert_end()
		
	def read_bone(self, mod):
		if self.bone_num <= 0:
			return
		mod.seek(self.bone_info_offset)
		print("reading bone data, bone_num = %d" % self.bone_num)
		print("@offset: 0x%x - 0x%x" % (mod.offset, mod.offset + self.bone_num * 0x18))
		mirror_index = [None] * self.bone_num
		parent_index = [None] * self.bone_num
		bone_mat = [None] * self.bone_num
		bone_offset_mat = [None] * self.bone_num
		# bone id used for retargeting
		bone_id = [None] * self.bone_num
		for bone_index in range(self.bone_num):
			bone_info1 = mod.block(0x18)
			unk1, parent_joint, mirror_joint, unk2 = bone_info1.get("4B")
			print("%d: id=%d, parent=%d, sym=%d, unk=%d" % (bone_index, unk1, parent_joint,
															mirror_joint, unk2))
			# bounding sphere radius for this bone
			radius = bone_info1.get("f")
			joint_length = bone_info1.get("f")
			joint_position = bone_info1.get("3f")
			calc_joint_length = (joint_position[0] ** 2 + joint_position[1] ** 2 + joint_position[2] ** 2) ** 0.5
			assert abs(calc_joint_length - joint_length) < 1e-3
			print("\t", "Position=(%f, %f, %f), Length=%f, Radius=%f" % (
				joint_position[0], joint_position[1], joint_position[2], joint_length,
				radius))
			
			parent_index[bone_index] = parent_joint
			mirror_index[bone_index] = mirror_joint
			bone_id[bone_index] = unk1
		
		root_index = None
		for bone_index in range(self.bone_num):
			parent = parent_index[bone_index]
			assert (parent == 0xFF or \
					(parent != bone_index and 0 <= parent < self.bone_num))
			mirror = mirror_index[bone_index]
			assert mirror == 0xFF or mirror_index[mirror] == bone_index
			if root_index is None and parent == 0xFF:
				root_index = bone_index
			
		print("@offset: 0x%x - 0x%x" % (mod.offset, mod.offset + self.bone_num * 0x40))
		# 0x40 is a typical size for a matrix
		# bone transformation
		for bone_index in range(self.bone_num):
			mat = numpy.matrix([
				list(mod.get("4f")),
				list(mod.get("4f")),
				list(mod.get("4f")),
				list(mod.get("4f")),
			])
			bone_mat[bone_index] = mat
			print(mat)
		print("@offset: 0x%x - 0x%x" % (mod.offset, mod.offset + self.bone_num * 0x40))
		# bone offset matrix:
		#	model space -> bone space
		for bone_index in range(self.bone_num):
			mat = numpy.matrix([
				list(mod.get("4f")),
				list(mod.get("4f")),
				list(mod.get("4f")),
				list(mod.get("4f")),
			])
			bone_offset_mat[bone_index] = mat
			print(mat)
			print()
		print("@offset: 0x%x - 0x%x" % (mod.offset, mod.offset + 0x100))
		# bone_id to bone_inex, meaning that max_bone_num = 256
		mod.skip(0x100)
		
		# The final vertex position will sometimes be encoded in format
		# such as DXGI_FORMAT_R16G16B16A16_SNORM, DXGI_FORMAT_R16G16B16A16_UNORM, etc.
		# i.e. they are normalized. We have to invert the normalization process in order
		# to get the correct binding pose.
		# Luckily the `normalize matrix` is 'baked' in the `bone offset matrix`.
		# We can calculate the invert normalize matrix as below
		self.inv_norm_mat = bone_offset_mat[root_index] * bone_mat[root_index]
		print("Invert normalize matrix:")
		print(self.inv_norm_mat)
		
		self.bone_mat = bone_mat
		self.bone_offset_mat = bone_offset_mat
		self.bone_parent = parent_index
		self.bone_id = bone_id
		
	# not even read by the game
	def read_bounding_box(self, mod):
		mod.seek(self.n2_array_offset)
		print("bounding box: %d" % self.n2)
		for i in range(self.n2):
			vals = mod.get("I7f")
			self.id_2_bounding_box[vals[0]] = vals
			print("\t", vals)
			
	def read_material_names(self, mod):
		mod.seek(self.material_names_offset)
		print("n = %d, @offset: 0x%x - 0x%x" % (self.material_num, mod.offset,
												mod.offset + self.material_num * 0x80))
		for i in range(self.material_num):
			material_name = mod.get("128s").rstrip("\x00")
			self.material_names.append(material_name)
			
		print("material names:")
		for material_name in self.material_names:
			print("\t", material_name)
			
	def read_dp(self, mod):
		mod.seek(self.primitives_offset)
		print("dp infos:", self.dp_num)
		self.dp_info_list = []
		for i in range(self.dp_num):
			block = mod.block(0x30)
			dp_info = CDpInfo(self.cur_n1_block_index)
			dp_info.read(block)
			self.cur_n1_block_index += dp_info.n1_block_count
			self.dp_info_list.append(dp_info)
			
		# reindexing
		batch_id = 1
		for i, cur_dp_info in enumerate(self.dp_info_list):
			cur_dp_info.batch_id = batch_id
			material_name = self.material_names[cur_dp_info.material_index]
			print("\t[UseMat]:%s" % material_name)
			print("\tBatch:%d" % batch_id, end=' ')
			cur_dp_info.print_unknowns()
			print()
			if i + 1 >= len(self.dp_info_list):
				break
			next_dp_info = self.dp_info_list[i + 1]
			if cur_dp_info != next_dp_info:
				batch_id += 1			
			
	def read_unknown1(self, mod):
		print("n1 = %d, @offset: 0x%x - 0x%x" % (self.n1, mod.offset,
												 mod.offset + self.n1 * 0x90))
		self.n1_block_list = []
		# getter.skip(n1 * 0x90)
		for i in range(self.n1):
			print(mod.get("I7f"))
			vec1 = mod.get("3f")
			reserved_0 = mod.get("I")
			assert reserved_0 == 0
			vec2 = mod.get("3f")
			reserved_1 = mod.get("I")
			assert reserved_1 == 0			
			#print "min", vec1
			#print "max", vec2
			#print "==========="
			mat = []
			for i in range(4):
				mat.append(mod.get("4f"))
			#for row in mat:
			#	print row
			#print "==========="

			vec3 = mod.get("3f")
			reserved_2 = mod.get("I")
			assert reserved_2 == 0
			#print "vec", vec3
			#print
			
			self.n1_block_list.append((numpy.matrix([mat[0], mat[1], mat[2], mat[3]]),
									   vec1, vec2, vec3))			
			# print "\t", data
			
	def read_vb(self, mod):
		mod.seek(self.vb_offset)
		self.vb = mod.get_raw(self.vb_size)
	
	def read_ib(self, mod):
		mod.seek(self.ib_offset)
		self.ib = mod.get("%dH" % self.index_num)
		
	def read_not_used(self, mod):
		mod.seek(self.unk_offset)
		n7 = mod.get("I")
		assert n7 == 0
		
	def dump(self, out_path):
		print("-" * 30)
		print("Parsing Primitives:")
		
		if out_path.endswith(".dae"):
			dump_type = DUMP_TYPE_COLLADA
		elif out_path.endswith(".gtb"):
			dump_type = DUMP_TYPE_GTB
		elif out_path.endswith(".obj"):
			dump_type == DUMP_TYPE_OBJ
		else:
			return
			
		# init dump
		if dump_type == DUMP_TYPE_COLLADA:
			collada_doc = collada.Collada()
			root_node = collada.scene.Node("Root", children=[])
			scene = collada.scene.Scene("Scene", [root_node])
			collada_doc.scenes.append(scene)
			collada_doc.scene = scene
		elif dump_type == DUMP_TYPE_GTB:
			gtb = {
				"objects": {},
			}
			if self.bone_num > 0:
				gtb["skeleton"] = {}
				gtb["skeleton"]["name"] = ["Bone%d" % v for v in range(self.bone_num)]
				gtb["skeleton"]["parent"] = [v == 255 and -1 or v for v in self.bone_parent]
				mat_list = []
				for mat in self.bone_mat:
					mat_list.extend(mat.getA1())
				gtb["skeleton"]["matrix"] = mat_list
				gtb["bone_id"] = self.bone_id
				# To support root bone animation, we have to add a virtual 'root' bone
				if IS_SUPPORT_ROOT_BONE_ANIMATION:
					gtb["skeleton"]["name"].append("Bone%d" % self.bone_num)
					for i, parent in enumerate(gtb["skeleton"]["parent"]):
						if parent == -1:
							gtb["skeleton"]["parent"][i] = self.bone_num
					gtb["skeleton"]["parent"].append(-1)
					mat_list.extend(numpy.identity(4).flatten())
					gtb["bone_id"].append(255)

		for dp_index in range(self.dp_num):
			dp_info = self.dp_info_list[dp_index]

			vertices = parse_primitives(self, dp_info)
			indices = self.ib[dp_info.ib_offset: dp_info.ib_offset + dp_info.ib_size]
			util.assert_min_max(indices, dp_info.index_min, dp_info.index_max)
			indices = [v - dp_info.index_min for v in indices]
			assert dp_info.bounding_box_id in self.id_2_bounding_box
			
			# mesh for special use, looks like some outline
			# that's just not useful for usual rendering
			if dp_info.unknowns[0] == 0x1020:
				continue
			
			if dump_type == DUMP_TYPE_OBJ:
				obj_str = dump_obj(vertices, indices)
				fout = open(out_path.replace(".obj", "_%d.obj" % dp_index), "w")
				fout.write(obj_str)
				fout.close()
			elif dump_type == DUMP_TYPE_COLLADA:
				dump_collada(vertices, indices, collada_doc)
			elif dump_type == DUMP_TYPE_GTB:
				material_name = self.material_names[dp_info.material_index]
				dump_gtb(vertices, indices, material_name, gtb)
		
		# finish up dump
		if dump_type == DUMP_TYPE_COLLADA:
			fp = open(out_path, "w")
			collada_doc.write(fp)
			fp.close()
		elif dump_type == DUMP_TYPE_GTB:
			data = json.dumps(gtb, indent=2, sort_keys=True, ensure_ascii=True)
			if COMPRESS:
				fp = open(out_path, "wb")
				fp.write("GTB\x00" + zlib.compress(data))
			else:
				fp = open(out_path, "w")
				fp.write(data)
			fp.close()
	
	
def parse(path):
	load_input_layouts("windbg/input_layouts.json", "windbg/input_layouts2.json")
	
	f = open(path, "rb")
	getter = util.get_getter(f, "<")
	
	model = CModel()
	model.read(getter)
		
	f.close()
	
	model.dump(path.replace(".mod", ".gtb"))
	
	print_bounding_box_check(model)
	
def print_bounding_box_check(model):
	if not all((used_x, used_y, used_z)):
		return
	print("-" * 30)
	calc_min_x = min(used_x)
	calc_max_x = max(used_x)
	calc_min_y = min(used_y)
	calc_max_y = max(used_y)
	calc_min_z = min(used_z)
	calc_max_z = max(used_z)	
	print("X Range [%f, %f]" % (calc_min_x, calc_max_x))
	print("Y Range [%f, %f]" % (calc_min_y, calc_max_y))
	print("Z Range [%f, %f]" % (calc_min_z, calc_max_z))
	# A very rough calculation
	assert abs(calc_min_x - model.min_x) < 1
	assert abs(calc_min_y - model.min_y) < 1
	assert abs(calc_min_z - model.min_z) < 1
	assert abs(calc_max_x - model.max_x) < 1
	assert abs(calc_max_y - model.max_y) < 1
	assert abs(calc_max_z - model.max_z) < 1
	
used_x = set()
used_y = set()
used_z = set()
def parse_primitives(mod, dp_info):
	print(dp_info)
	IA_d3d10 = IA_D3D10[str(dp_info.input_layout_index)]
	IA_game = IA_GAME[dp_info.input_layout_index]
	print("input_layout_index", dp_info.input_layout_index)
	
	# Parse
	vertices = []
	
	# parse referrenced vertex buffer
	vertex_format_size = calc_vertex_format_size(IA_d3d10)	
	getter = util.get_getter(mod.vb, "<")
	getter.seek(dp_info.vb_offset + vertex_format_size * dp_info.index_min)
	for i in range(dp_info.index_min, dp_info.index_max + 1, 1):
		vertex = parse_vertex(getter, IA_d3d10, IA_game)
		if mod.bone_num > 0:
			unnormalize_vertex(vertex, mod.inv_norm_mat)
		
		vertices.append(vertex)
		
		used_x.add(vertex["Position"][0])
		used_y.add(vertex["Position"][1])
		used_z.add(vertex["Position"][2])
		# for k, v in sorted(vertex.iteritems()):
		# 	print k, v
		# print "-" * 10
	return vertices

def dump_obj(vertices, indices):
	obj_lines = []
	for vertex in vertices:
		obj_lines.extend( dump_obj_vertices(vertex) )
	obj_lines.extend( dump_obj_faces(indices) )
	res = "\n".join(obj_lines)
	return res

# dump all primitives to a single dae file
# because pycollada does not yet support skinning yet, we have to stop here, and find
# another way.
def dump_collada(vertices, indices, doc):
	i = len(doc.geometries)
	v0 = vertices[0]
	has_normal = "Normal" in v0
	has_uv = "TexCoord" in v0
	# separate source from interleave data
	pos_list = []
	normal_list = []
	uv_list = []
	for v in vertices:
		pos = v["Position"]
		pos_list.extend(v["Position"][:3])
		if has_normal:
			normal_list.extend(v["Normal"][:3])
		if has_uv:
			uv_list.extend(v["TexCoord"][:2])
				
	# build up collada source and inputlist
	inputlist = collada.source.InputList()
	pos_src = collada.source.FloatSource("pos_src%d" % i, numpy.array(pos_list),
										 ("X", "Y", "Z"))
	src_list = [pos_src]
	inputlist.addInput(0, "VERTEX", "#pos_src%d" % i)
	if has_normal:
		src_list.append( collada.source.FloatSource(
			"normal_src%d" % i, numpy.array(normal_list), ("X", "Y", "Z")
		) )
		inputlist.addInput(0, "NORMAL", "#normal_src%d" % i)
	if has_uv:
		src_list.append( collada.source.FloatSource(
			"uv_src%d" % i, numpy.array(uv_list), ("U", "V")
		) )
		inputlist.addInput(0, "TEXCOORD", "#uv_src%d" % i)
			
	# create a default material
	effect = collada.material.Effect("effect%d" % i, [], "constant")
	mat = collada.material.Material("material%d" % i, "mymaterial%d" % i, effect)
	doc.effects.append(effect)
	doc.materials.append(mat)
	# create primitives
	mesh = collada.geometry.Geometry(doc, "Geometry%d" % i, "Mesh%d" % i, src_list)
	triset = mesh.createTriangleSet(numpy.array(indices), inputlist, "materialref%d" % i)
	mesh.primitives.append(triset)
	doc.geometries.append(mesh)
	# create scene node
	mat_node = collada.scene.MaterialNode("materialref%d" % i, mat, inputs=[])
	geom_node = collada.scene.GeometryNode(mesh, [mat_node])
	doc.scene.nodes[0].children.append(geom_node)

def dump_gtb(vertices, indices, mat_name, gtb):
	v0 = vertices[0]
	
	msh = {"flip_v": 1, "double_sided": 0, "shade_smooth": True,
		   "vertex_num": len(vertices), "index_num": len(indices)}
	msh["textures"] = ((mat_name, 0), )
	msh["indices"] = indices
	msh["position"] = []
	has_normal = "Normal" in v0
	if has_normal:
		msh["normal"] = []
	has_uv = "TexCoord" in v0
	if has_uv:
		msh["uv0"] = []
		msh["uv_count"] = 1
	else:
		msh["uv_count"] = 0
	has_joint = "Joint" in v0
	if has_joint:
		msh["max_involved_joint"] = len(v0["Joint"])
		msh["joints"] = []
		msh["weights"] = []
	else:
		msh["max_involved_joint"] = 0
		
	for v in vertices:
		pos = v["Position"]
		msh["position"].extend(v["Position"][:3])
		if has_normal:
			msh["normal"].extend(v["Normal"][:3])
		if has_uv:
			msh["uv0"].extend(v["TexCoord"][:2])
			
		if has_joint:
			msh["joints"].extend(list(map(int, v["Joint"])))
			weights = v.get("Weight", [])
			msh["weights"].extend(weights)
			weight_lack_num = len(v["Joint"]) - len(weights)
			if weight_lack_num > 0:
				msh["weights"].append(1.0 - sum(weights))
				msh["weights"].extend([0.0] * (weight_lack_num - 1))
				
	
	msh_idx = len(gtb["objects"])
	msh_name = "msh%d" % msh_idx
	gtb["objects"][msh_name] = msh		
			
used_joint_ids = set()
def parse_vertex(getter, IA_d3d10, IA_game):
	offset_attri_list = []
	offset = 0
	for element in IA_d3d10:
		fmt = element["Format"]
		format_size = dxgi_format_parse.get_format_size(fmt)
		attri_data = getter.get_raw(format_size)
		attri = dxgi_format_parse.parse_format(attri_data, fmt)
		attri_norm = dxgi_format_parse.normalize(attri, fmt)
		offset_attri_list.append((offset, offset + format_size, attri, attri_norm))
		offset += format_size
	vertex = {}
	for config in IA_game:
		v = vertex.setdefault(config["sematics"], [])
		fetch_next = False
		fetch_index = 0
		total = config["component_count"] + len(v)
		for offset_beg, offset_end, attri, attri_norm in offset_attri_list:
			if not (fetch_next or offset_beg <= config["offset"] < offset_end):
				continue
			if not fetch_next:
				unit_size = (offset_end - offset_beg) / len(attri)
				fetch_index = (config["offset"] - offset_beg) / unit_size
				fetch_next = True
			to_fetch_count = total - len(v)
			if config["sematics"] == "Joint":
				src = attri
			else:
				src = attri_norm
			v.extend(src[fetch_index: fetch_index + to_fetch_count])
			fetch_index = 0
			fetch_next = (len(v) < total)
	
	global used_joint_ids
	joint_ids = list(map(int, vertex.get("Joint", ())))
	used_joint_ids.update(joint_ids)
				
	return vertex
				
def calc_vertex_format_size(IA_d3d10):
	vertex_format_size = 0
	for element in IA_d3d10:
		format_size = dxgi_format_parse.get_format_size(element["Format"])
		vertex_format_size += format_size
	return vertex_format_size

def unnormalize_vertex(vertex, inv_norm_mat):
	pos = list(vertex["Position"])
	if len(pos) == 2:
		pos.extend([0.0, 1.0])
	elif len(pos) == 3:
		pos.append(1.0)
	assert len(pos) == 4
	pos_mat = numpy.matrix(pos)
	pos_out = (pos_mat * inv_norm_mat).getA1()
	vertex["Position"] = tuple(pos_out)
	
def dump_obj_vertices(vertex):
	obj_lines = []
	pos = vertex["Position"]
	obj_lines.append("v %f %f %f" % (pos[0], pos[1], pos[2]))
	uv = vertex.get("TexCoord", (0.0, 0.0, 0.0, 1.0))
	obj_lines.append("vt %f %f" % (uv[0], uv[1]))
	normal = vertex.get("Normal", (0.0, 0.0, 0.0))
	obj_lines.append("vn %f %f %f" % (normal[0], normal[1], normal[2]))
	return obj_lines

def dump_obj_faces(indices, base=0):
	obj_lines = []
	assert len(indices) % 3 == 0, "DMC4SE uses TRIANGLE_LIST as its only primtive type"
	
	fmt = "%d"
	elem_count = 1
	if DUMP_UV:
		fmt += "/%d"
		elem_count += 1
	if DUMP_NORMAL:
		if not DUMP_UV:
			fmt += "/"
		fmt += "/%d"
		elem_count += 1
	face_fmt = "f %s %s %s" % (fmt, fmt, fmt)
	
	for i in range(0, len(indices), 3):
		args = []
		for j in range(3):
			index = indices[i + j] - base + 1
			args.extend([index] * elem_count)
		obj_lines.append(face_fmt % tuple(args))
		
	return obj_lines
		
def run_test(root, root2, move_when_error=False):
	for model_path in glob.glob(os.path.join(root, "*.MOD")):
		print("parsing:", model_path)
		try:
			parse(model_path)
			error = False
		except AssertionError:
			print("error %s" % model_path, file=sys.stderr)
			error = True
		if error == move_when_error:
			rel_path = os.path.relpath(model_path, root)
			shutil.move(model_path, os.path.join(root2, rel_path))

# verify that sematic names are usually in a fixed order
# POSITION,NORMAL,TANGENT,BINORMAL,
# TEXCOORD,TEXCOORD,TEXCOORD,TEXCOORD,TEXCOORD,TEXCOORD,TEXCOORD
# which can be used to filter a set of valid shaders
def verify_sematic_order(input_layout_descs):
	_sig = ""
	for index, descs in input_layout_descs.items():
		sematic_names = []
		for desc in descs:
			sematic_names.append(desc["SematicName"])
		sig = ",".join(sematic_names)
		if sig.startswith(_sig):
			_sig = sig
			print("sig =", _sig)
		elif _sig.startswith(sig):
			continue
		else:
			return False
	return True
			
def load_json_object(path):
	f = open(path, "r")
	py_obj = json.load(f)
	f.close()
	return py_obj

def load_input_layouts(d3d10_json, game_json):
	global IA_D3D10
	global IA_GAME
	IA_D3D10 = load_json_object(d3d10_json)
	IA_GAME = load_json_object(game_json)
	
def get_material_name_hash(string):
	pass

if __name__ == '__main__':
	# assert verify_sematic_order(input_layout_descs), "sematic name should be in the same order"
	
	if len(sys.argv) > 1:
		if sys.argv[1] == "test":
			run_test("test_models", "work_models", move_when_error=None)
		elif sys.argv[1] == "work":
			run_test("work_models", "test_models", move_when_error=False)
		elif sys.argv[1] == "random":
			rand_path = os.path.join("test_models", random.choice(os.listdir("test_models")))
			print("mod_parser.py %s > log.txt" % rand_path)
			parse(rand_path)
		else:
			parse(sys.argv[1])
	else:	
		parse("st200-m91.MOD")
		
	if used_joint_ids:
		max_joint_id = max(used_joint_ids)
		min_joint_id = min(used_joint_ids)
		print("=" * 30)
		print("Joint Id Range = [%d, %d]" % (min_joint_id, max_joint_id))
		