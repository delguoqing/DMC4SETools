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

DUMP_OBJ = True
DUMP_OBJ_WRITE_NORMAL = True
DUMP_OBJ_WRITE_UV = True

IA_D3D10 = None
IA_GAME = None

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
		print "n1_idx:[%d, %d)" % (self.n1_block_start_index, self.n1_block_end_index),
		#print "cmp_id_", map(hex, self.cmp_id),
		print "unknowns:", map(hex, self.unknowns)
		
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
		self.inv_world_translation = header.get("3f", offset=0x40)	# ?
		self.world_scale_factor = header.get("f", offset=0x4c)		# ?
		print "inv_world_translation:", self.inv_world_translation
		print "world_scale_factor:", self.world_scale_factor
		
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
		
		print "dumping dp"
		for dp_index in xrange(self.dp_num):
			dp_info = self.dp_info_list[dp_index]

			# input_layout_desc = input_layout_descs[str(dp_info.input_layout_index)]
			# print "input_layout_index", dp_info.input_layout_index
			# for input_element in input_layout_desc:
			# 	print "%s%d: %d" % (input_element["SematicName"], input_element["SematicIndex"],
			# 						input_element["Format"])
		
			assert dp_info.bounding_box_id in self.id_2_bounding_box
		
			obj_str = dump_obj(self, dp_info)
			if DUMP_OBJ:
				fout = open("objs/dp_%d.obj" % dp_index, "w")
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
			vals = mod.get("I7f")
			self.id_2_bounding_box[vals[0]] = vals
			print "\t", vals
			
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
			
	def read_dp(self, mod):
		mod.seek(self.primitives_offset)
		print "dp infos:", self.dp_num
		self.dp_info_list = []
		for i in xrange(self.dp_num):
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
			print "\t[UseMat]:%s" % material_name
			print "\tBatch:%d" % batch_id,
			cur_dp_info.print_unknowns()
			print
			if i + 1 >= len(self.dp_info_list):
				break
			next_dp_info = self.dp_info_list[i + 1]
			if cur_dp_info != next_dp_info:
				batch_id += 1			
			
	def read_unknown1(self, mod):
		print "n1 = %d, @offset: 0x%x - 0x%x" % (self.n1, mod.offset,
												 mod.offset + self.n1 * 0x90)
		self.n1_block_list = []
		# getter.skip(n1 * 0x90)
		for i in xrange(self.n1):
			print mod.get("I7f")
			vec1 = mod.get("3f")
			reserved_0 = mod.get("I")
			assert reserved_0 == 0
			vec2 = mod.get("3f")
			reserved_1 = mod.get("I")
			assert reserved_1 == 0			
			print "min", vec1
			print "max", vec2
			print "==========="
			mat = []
			for i in xrange(4):
				mat.append(mod.get("4f"))
				print mat[-1]
			print "==========="

			vec3 = mod.get("3f")
			reserved_2 = mod.get("I")
			assert reserved_2 == 0
			print "vec", vec3
			print
			
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
	
def parse(path):
	load_input_layouts("windbg/input_layouts.json", "windbg/input_layouts2.json")
	
	f = open(path, "rb")
	getter = util.get_getter(f, "<")
	
	model = CModel()
	model.read(getter)
		
	f.close()
	
def dump_obj(mod, dp_info):
	print dp_info
	IA_d3d10 = IA_D3D10[str(dp_info.input_layout_index)]
	IA_game = IA_GAME[dp_info.input_layout_index]
	print "input_layout_index", dp_info.input_layout_index
	
	# Parse
	vertices = []
	
	# remap position to the correct value range
	n1_block_index = dp_info.n1_block_start_index
	bb_min = mod.n1_block_list[n1_block_index][1]
	bb_max = mod.n1_block_list[n1_block_index][2]
	
	# parse referrenced vertex buffer
	vertex_format_size = calc_vertex_format_size(IA_d3d10)	
	getter = util.get_getter(mod.vb, "<")
	getter.seek(dp_info.vb_offset + vertex_format_size * dp_info.index_min)
	for i in xrange(dp_info.index_min, dp_info.index_max + 1, 1):
		vertex = parse_vertex(getter, IA_d3d10, IA_game)
		vertices.append(vertex)
		for k, v in sorted(vertex.iteritems()):
			print k, v
		print "-" * 10
	# Dump
	if not DUMP_OBJ:
		return ""
	indices = mod.ib[dp_info.ib_offset: dp_info.ib_offset + dp_info.ib_size]
	util.assert_min_max(indices, dp_info.index_min, dp_info.index_max)
	obj_lines = []
	for vertex in vertices:
		obj_lines.extend( dump_obj_vertices(vertex) )
	obj_lines.extend( dump_obj_faces(indices, dp_info.index_min) )
	res = "\n".join(obj_lines)
	return res

def parse_vertex(getter, IA_d3d10, IA_game):
	offset_attri_list = []
	offset = 0
	for element in IA_d3d10:
		format_size = dxgi_format_parse.get_format_size(element["Format"])
		attri_data = getter.get_raw(format_size)
		attri = dxgi_format_parse.parse_format(attri_data, element["Format"])
		attri_int = dxgi_format_parse.parse_format_int(attri_data, element["Format"])
		offset_attri_list.append((offset, offset + format_size, attri, attri_int))
		offset += format_size
	vertex = {}
	for config in IA_game:
		v = vertex.setdefault(config["sematics"], [])
		fetch_next = False
		fetch_index = 0
		total = config["component_count"] + len(v)
		for offset_beg, offset_end, attri, attri_int in offset_attri_list:
			if not (offset_beg <= config["offset"] < offset_end):
				continue
			if not fetch_next:
				unit_size = (offset_end - offset_beg) / len(attri)
				fetch_index = (config["offset"] - offset_beg) / unit_size
				fetch_next = True
			to_fetch_count = total - len(v)
			if config["sematics"] == "Joint":
				v.extend(attri_int[fetch_index: fetch_index + to_fetch_count])
			else:
				v.extend(attri[fetch_index: fetch_index + to_fetch_count])
			fetch_index = 0
	return vertex
				
def calc_vertex_format_size(IA_d3d10):
	vertex_format_size = 0
	for element in IA_d3d10:
		format_size = dxgi_format_parse.get_format_size(element["Format"])
		vertex_format_size += format_size
	return vertex_format_size

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
	if DUMP_OBJ_WRITE_UV:
		fmt += "/%d"
		elem_count += 1
	if DUMP_OBJ_WRITE_NORMAL:
		if not DUMP_OBJ_WRITE_UV:
			fmt += "/"
		fmt += "/%d"
		elem_count += 1
	face_fmt = "f %s %s %s" % (fmt, fmt, fmt)
	
	for i in xrange(0, len(indices), 3):
		args = []
		for j in xrange(3):
			index = indices[i + j] - base + 1
			args.extend([index] * elem_count)
		obj_lines.append(face_fmt % tuple(args))
		
	return obj_lines
		
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