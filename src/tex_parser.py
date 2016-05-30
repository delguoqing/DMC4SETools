import os
import sys
import util

def parse(path):
	f = open(path, "rb")
	getter = util.get_getter(f, "<")
	
	FOURCC = getter.get("4s")
	assert FOURCC == "TEX\x00"
	
	field_4 = getter.get("I")
	check_code = field_4 & 0xFFFF
	assert check_code == 0x9E or check_code == 0x809E
	unkown0 = (field_4 >> 16) & 0xFF
	reso_pow = (field_4 >> 24) & 0xF
	unknown1 = (field_4 >> 28) & 0xF
	
	field_8 = getter.get("I")
	unknown2 = (field_8 & 0x3F)
	width = (field_8 >> 6) & 0x1FFFF
	height = (field_8 >> 19) & 0x1FFFF
	
	field_C = getter.get("I")
	unknown3 = field_C & 0xFFFF
	depth = (field_C >> 16) & 0x1FFFF
	unknown4 = (field_C >> 29) & 0x7
	
	print "high reso scale = %d" % (1 << reso_pow)
	print "texture dimension = (%d, %d, %d)" % (width, height, depth)
	
	f.close()
	
if __name__ == '__main__':
	parse(sys.argv[1])