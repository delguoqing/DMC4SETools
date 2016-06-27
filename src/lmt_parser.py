import sys
import struct
import json
import util

# keyframe types
POS_XYZ_FLOAT_T32 = 3
POS_XYZT16 = 4
POS_XYZT8 = 5
ROT_XYZW14_T8 = 6
ROT_XYZW7_T4 = 7
ROT_XW14_T4 = 11
ROT_YW14_T4 = 12
ROT_ZW14_T4 = 13
ROT_XYZW11_T4 = 14
ROT_XYZW9_T4 = 15

BONE_ROT = 0
BONE_POS = 1
BONE_SCALE = 2
BONE_TRANS = (BONE_ROT, BONE_POS, BONE_SCALE)
MODEL_ROT = 3
MODEL_POS = 4
MODEL_SCALE = 5
MODEL_TRANS = (MODEL_ROT, MODEL_POS, MODEL_SCALE)

class LMT(object):
	
	def read(self, getter):
		fourcc = getter.get("4s")
		assert fourcc == "LMT\x00"
		reserved = getter.get("H")
		assert reserved == 0x43
		# motion count
		motion_num = getter.get("H")
		# motion list
		self.motion_list = motion_list = []
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
		
		self.track_list = track_list = []
		if (field_33 & 1) == 0:
			lmt.seek(track_off)
			for track_index in xrange(track_num):
				print "track offset = 0x%x" % (track_off + track_index * track.SIZE)
				lmt.seek(track_off + track_index * track.SIZE)
				_track = track()
				_track.read(lmt.block(track.SIZE), lmt)
				track_list.append(_track)
		else:
			print "[WARNING] not skeletal animation!"
		
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
		# keyframe type
		key_type = flag_0 & 0xFF
		# transformation type
		self.trans_type = trans_type = (flag_0 >> 8) & 0xFF
		# unknown
		type_2 = (flag_0 >> 16) & 0xFF
		# bone id
		self.bone_id = bone_id = (flag_0 >> 24)
		
		float_4 = getter.get("f")
		keyframes_size = getter.get("I")
		keyframe_offset = getter.get("I")		
		self.default_value = frame_0 = getter.get("4f")
		self.keys = []
		
		range_offset = getter.get("I")
		if range_offset != 0:
			assert key_type > 9 or key_type in (4, 5, 7)
			lmt.seek(range_offset)
			range_scales = lmt.get("4f")
			range_bases = lmt.get("4f")
		else:
			range_scales = range_bases = None
		
		# keyframe data are stored in a fairly compact format
		if keyframe_offset != 0:
			def print_keyframe(i, f, v0, v1, v2, v3):
				print "\tframe=%d, eval=(%f, %f, %f, %f)" % (t, v0, v1, v2, v3)
			print "checking keyframe offset = 0x%x, size = 0x%x, type = %d" % (
				keyframe_offset, keyframes_size, key_type
			)
			lmt.seek(keyframe_offset)
			keyframes = lmt.block(keyframes_size)
			if key_type == POS_XYZ_FLOAT_T32:
				self.keys = self.parse_keyframes_POS_XYZ_FLOAT_T32(keyframes, range_scales, range_bases)
			elif key_type == POS_XYZT16:
				self.keys = self.parse_keyframes_POS_XYZT16(keyframes, range_scales, range_bases)
			elif key_type == POS_XYZT8:
				self.keys = self.parse_keyframes_POS_XYZT8(keyframes, range_scales, range_bases)
			elif key_type == ROT_XYZW14_T8:
				self.keys = self.parse_keyframes_ROT_XYZW14_T8(keyframes, range_scales, range_bases)
			elif key_type == ROT_XYZW7_T4:
				self.keys = self.parse_keyframes_ROT_XYZW7_T4(keyframes, range_scales, range_bases)
			elif key_type == ROT_XW14_T4:
				self.keys = self.parse_keyframes_ROT_XW14_T4(keyframes, range_scales, range_bases)
			elif key_type == ROT_YW14_T4:
				self.keys = self.parse_keyframes_ROT_YW14_T4(keyframes, range_scales, range_bases)
			elif key_type == ROT_ZW14_T4:
				self.keys = self.parse_keyframes_ROT_ZW14_T4(keyframes, range_scales, range_bases)
			elif key_type == ROT_XYZW11_T4:
				self.keys = self.parse_keyframes_ROT_XYZW11_T4(keyframes, range_scales, range_bases)
			elif key_type == ROT_XYZW9_T4:
				self.keys = self.parse_keyframes_ROT_XYZW9_T4(keyframes, range_scales, range_bases)
			else:
				assert False, "unsupported keyframe packing type! %d" % key_type
			f = 0
			for i, (t, x, y, z, w) in enumerate(self.keys):
				self.keys[i] = (f, x, y, z, w)
				print_keyframe(i, f, x, y, z, w)
				f += t
		else:
			key = list(self.default_value)
			key.insert(0, 0)
			self.keys.append(key)
				
		print "track: key_type=%d, trans_type=%d, type_2=%d, bone_id=%d, float_4=%f" % (
			key_type, trans_type, type_2, bone_id, float_4)
		if trans_type in (BONE_ROT, MODEL_ROT):
			print "ROTATION",
			util.assert_quat(frame_0)
		elif trans_type in (BONE_POS, MODEL_POS):
			print "POSITION",
		elif trans_type in (BONE_SCALE, MODEL_SCALE):
			print "SCALE   ",
		else:
			assert False, "unsupported type! %d" % trans_type
		print frame_0
		print
		
		# assert model root transformation
		if bone_id == 255:
			assert trans_type in MODEL_TRANS

	def parse_keyframes_ROT_XYZW9_T4(self, keyframes, range_scales, range_bases):
		keyframes_size = keyframes.size
		assert keyframes_size % 5 == 0
		keyframe_num = keyframes_size / 5
		FAC = struct.unpack(">f", "\x3B\x04\x21\x08")[0]
		keys = []
		for i in xrange(keyframe_num):
			v = keyframes.get("5B")
			v0 = (((v[0] << 1) | (v[1] & 1)) - 8) * FAC * range_scales[0] + range_bases[0]
			v1 = ((((v[1] >> 1) << 2) | v[2] & 0x3) - 8) * FAC * range_scales[1] + range_bases[1]
			v2 = ((((v[2] >> 2) << 3) | (v[3] & 0x7)) - 8) * FAC * range_scales[2] + range_bases[2]
			v3 = ((((v[3] >> 3) << 4) | (v[4] & 0xF)) - 8) * FAC * range_scales[3] + range_bases[3]
			t = (v[2] >> 12)
			# normalize
			length = (v0 ** 2 + v1 ** 2 + v2 ** 2 + v3 ** 2) ** 0.5
			v0 /= length
			v1 /= length
			v2 /= length
			v3 /= length
			keys.append((t, v0, v1, v2, v3))
		return keys

	def parse_keyframes_ROT_XYZW11_T4(self, keyframes, range_scales, range_bases):
		keyframes_size = keyframes.size
		assert keyframes_size % 6 == 0
		keyframe_num = keyframes_size / 6
		keys = []
		FAC = struct.unpack(">f", "\x3A\x01\x02\x04")[0]
		for i in xrange(keyframe_num):
			v = keyframes.get("HHH")
			v0 = ((v[0] & 0x7FF) - 8) * FAC * range_scales[0] + range_bases[0]
			v1 = ((((v[0] >> 11) << 6) | (v[1] & 0x3F)) - 8) * FAC * range_scales[1] + range_bases[1]
			v2 = ((((v[1] >> 6) << 1) | (v[2] & 1)) - 8) * FAC * range_scales[2] + range_bases[2]
			v3 = (((v[2] >> 1) & 0x7FF) - 8) * FAC * range_scales[3] + range_bases[3]
			t = (v[2] >> 12)
			# normalize
			length = (v0 ** 2 + v1 ** 2 + v2 ** 2 + v3 ** 2) ** 0.5
			v0 /= length
			v1 /= length
			v2 /= length
			v3 /= length
			keys.append((t, v0, v1, v2, v3))
		return keys

	def parse_keyframes_ROT_ZW14_T4(self, keyframes, range_scales, range_bases):
		keyframes_size = keyframes.size
		assert keyframes_size % 4 == 0
		keyframe_num = keyframes_size / 4
		FAC = struct.unpack(">f", "\x38\x80\x20\x08")[0]
		keys = []
		for i in xrange(keyframe_num):
			v = keyframes.get("I")
			t = (v >> 28) & 0xF
			v0 = range_bases[0]
			v1 = range_bases[1]
			v2 = (((v >> 0) & 0x3FFF) - 8) * FAC * range_scales[2] + range_bases[2]
			v3 = (((v >> 14) & 0x3FFF) - 8) * FAC * range_scales[3] + range_bases[3]
			# normalize
			length = (v0 ** 2 + v1 ** 2 + v2 ** 2 + v3 ** 2) ** 0.5
			v0 /= length
			v1 /= length
			v2 /= length
			v3 /= length
			keys.append((t, v0, v1, v2, v3))
		return keys

	def parse_keyframes_ROT_YW14_T4(self, keyframes, range_scales, range_bases):
		keyframes_size = keyframes.size
		assert keyframes_size % 4 == 0
		keyframe_num = keyframes_size / 4
		FAC = struct.unpack(">f", "\x38\x80\x20\x08")[0]
		keys = []
		for i in xrange(keyframe_num):
			v = keyframes.get("I")
			t = (v >> 28) & 0xF
			v0 = range_bases[0]
			v1 = (((v >> 0) & 0x3FFF) - 8) * FAC * range_scales[1] + range_bases[1]
			v2 = range_bases[2]
			v3 = (((v >> 14) & 0x3FFF) - 8) * FAC * range_scales[3] + range_bases[3]
			# normalize
			length = (v0 ** 2 + v1 ** 2 + v2 ** 2 + v3 ** 2) ** 0.5
			v0 /= length
			v1 /= length
			v2 /= length
			v3 /= length
			keys.append((t, v0, v1, v2, v3))
		return keys	

	def parse_keyframes_ROT_XW14_T4(self, keyframes, range_scales, range_bases):
		keyframes_size = keyframes.size
		assert keyframes_size % 4 == 0
		keyframe_num = keyframes_size / 4
		FAC = struct.unpack(">f", "\x38\x80\x20\x08")[0]
		keys = []
		for i in xrange(keyframe_num):
			v = keyframes.get("I")
			t = (v >> 28) & 0xF
			v0 = (((v >> 0) & 0x3FFF) - 8) * FAC * range_scales[0] + range_bases[0]
			v1 = range_bases[1]
			v2 = range_bases[2]
			v3 = (((v >> 14) & 0x3FFF) - 8) * FAC * range_scales[3] + range_bases[3]
			# normalize
			length = (v0 ** 2 + v1 ** 2 + v2 ** 2 + v3 ** 2) ** 0.5
			v0 /= length
			v1 /= length
			v2 /= length
			v3 /= length
			keys.append((t, v0, v1, v2, v3))
		return keys
	
	def parse_keyframes_ROT_XYZW7_T4(self, keyframes, range_scales, range_bases):
		keyframes_size = keyframes.size
		assert keyframes_size % 4 == 0
		keyframe_num = keyframes_size / 4
		FAC = struct.unpack(">f", "\x3C\x12\x49\x25")[0]
		keys = []
		for i in xrange(keyframe_num):
			v = keyframes.get("I")
			t = (v >> 28) & 0xF
			v0 = ((v >> 0 & 0x7F) - 8) * FAC * range_scales[0] + range_bases[0]
			v1 = ((v >> 7 & 0x7F) - 8) * FAC * range_scales[1] + range_bases[1]
			v2 = ((v >> 14 & 0x7F) - 8) * FAC * range_scales[2] + range_bases[2]
			v3 = ((v >> 21 & 0x7F) - 8) * FAC * range_scales[3] + range_bases[3]
			# normalize
			length = (v0 ** 2 + v1 ** 2 + v2 ** 2 + v3 ** 2) ** 0.5
			v0 /= length
			v1 /= length
			v2 /= length
			v3 /= length
			keys.append((t, v0, v1, v2, v3))
		return keys

	def parse_keyframes_ROT_XYZW14_T8(self, keyframes, range_scales, range_bases):
		keyframes_size = keyframes.size
		assert keyframes_size % 8 == 0
		keyframe_num = keyframes_size / 8
		FAC = struct.unpack(">f", "\x38\x80\x00\x00")[0]
		keys = []
		for i in xrange(keyframe_num):
			q = keyframes.get("Q")
			v3 = ((q >> 0) & 0x3FFF) << 2
			if v3 & 0x8000: v3 -= (1 << 16)
			v3 *= FAC
			v2 = ((q >> 14) & 0x3FFF) << 2
			if v2 & 0x8000: v2 -= (1 << 16)
			v2 *= FAC
			v1 = ((q >> 28) & 0x3FFF) << 2
			if v1 & 0x8000: v1 -= (1 << 16)
			v1 *= FAC
			v0 = ((q >> 42) & 0x3FFF) << 2
			if v0 & 0x8000: v0 -= (1 << 16)
			v0 *= FAC
			t = (q >> 56) & 0xFF
			# normalize
			length = (v0 ** 2 + v1 ** 2 + v2 ** 2 + v3 ** 2) ** 0.5
			v0 /= length
			v1 /= length
			v2 /= length
			v3 /= length
			keys.append((t, v0, v1, v2, v3))
		return keys

	def parse_keyframes_POS_XYZT8(self, keyframes, range_scales, range_bases):
		keyframes_size = keyframes.size
		assert keyframes_size % 4 == 0
		keyframe_num = keyframes_size / 4
		FAC = struct.unpack(">f", "\x3B\x88\x88\x89")[0]
		keys = []
		for i in xrange(keyframe_num):
			v0, v1, v2, t = keyframes.get("BBBB")
			v0 = (v0 - 8) * FAC * range_scales[0] + range_bases[0]
			v1 = (v1 - 8) * FAC * range_scales[1] + range_bases[1]
			v2 = (v2 - 8) * FAC * range_scales[2] + range_bases[2]
			keys.append((t, v0, v1, v2, 0.0))
		return keys
	
	def parse_keyframes_POS_XYZT16(self, keyframes, range_scales, range_bases):
		keyframes_size = keyframes.size
		assert keyframes_size % 8 == 0
		keyframe_num = keyframes_size / 8
		FAC = struct.unpack(">f", "\x37\x80\x08\x01")[0]
		keys = []
		for i in xrange(keyframe_num):
			v0, v1, v2, t = keyframes.get("HHHH")
			v0 = (v0 - 8) * FAC * range_scales[0] + range_bases[0]
			v1 = (v1 - 8) * FAC * range_scales[1] + range_bases[1]
			v2 = (v2 - 8) * FAC * range_scales[2] + range_bases[2]
			keys.append((t, v0, v1, v2, 0.0))
		return keys

	def parse_keyframes_POS_XYZ_FLOAT_T32(self, keyframes, range_scales, range_bases):
		keyframes_size = keyframes.size
		assert keyframes_size % 16 == 0
		keyframe_num = keyframes_size / 16
		keys = []
		for i in xrange(keyframe_num):
			v0, v1, v2, t = keyframes.get("fffI")
			keys.append((t, v0, v1, v2, 0.0))
		return keys
	
