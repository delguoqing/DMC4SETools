import sys
import util

class LMT(object):
	
	def read(self, getter):
		fourcc = getter.get("4s")
		assert fourcc == "LMT\x00"
		field_4 = getter.get("H")
		assert field_4 == 0x43
		# motion count
		count_6 = getter.get("H")
		# motion list
		struc_6_list = []
		struc_6_offset_list = getter.get("%dI" % count_6, force_tuple=True)
		for offset in struc_6_offset_list:
			if offset == 0:
				continue
			getter.seek(offset)
			print "======================"
			print "motion offset =", hex(offset)
			_struc_6 = struc_6()
			_struc_6.read(getter.block(0x3c), getter)
			struc_6_list.append(_struc_6)
			print 
			
# motion
class struc_6(object):
	
	SIZE = 0x3c
	
	def read(self, getter, lmt):
		get = getter.get
		struc_7_arr_offset = getter.get("I")
		struc_7_arr_size = getter.get("I")
		getter.skip(43)
		field_33 = getter.get("B")
		offset_34 = getter.get("I")
		
		if (field_33 & 1) == 0:
			struc_7_list = []
			lmt.seek(struc_7_arr_offset)
			for i in xrange(struc_7_arr_size):
				_struc_7 = struc_7()
				_struc_7.read(lmt.block(0x24), lmt)
				struc_7_list.append(_struc_7)
		
		if offset_34 != 0:
			print "offset_34 = 0x%x, flag=%d" % (offset_34, (field_33 & 2 == 0))
			if (field_33 & 2) == 0:
				getter.seek(offset_34)
				_struc_8 = struc_8()
				_struc_8.read(getter.block(struc_8.SIZE), getter)
		
# bone keyframe
class struc_7(object):
	
	SIZE = 0x24
	
	def read(self, getter, lmt):
		# print "struc_7 offset = 0x%x" % lmt.offset
		get = getter.get
		flag_0 = getter.get("I")
		# track type
		type_0 = flag_0 & 0xFF
		# track type
		# 0 - rotation
		# 1 - position
		# 2 - scale
		# 3 - rotation used by bone_index 0xFF
		# 4 - position used by bone_index 0xFF
		# 5 - scale used by bone_index 0xFF
		type_1 = (flag_0 >> 8) & 0xFF
		type_2 = (flag_0 >> 16) & 0xFF
		# bone index
		bone_index = (flag_0 >> 24)
		
		float_4 = getter.get("f")
		size_of_offset_C = getter.get("I")
		offset_C = getter.get("I")
		unk = getter.get("4f")
		offset_20 = getter.get("I")	# points to struc_9, size = 0x20
									# keyframes
		if (offset_20 != 0 and \
			(type_0 > 9 or type_0 in (4, 5, 7))):
			offset_20 = offset_20
			_struc_9 = struc_9()
			_struc_9.read(getter)
		else:
			assert offset_20 == 0
		print "track: type_0=%d, type_1=%d, type_2=%d, bone_index=0x%x, size=0x%x" % (
			type_0, type_1, type_2, bone_index, size_of_offset_C)
		if type_1 in (0, 3):
			print "ROTATION",
			util.assert_quat(unk)
		elif type_1 in (1, 4):
			print "POSITION",
		elif type_1 in (2, 5):
			print "SCALE   ",
		else:
			assert False, "unsupported type! %d" % type_1
		print unk
		print
			
class struc_8(object):
	
	SIZE = 0x120
	
	def read(self, getter, lmt):
		get = getter.get
		
		

class struc_9(object):
	
	SIZE = 0x20
	
	def read(self, getter):
		pass
	
def parse(lmt_path):
	f = open(lmt_path, "rb")
	getter = util.get_getter(f, "<")

	lmt = LMT()
	lmt.read(getter)
	
	f.close()

if __name__ == '__main__':
	parse(sys.argv[1])
