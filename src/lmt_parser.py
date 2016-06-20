import sys
import util

class LMT(object):
	
	def read(self, getter):
		fourcc = getter.get("4s")
		assert fourcc == "LMT\x00"
		reserved = getter.get("H")
		assert reserved == 0x43
		# motion count
		motion_num = getter.get("H")
		# motion list
		motion_list = []
		motion_offset_list = getter.get("%dI" % motion_num, force_tuple=True)
		for motion_offset in motion_offset_list:
			if motion_offset == 0:
				continue
			getter.seek(motion_offset)
			print "======================"
			print "motion offset = 0x%x" % motion_offset
			_motion = motion()
			_motion.read(getter.block(0x3c), getter)
			motion_list.append(_motion)
			print 
			
# motion
class motion(object):
	
	SIZE = 0x3c
	
	def read(self, getter, lmt):
		get = getter.get
		#print get("IIIi")
		#print get("f4BfI")
		#print get("IIIf")
		#print get("4BII")
		
		track_off = getter.get("I")
		track_num = getter.get("I")
		getter.skip(40)
		field_30 = getter.get("I")
		field_33 = (field_30 >> 24) & 0xFF
		offset_34 = getter.get("I")
		offset_38 = getter.get("I")
		
		if (field_33 & 1) == 0:
			track_list = []
			lmt.seek(track_off)
			for track_index in xrange(track_num):
				print "track offset = 0x%x" % (track_off + track_index * track.SIZE)
				lmt.seek(track_off + track_index * track.SIZE)
				_track = track()
				_track.read(lmt.block(track.SIZE), lmt)
				track_list.append(_track)
		
		if offset_34 != 0:
			print "offset_34 = 0x%x, flag=%d" % (offset_34, (field_33 & 2 == 0))
			if (field_33 & 2) == 0:
				getter.seek(offset_34)
				_struc_8 = struc_8()
				_struc_8.read(getter.block(struc_8.SIZE), getter)
		
		if (field_30 >> 16) & 0x1F:
			# offset_38 is valid
			print "offset_38 = 0x%x" % offset_38
			if field_30 & 0x4000000:
				n = (field_30 >> 16) & 0x1F
				
# bone keyframe
class track(object):
	
	SIZE = 0x24
	
	def read(self, getter, lmt):
		# print "track offset = 0x%x" % lmt.offset
		get = getter.get
		flag_0 = getter.get("I")
		# track type
		type_0 = flag_0 & 0xFF
		# track type
		# 0 - rotation
		# 1 - position
		# 2 - scale
		# 3 - rotation used by bone_id 0xFF
		# 4 - position used by bone_id 0xFF
		# 5 - scale used by bone_id 0xFF
		type_1 = (flag_0 >> 8) & 0xFF
		type_2 = (flag_0 >> 16) & 0xFF
		# bone id
		bone_id = (flag_0 >> 24)
		
		float_4 = getter.get("f")
		size_of_offset_C = getter.get("I")
		offset_C = getter.get("I")
		unk = getter.get("4f")
		offset_20 = getter.get("I")	# points to struc_9, size = 0x20
									# keyframes? need keyframe count!
				
		# type_0:
		# 0, 1: no keyframe
		# 2: no keyframe?
		# we got a look up table @10ADE60, each element is of size 0xC
		#       (keyframe size, get keyframe time, get value)
		
		
		if offset_C != 0:
			print "checking offset_C = 0x%x, size = 0x%x" % (offset_C, size_of_offset_C)
			lmt.seek(offset_C)
			a = lmt.block(size_of_offset_C)
			if type_0 == 4:
				assert size_of_offset_C % 0x8 == 0
				for ki in xrange(size_of_offset_C / 8):
					print 
			
		if (offset_20 != 0 and \
			(type_0 > 9 or type_0 in (4, 5, 7))):
			offset_20 = offset_20
			print "offset_20 = 0x%x" % offset_20
			lmt.seek(offset_20)
			_struc_9 = struc_9()
			_struc_9.read(lmt.block(struc_9.SIZE))
		else:
			assert offset_20 == 0
		print "track: type_0=%d, type_1=%d, type_2=%d, bone_id=%d, float_4=%f" % (
			type_0, type_1, type_2, bone_id, float_4)
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
		
		# assert model root transformation
		if 3 <= type_1 <= 5:
			assert bone_id == 255
			
class struc_8(object):
	
	SIZE = 0x120
	
	def read(self, getter, lmt):
		get = getter.get
		# offset_44
		# offset_8C
		# offset_D4
		# offset_11C
		

class struc_9(object):
	
	SIZE = 0x20
	
	def read(self, getter):
		get = getter.get
		seek = getter.seek
		# min-max float value for a set of compressed keyframes
		f0 = get("f", offset=0x0)
		f1 = get("f", offset=0x4)
		f2 = get("f", offset=0x8)
		f3 = get("f", offset=0xc)
		f4 = get("f", offset=0x10)
		f5 = get("f", offset=0x14)
		f6 = get("f", offset=0x18)
		f7 = get("f", offset=0x1c)
		print f0, f1, f2, f3
		print f4, f5, f6, f7
	
class struc_10(object):
	
	SIZE = 0xc
	
	def read(self, getter):
		# offset_8
		pass
	
def parse(lmt_path):
	f = open(lmt_path, "rb")
	getter = util.get_getter(f, "<")

	lmt = LMT()
	lmt.read(getter)
	
	f.close()

if __name__ == '__main__':
	parse(sys.argv[1])
