import os
import sys
import util

PF_RGBA4 = 7
PF_23 = 23
PF_25 = 25
PF_31 = 31
PF_19 = 19
PF_30 = 30
PF_42 = 42
PF_32 = 32
PF_37 = 37
PF_2 = 2

PF_CONFIG = {
	PF_RGBA4: {
		"bpp": 4,
	},
	PF_23: {
		"bpp": 1,
	},
	PF_25: {
		"bpp": 0.5,
	},
	PF_31: {
		"bpp": 1,
	},
	PF_19: {
		"bpp": 0.5,
	},
	PF_30: {
		"bpp": 0.5,
	},
	PF_42: {
		"bpp": 1,
	},
	PF_32: {
		"bpp": 1,
	},
	PF_37: {
		"bpp": 1,
	},
	PF_2: {
		"bpp": 8,
	},			
}

TT_2D = 2
TT_VOLUME = 3
TT_CUBE = 6

TT_CONFIG = {
	TT_2D: {
		
	},
	TT_VOLUME: {
		
	},		
	TT_CUBE: {
		
	},
}
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
	texture_type = (field_4 >> 28) & 0xF	# texture type
	
	field_8 = getter.get("I")
	mip_level = (field_8 & 0x3F)
	width = (field_8 >> 6) & 0x1FFF
	height = (field_8 >> 19) & 0x1FFF
	
	field_C = getter.get("I")
	side_count = field_C & 0xFF		# for cube map
	pixel_format = (field_C >> 8) & 0xFF
	depth = (field_C >> 16) & 0x1FFF
	unknown5 = (field_C >> 29) & 0x7
		
	# print "high reso scale = %d" % (1 << reso_pow)
	assert reso_pow == 0, "uncomment print if assert failed"
	print "texture dimension = (%d, %d, %d)" % (width, height, depth)
	print "mipmap level count = %d" % mip_level
	# print "texture type = %d" % texture_type
	print "unknowns", unkown0, unknown5
	
	if texture_type == TT_CUBE:
		getter.skip(0x6c)
		
	# offset of each mip map level of each side
	texture_offsets = getter.get("%dI" % (side_count * mip_level), force_tuple=True)
	
	if texture_type == TT_2D:
		assert depth == 1
	if texture_type == TT_CUBE:
		assert side_count == 6
	else:
		assert side_count == 1
		
	# Simply reads all data from the `texture_offsets[0]` to file end.
	# As we are exporting textures, we just need the first mip0
	
	# texture offsets layout
	# side0_mip0, side0_mip1, ..., side0_mipN
	# side1_mip0, side1_mip1, ..., side1_mipN,
	# ...
	# sideM_mip0, sideM_mip1, ..., sideM_mipN
	
	for side_idx in xrange(side_count):
		offset_idx = side_idx * mip_level
		start_offset = texture_offsets[offset_idx]
		if len(texture_offsets) > offset_idx + 1:
			end_offset = texture_offsets[offset_idx + 1]
		else:
			end_offset = getter.size
		size = end_offset - start_offset
		pixel_count = width * height * depth
		print "texture(mip0) offset = 0x%x - 0x%x" % (start_offset, end_offset)
		print "texture(mip0) size = 0x%x" % size
		assert (pixel_format in PF_CONFIG), \
				"unknown pixel format = %d, bpp = %f" % (pixel_format,
														 size / float(pixel_count))
		calc_size = int(pixel_count * PF_CONFIG[pixel_format]["bpp"])
		assert size == calc_size, "bpp is not correct"
		
	f.close()
	
def test_all(test_count=-1):
	ROM_ROOT = os.path.join(os.environ["DMC4SE_DATA_DIR"], "rom")
	for top, dirs, files in os.walk(ROM_ROOT):
		for fname in files:
			if fname.endswith(".TEX"):
				print "-" * 30
				# print "parsing", fname
				print "fullpath", os.path.join(top, fname)
				parse(os.path.join(top, fname))
				if test_count > 0:
					test_count -= 1
					if test_count <= 0:
						return
				
if __name__ == '__main__':
	if len(sys.argv) > 1:
		parse(sys.argv[1])
	else:
		test_all()