class struc_8(object):
	
	SIZE = 0x120
	
	def read(self, getter, lmt):
		get = getter.get
		# offset_44
		# offset_8C
		# offset_D4
		# offset_11C
	
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
	
	# dump to gtba format
	# 	poses: will be imported into pose library, the 1st pose will be set as a default
	#		   pose which is also a very convenient way to debug your exporter code.
	# 	animations: will be imported as actions
	gtba = {
		"pose": {},
		"animations": {},
	}
	default_pose = {}
	for track in lmt.motion_list[0].track_list:
		if track.trans_type in MODEL_TRANS:
			continue
		bone_trans = default_pose.setdefault(track.bone_id, [None, None, None])
		i = [BONE_POS, BONE_ROT, BONE_SCALE].index(track.trans_type)
		bone_trans[i] = track.default_value
	gtba["pose"]["default"] = default_pose
	
	for i, motion in enumerate(lmt.motion_list):
		motion_name = "motion_%d" % i
		motion_data = gtba["animations"][motion_name] = {}
		for track in motion.track_list:
			if track.trans_type in MODEL_TRANS:
				continue
			bone_trans = motion_data.setdefault(track.bone_id, [None, None, None])
			j = [BONE_POS, BONE_ROT, BONE_SCALE].index(track.trans_type)
			bone_trans[j] = track.keys
		
	f = open("objs/motion.gtba", "w")
	json.dump(gtba, f, indent=2, sort_keys=True)
	f.close()
		
if __name__ == '__main__':
	parse(sys.argv[1])
