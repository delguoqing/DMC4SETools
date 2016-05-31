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
	unknown1 = (field_4 >> 28) & 0xF	# texture type?
	
	field_8 = getter.get("I")
	mip_level = (field_8 & 0x3F)
	width = (field_8 >> 6) & 0x1FFFF
	height = (field_8 >> 19) & 0x1FFFF
	
	field_C = getter.get("I")
	unknown3 = field_C & 0xFF
	unknown4 = (field_C >> 8) & 0xFF
	depth = (field_C >> 16) & 0x1FFFF
	unknown5 = (field_C >> 29) & 0x7
		
	print "high reso scale = %d" % (1 << reso_pow)
	print "texture dimension = (%d, %d, %d)" % (width, height, depth)
	print "mipmap level count = %d" % mip_level
	
	if unknown1 == 6:
		getter.skip(0x6c)
		
	# offset of each mip map level
	# unknown3: used by cube map? where each mip level contains serveral texture
	unknown6 = getter.block(unknown3 * mip_level * 4)
	
	texture_type = unknown1 - 1
	
	f.close()
	
if __name__ == '__main__':
	parse(sys.argv[1])