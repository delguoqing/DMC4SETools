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

from d3d10 import dxgi_format_parse

f = open("windbg/input_layouts.json", "r")
input_layout_descs = json.load(f)
f.close()

class CBatchInfo(object):
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
		unk1 = self.unk1 & 0xFFF000
		self.unk2 = getter.get("B", offset=0xB)
		unk2 = self.unk2 & 0x3F
		
		# cmp id
		self.cmp_id = (self.fvf, self.vb_offset, unk1 >> 12, unk2, self.fvf_size)
		# unknown
		unk5 = getter.get("B", offset=0x25)
		unk6 = getter.get("I", offset=0x2c)	# will be replaced in memory after hash,
								# pointer to `unk5`th block of size 0x90
		self.material_index = (self.unk1 >> 12) & 0xFFF
		
		self.n1_block_index = getter.get("B", offset=0x25)
		
		# no use, will be assigned at runtime
		batch_index = getter.get("H", offset=0x26)
		
		self.unknowns = []
		self.unknowns.append(getter.get("H", offset=0x0))	# size ok
		v = getter.get("I", offset=0x4)
		self.unknowns.append(v >> 24)						# size ok
		self.unknowns.append(v & 0xFFF)						# size ok
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
		# print self.unknowns
		print "material_index:", self.material_index, "n1_idx:", self.n1_block_index, "unknowns:",
		print map(hex, self.unknowns)
		
class CModel(object):
	
	def __init__(self):
		self.material_names = []
		self.header = None
		
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
		self.batch_num = header.get("H", 0x8)
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
		self.inv_world_translation = header.get("3f", offset=0x40)	# ?
		self.world_scale_factor = header.get("f", offset=0x4c)		# ?
		
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
		print "bounding box: (%f, %f, %f) - (%f, %f, %f)" % self.bounding_box
		
		self.n1 = mod.get("I")
		#assert self.n1 == self.batch_num
		#return
		self.read_bone(mod)
		self.read_bounding_box(mod)
		self.read_material_names(mod)
		self.read_batch(mod)
		self.read_unknown1(mod)
		self.read_vb(mod)	
		self.read_ib(mod)
		self.read_not_used(mod)
		mod.assert_end()
		
		print "dumping dp"
		for batch_index in xrange(self.batch_num):
			batch_info = self.batch_info_list[batch_index]
			obj_str = dump_obj(self, batch_info, self.vb, self.indices)
			fout = open("objs/batch_%d.obj" % batch_index, "w")
			fout.write(obj_str)
			fout.close()
			
	def read_bone(self, mod):
		if self.bone_num <= 0:
			return
		mod.seek(self.bone_info_offset)
		print "reading bone data, bone_num = %d" % self.bone_num
		print "@offset: 0x%x - 0x%x" % (mod.offset, mod.offset + self.bone_num * 0x18)
		for bone_index in xrange(self.bone_num):
			bone_info1 = mod.block(0x18)
			print map(hex, bone_info1.get("BBBB")), bone_info1.get("5f")
		print "@offset: 0x%x - 0x%x" % (mod.offset, mod.offset + self.bone_num * 0x40)
		# 0x40 is a typical size for a matrix
		for bone_index in xrange(self.bone_num):
			print mod.get("4f")
			print mod.get("4f")
			print mod.get("4f")
			print mod.get("4f")
			print
		print "@offset: 0x%x - 0x%x" % (mod.offset, mod.offset + self.bone_num * 0x40)
		for bone_index in xrange(self.bone_num):
			print mod.get("4f")
			print mod.get("4f")
			print mod.get("4f")
			print mod.get("4f")
			print
		print "@offset: 0x%x - 0x%x" % (mod.offset, mod.offset + 0x100)
		mod.skip(0x100)
	
	# not even read by the game
	def read_bounding_box(self, mod):
		mod.seek(self.n2_array_offset)
		print "bounding box: %d" % self.n2
		for i in xrange(self.n2):
			print "\t", mod.get("I7f")
			
	def read_material_names(self, mod):
		mod.seek(self.material_names_offset)
		print "n = %d, @offset: 0x%x - 0x%x" % (self.material_num, mod.offset,
												mod.offset + self.material_num * 0x80)
		for i in xrange(self.material_num):
			material_name = mod.get("128s").rstrip("\x00")
			self.material_names.append(material_name)
			
		print "material names:"
		for material_name in self.material_names:
			print "\t", material_name
			
	def read_batch(self, mod):
		mod.seek(self.primitives_offset)
		print "dp infos:", self.batch_num
		self.batch_info_list = []
		for i in xrange(self.batch_num):
			block = mod.block(0x30)
			batch_info = CBatchInfo()
			batch_info.read(block)
			self.batch_info_list.append(batch_info)
			
		# reindexing
		mesh_id = 1
		for i, cur_batch_info in enumerate(self.batch_info_list):
			cur_batch_info.mesh_id = mesh_id
			material_name = self.material_names[cur_batch_info.material_index]
			print "\t", material_name
			print "\t", mesh_id,
			cur_batch_info.print_unknowns()
			print
			if i + 1 >= len(self.batch_info_list):
				break
			next_batch_info = self.batch_info_list[i + 1]
			if cur_batch_info != next_batch_info:
				mesh_id += 1			
			
	def read_unknown1(self, mod):
		print "n1 = %d, @offset: 0x%x - 0x%x" % (self.n1, mod.offset,
												 mod.offset + self.n1 * 0x90)
		self.n1_block_list = []
		# getter.skip(n1 * 0x90)
		for i in xrange(self.n1):
			print mod.get("8f")
			print mod.get("8f")
			mat = []
			print "==========="
			for i in xrange(4):
				mat.append(mod.get("4f"))
				print mat[-1]
			self.n1_block_list.append(numpy.matrix([mat[0], mat[1], mat[2], mat[3]]))
			print "==========="
			print mod.get("4f")
			print
			# print "\t", data
			
	def read_vb(self, mod):
		mod.seek(self.vb_offset)
		self.vb = mod.get_raw(self.vb_size)
	
	def read_ib(self, mod):
		mod.seek(self.ib_offset)
		self.indices = mod.get("%dH" % self.index_num)
		
	def read_not_used(self, mod):
		mod.seek(self.unk_offset)
		n7 = mod.get("I")
		assert n7 == 0
	
