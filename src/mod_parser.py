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


class CSubMeshInfo(object):
	def read(self, getter):
		# vertex count
		getter.seek(0x2)
		self.vertex_num = getter.get("H")
		# fvf_size
		getter.seek(0xA)
		self.fvf_size = getter.get("B")
		# fvf & 0xFFF
		# fvf & 0xFFFFF
		# ib offset
		getter.seek(0x18)
		self.ib_offset = getter.get("I")
		self.ib_size = getter.get("I")
		# vb offset
		getter.seek(0x10)
		self.vb_offset = getter.get("I")
		# fvf flags: I don't know what is this...
		getter.seek(0x14)
		self.fvf = getter.get("I")
		self.input_layout_index = self.fvf & 0xFFF
		# index min max
		getter.seek(0x28)
		self.index_min = getter.get("H")
		self.index_max = getter.get("H")
		# 	index min duplicated?
		getter.seek(0xC)
		index_min_dup = getter.get("I")
		assert index_min_dup == self.index_min, "0x%x vs 0x%x" % (self.index_min, index_min_dup)
		# cmp id
		getter.seek(0x4)
		# dword @0x4 can be used to generate some kind of hash,
		# will be replaced in memory with the value after hash
		# but after hash, this value if identical to the value before hash
		self.unk1 = getter.get("I")
		unk1 = self.unk1 & 0xFFF000
		getter.seek(0xB)
		self.unk2 = getter.get("B")
		unk2 = self.unk2 & 0x3F		
		self.cmp_id = (self.fvf, self.vb_offset, unk1 >> 12, unk2, self.fvf_size)
		# unknown
		getter.seek(0x25)
		unk5 = getter.get("B")
		getter.seek(0x2C)
		unk6 = getter.get("I")	# will be replaced in memory after hash,
								# pointer to `unk5`th block of size 0x90
		self.submesh_name_index = (self.unk1 >> 12)

		self.unknowns = []
		getter.seek(0x0)
		self.unknowns.append(getter.get("H"))
		getter.seek(0x4)
		self.unknowns.append(getter.get("I"))
		getter.seek(0x8)
		self.unknowns.append(getter.get("H"))
		getter.seek(0xB)
		self.unknowns.append(getter.get("B"))
		getter.seek(0x20)
		self.unknowns.append(getter.get("I"))
		getter.seek(0x24)
		self.unknowns.append(getter.get("B"))
		getter.seek(0x25)
		self.unknowns.append(getter.get("B"))
		getter.seek(0x26)
		self.unknowns.append(getter.get("H"))
		self.unknowns.append(self.unk1 & 0xFFF)

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
	
class CBlock0(object):
	def read(self, getter):
		# out buffer here!!!! disk value is useless
		getter.seek(0x20)
		
		# some kind of matrix here: inverse world?
		# 0x40 ~ 0x8c float
		getter.seek(0x40)
		mat = getter.get("16f")
		
		# some kind of position here?
		getter.get("4f")
			
