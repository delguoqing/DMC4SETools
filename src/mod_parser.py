import os
import glob
import shutil
import sys
import numpy
import random
import math
import util

fvf_2_fvf_size = {}
pos_is_4h = set()
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
		unk1 = getter.get("I") & 0xFFF000
		getter.seek(0xB)
		unk2 = getter.get("B") & 0x3F		
		self.cmp_id = (self.fvf, self.vb_offset, unk1, unk2, self.fvf_size)
		# unknown
		getter.seek(0x25)
		unk5 = getter.get("B")
		getter.seek(0x2C)
		unk6 = getter.get("I")	# will be replaced in memory after hash,
								# pointer to `unk5`th block of size 0x90

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
	n0 = header.get("H")
	if n0 != 0:
		# print "reading something special"
		# print "@offset: 0x%x - 0x%x" % (getter.offset, getter.offset + n0 * 0x18)
		getter.skip(n0 * 0x18)
		# print "@offset: 0x%x - 0x%x" % (getter.offset, getter.offset + n0 * 0x40)
		getter.skip(n0 * 0x40)
		# print "@offset: 0x%x - 0x%x" % (getter.offset, getter.offset + n0 * 0x40)
		getter.skip(n0 * 0x40)
		# print "@offset: 0x%x - 0x%x" % (getter.offset, getter.offset + 0x100)
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
	print "submesh:", n3
	print "n = %d, @offset: 0x%x - 0x%x" % (n3, getter.offset, getter.offset + n3 * 0x80)
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
		if cur_submesh_info.cmp_id != next_submesh_info.cmp_id:
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
		if submesh_info.fvf in fvf_2_fvf_size:
			assert submesh_info.fvf_size == fvf_2_fvf_size[submesh_info.fvf]
		else:
			fvf_2_fvf_size[submesh_info.fvf] = submesh_info.fvf_size
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
	
	# parse referrenced vertex buffer
	for i in xrange(submesh_info.index_max + 1):
		vertex = getter.block(submesh_info.fvf_size)
		if submesh_info.fvf in (0x926fd02f, 0x49b4f02a, 0x207d6038, 0xa7d7d037, 0xd8297029,
								0xb86de02b, 0xd1a47039, 0x5e7f202d, 0xa14e003d, 0xafa6302e,
								0x9399c034, 0x63b6c030):
			pos = vertex.get("fff")
		elif submesh_info.fvf in (0xcb68016, 0xdb7da015, 0xa013501f, 0x14d40021,
								  0xa320c017, 0xbb424025, 0xd84e3027, 0x77d87023,
								  0xb0983014, 0xa8fab019, 0xcbf6c01b, 0xc31f201d, ):
			pos = vertex.get("hhhh")
			pos = (pos[0] / 32767.0, pos[1] / 32767.0, pos[2] / 32767.0, pos[3] / 32767.0)
		else:
			assert False, "unsupported vertex format 0x%x" % submesh_info.fvf
		obj_lines.append("v %f %f %f" % (pos[0], pos[1], pos[2]))

	# faces
	assert len(used_indices) % 3 == 0
	for i in xrange(len(used_indices) / 3):
		i1 = used_indices[i * 3] + 1
		i2 = used_indices[i * 3 + 1] + 1
		i3 = used_indices[i * 3 + 2] + 1
		obj_lines.append("f %d %d %d" % (i1, i2, i3))
		
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

# possible fvf and fvf size
# 0xb0983014: 0xc
# 0xdb7da015: 0x10
# 0xcb68016: 0x14
# 0xa7d7d037: 0x14
# 0xa8fab019: 0x14
# 0x207d6038: 0x18
# 0xc31f201d: 0x18
# 0xcbf6c01b: 0x18
# 0xd1a47039: 0x18
# 0xd8297029: 0x18
# 0x14d40021: 0x1c
# 0x49b4f02a: 0x1c
# 0x5e7f202d: 0x1c
# 0xa013501f: 0x1c
# 0xa14e003d: 0x1c
# 0xa320c017: 0x1c
# 0xafa6302e: 0x1c
# 0x926fd02f: 0x20
# 0x9399c034: 0x20
# 0xb86de02b: 0x20
# 0x63b6c030: 0x24
# 0xbb424025: 0x24
def check_fvf(self):
	if fvf != 0x2F55C03E:
		if fvf != 0x4325A03F:
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
		
if __name__ == '__main__':
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
		print "fucker?"
		for a in pos_is_4h:
			print "0x%x" % a
	else:	
		parse("st200-m91.MOD")
		
	vk = []
	for k, v in fvf_2_fvf_size.iteritems():
		vk.append((v, k))
	vk.sort()
	for v, k in vk:
		print "0x%x, 0x%x: 0x%x" % (k & 0xFFF, k >> 12, v)