def parse(path):
	f = open(path, "rb")
	getter = util.get_getter(f, "<")
	
	model = CModel()
	model.read(getter)
		
	f.close()
	
def dump_obj(mod, submesh_info, vb, indices):
	getter = util.get_getter(vb, "<")
	print "vb_offset = 0x%x, fvf_size=0x%x, fvf=0x%x, vertex_num=%d" % (
		submesh_info.vb_offset, submesh_info.fvf_size, submesh_info.fvf, submesh_info.vertex_num)
	
	used_indices = indices[submesh_info.ib_offset: submesh_info.ib_offset + submesh_info.ib_size]
	min_index = min(used_indices)
	max_index = max(used_indices)
	assert min_index == submesh_info.index_min and max_index == submesh_info.index_max
	
	obj_lines = []
	
	vertices = []
	getter.seek(submesh_info.vb_offset)
	
	input_layout_desc = input_layout_descs[str(submesh_info.input_layout_index)]
	print "input_layout_index", submesh_info.input_layout_index
	
	# parse referrenced vertex buffer
	unsupported_input_layout = False
	world_matrix = mod.n1_block_list[submesh_info.n1_block_index].getI()
	for i in xrange(submesh_info.index_max + 1):
		# read vertex data using input layout
		vertex = {}
		for element in input_layout_desc:
			format_size = dxgi_format_parse.get_format_size(element["Format"])
			attri_data = getter.get_raw(format_size)
			attri = dxgi_format_parse.parse_format(attri_data, element["Format"])
			if element["SematicName"] not in vertex:
				vertex[element["SematicName"]] = attri
			else:
				vertex[element["SematicName"] + str(element["SematicIndex"])] = attri
		try:
			vertex_trans = input_layout.parse(vertex, submesh_info.input_layout_index)
		except:
			vertex_trans = vertex
			unsupported_input_layout = True
		# transform vertex data to its real meaning
		pos = vertex_trans["POSITION"]
		assert mod.min_x <= pos[0] <= mod.max_x
		assert mod.min_y <= pos[1] <= mod.max_y
		assert mod.min_z <= pos[2] <= mod.max_z
		
		np_pos = (pos[0] - mod.inv_world_translation[0],
				  pos[1] - mod.inv_world_translation[1],
				  pos[2] - mod.inv_world_translation[2],)
		np_pos = pos
		#np_pos = (numpy.matrix([pos[0], pos[1], pos[2], 1.0]) * world_matrix).getA1()
		#print pos
		#print np_pos[0], np_pos[1], np_pos[2]
		obj_lines.append("v %f %f %f" % (np_pos[0], np_pos[1], np_pos[2]))
		uv = vertex_trans.get("TEXCOORD", (0.0, 0.0, 0.0, 1.0))
		obj_lines.append("vt %f %f" % (uv[0], uv[1]))
		normal = vertex_trans.get("NORMAL", (0.0, 0.0, 0.0))
		obj_lines.append("vn %f %f %f" % (normal[0], normal[1], normal[2]))

	# assert not unsupported_input_layout, "unsupported input layout %d" % submesh_info.input_layout_index
	
	# faces
	assert len(used_indices) % 3 == 0
	for i in xrange(len(used_indices) / 3):
		i1 = used_indices[i * 3] + 1
		i2 = used_indices[i * 3 + 1] + 1
		i3 = used_indices[i * 3 + 2] + 1
		obj_lines.append("f %d/%d/%d %d/%d/%d %d/%d/%d" % (i1, i1, i1, i2, i2, i2, i3, i3, i3))
		
	res = "\n".join(obj_lines)
	return res
		