def parse(path):
	f = open(path, "rb")
	getter = util.get_getter(f, "<")
	
	# header
	header = getter.block(0x80)
	header.seek(0xc)
	vertex_num, indices_num = header.get("2I")
	print "vertex_num", hex(vertex_num)
	header.seek(0x18)
	vb_size = header.get("I")
	
	n1 = getter.get("I")

	header.seek(0x6)
	bone_count = header.get("H")	# bone count
	if bone_count > 0:
		print "reading bone data, bone_count = %d" % bone_count
		print "@offset: 0x%x - 0x%x" % (getter.offset, getter.offset + bone_count * 0x18)
		for bone_index in xrange(bone_count):
			bone_info1 = getter.block(0x18)
			print map(hex, bone_info1.get("BBBB")), bone_info1.get("5f")
		print "@offset: 0x%x - 0x%x" % (getter.offset, getter.offset + bone_count * 0x40)
		# 0x40 is a typical size for a matrix
		for bone_index in xrange(bone_count):
			print getter.get("4f")
			print getter.get("4f")
			print getter.get("4f")
			print getter.get("4f")
			print
		print "@offset: 0x%x - 0x%x" % (getter.offset, getter.offset + bone_count * 0x40)
		for bone_index in xrange(bone_count):
			print getter.get("4f")
			print getter.get("4f")
			print getter.get("4f")
			print getter.get("4f")
			print
		print "@offset: 0x%x - 0x%x" % (getter.offset, getter.offset + 0x100)
		getter.skip(0x100)
	
	# kind of bounding box information
	header.seek(0x20)
	n2 = header.get("I")
	print "n = %d, @offset: 0x%x - 0x%x" % (n2, getter.offset, getter.offset + n2 * 0x20)
	print "bounding box information:", n2
	for i in xrange(n2):
		print "\t", getter.get("8f")
		
	# submesh names
	header.seek(0xa)
	n3 = header.get("H")
	print "submesh names:", n3
	# print "n = %d, @offset: 0x%x - 0x%x" % (n3, getter.offset, getter.offset + n3 * 0x80)
	for i in xrange(n3):
		print "\t", getter.get("128s").rstrip("\x00")
	
	####################
	# The following two blocks are related!!!
	header.seek(0x8)
	n4 = header.get("H")
	print "n = %d, @offset: 0x%x - 0x%x" % (n4, getter.offset, getter.offset + n4 * 0x30)
	submesh_info_list = []
	for i in xrange(n4):
		blk_submesh_info = getter.block(0x30)
		info = CSubMeshInfo()
		info.read(blk_submesh_info)
		submesh_info_list.append(info)
		
		
	# reindexing
	mesh_id = 1
	for i, cur_submesh_info in enumerate(submesh_info_list):
		cur_submesh_info.mesh_id = mesh_id
		print "\t", mesh_id, map(hex, info.unknowns)
		if i + 1 >= len(submesh_info_list):
			break
		next_submesh_info = submesh_info_list[i + 1]
		if cur_submesh_info != next_submesh_info:
			mesh_id += 1
		
	print "n1 = %d, @offset: 0x%x - 0x%x" % (n1, getter.offset, getter.offset + n1 * 0x90)
	# getter.skip(n1 * 0x90)
	for i in xrange(n1):
		print getter.get("8f")
		print getter.get("8f")
		mat = []
		for i in xrange(4):
			mat.append(getter.get("4f"))
			print mat[-1]
		print "==========="
		print getter.get("4f")
		print
		# print "\t", data
	
	# vertex buffer
	print "vbsize = 0x%x, @offset: 0x%x - 0x%x" % (vb_size, getter.offset, getter.offset + vb_size)
	# if vb_size % vertex_num != 0 or vb_size / vertex_num != 0x18:
	# 	raise Exception("oh ~~~ no")
	print "vertex size = 0x%x" % (vb_size / vertex_num)
	# for i in xrange(vertex_num):
	# 	pos = getter.get("3f")
	# 	unk1 = getter.get("I")
	# 	uv = numpy.frombuffer(getter.get_raw(4), dtype=numpy.dtype("<f2"))
	# 	unk2 = getter.get("I")
	# 	# print pos, (uv[0], uv[1])
	# 	print hex(unk1), hex(unk2)
	vb = getter.get_raw(vb_size)
	
	# index buffer
	print "indices:"
	print "n = 0x%x, @offset: 0x%x - 0x%x" % (indices_num, getter.offset,
											getter.offset + indices_num * 0x2)
	indices = getter.get("%dH" % indices_num)
	# print indices
	
	getter.align(0x4)

	n7 = getter.get("I")
	assert n7 == 0, "not supported yet!"
	getter.assert_end()
	
	for i, submesh_info in enumerate(submesh_info_list):
		print "=============="
		obj_file_str = dump_obj(submesh_info, vb, indices)
		f_obj = open("objs/%d.obj" % i, "w")
		f_obj.write(obj_file_str)
		f_obj.close()
		
	f.close()
	
def dump_obj(submesh_info, vb, indices):
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
		print vertex
		try:
			vertex_trans = input_layout.parse(vertex, submesh_info.input_layout_index)
		except:
			vertex_trans = vertex
			unsupported_input_layout = True
		# transform vertex data to its real meaning
		pos = vertex_trans["POSITION"]
		obj_lines.append("v %f %f %f" % (pos[0], pos[1], pos[2]))
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