def reindex_submesh_info():
	# psudo code for reindexing submesh info
	# next_idx = 1
	# for i in xrange(n4):
	# 	info[i][0x26] = (short)next_idx
	# 	if i + 1 >= n4:
	# 		break
	# 	if info[i][0x14] != info[i + 1][0x14]:
	# 		next_idx += 1
	# 		break
	#	# vb offset
	# 	if info[i][0x10] != info[i + 1][0x10]:
	# 		next_idx += 1
	# 		break
	#	# looks like bitflag
	# 	if ((info[i][0x4] ^ info[i + 1][0x4]) & 0xFFF000) != 0:
	# 		next_idx += 1
	# 		break
	#	# looks like bitflag
	# 	if (((byte)info[i][0xB] ^ (byte)info[i + 1][0xB]) & 0x00003F) != 0:
	# 		next_idx += 1
	# 		break
	# 	if (byte)info[i][0xA] != (byte)info[i + 1][0xA]:
	# 		next_id += 1
	# 		break
	pass
		
def run_test(root, root2, move_when_error=False):
	for model_path in glob.glob(os.path.join(root, "*.MOD")):
		print "parsing:", model_path
		try:
			parse(model_path)
			error = False
		except AssertionError:
			print >> sys.stderr, "error %s" % model_path
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
	for index, descs in input_layout_descs.iteritems():
		sematic_names = []
		for desc in descs:
			sematic_names.append(desc["SematicName"])
		sig = ",".join(sematic_names)
		if sig.startswith(_sig):
			_sig = sig
			print "sig =", _sig
		elif _sig.startswith(sig):
			continue
		else:
			return False
	return True
			
if __name__ == '__main__':
	# assert verify_sematic_order(input_layout_descs), "sematic name should be in the same order"
	
	if len(sys.argv) > 1:
		if sys.argv[1] == "test":
			run_test("test_models", "work_models", move_when_error=None)
		elif sys.argv[1] == "work":
			run_test("work_models", "test_models", move_when_error=False)
		elif sys.argv[1] == "random":
			rand_path = os.path.join("test_models", random.choice(os.listdir("test_models")))
			print "mod_parser.py %s > log.txt" % rand_path
			parse(rand_path)
		else:
			parse(sys.argv[1])
	else:	
		parse("st200-m91.MOD")