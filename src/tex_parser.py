import os
import sys
import struct
import util
from d3d10.dxgi_format import *

PF_7 = 7
PF_23 = 23
PF_25 = 25
PF_31 = 31
PF_19 = 19
PF_30 = 30
PF_42 = 42
PF_32 = 32
PF_37 = 37
PF_2 = 2

# In fact, these are not pixel format
# dump 0xfaa41e to get the LUT 'pf_2_dxgi'
PF_CONFIG = {
	PF_7: {
		"bpp": 4,
		"DXGI": DXGI_FORMAT_R8G8B8A8_UNORM,
	},
	PF_23: {
		"bpp": 1,
		"DXGI": DXGI_FORMAT_BC3_UNORM,
	},
	PF_25: {
		"bpp": 0.5,
		"DXGI": DXGI_FORMAT_BC4_UNORM,
	},
	PF_31: {
		"bpp": 1,
		"DXGI": DXGI_FORMAT_BC5_SNORM,
	},
	PF_19: {
		"bpp": 0.5,
		"DXGI": DXGI_FORMAT_BC1_UNORM,
	},
	PF_30: {
		"bpp": 0.5,
		"DXGI": DXGI_FORMAT_BC1_UNORM,
	},
	PF_42: {
		"bpp": 1,
		"DXGI": DXGI_FORMAT_BC3_UNORM,
	},
	PF_32: {
		"bpp": 1,
		"DXGI": DXGI_FORMAT_BC3_UNORM,
	},
	PF_37: {
		"bpp": 1,
		"DXGI": DXGI_FORMAT_BC3_UNORM,
	},
	PF_2: {
		"bpp": 8,
		"DXGI": DXGI_FORMAT_R16G16B16A16_FLOAT,
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
	assert reso_pow == 0, "seems like reserved fields"
	print "texture dimension = (%d, %d, %d)" % (width, height, depth)
	print "mipmap level count = %d" % mip_level
	print "pixel format = %d, bpp = %f" % (pixel_format, PF_CONFIG[pixel_format]["bpp"])
	# print "texture type = %d" % texture_type
	# print "unknowns", unkown0, unknown5
	assert unkown0 == 0 and unknown5 == 0, "seems like reserved fields"
	
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
	
	texel_data_list = []
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
		
		getter.seek(start_offset)
		texel_data = getter.get_raw(size)
		texel_data_list.append(texel_data)
	
	output_name_base = os.path.splitext(f.name)[0]
	# export
	if texture_type == TT_2D:
		data = texel_data_list[0]
		dxgi = PF_CONFIG[pixel_format]["DXGI"]
		if dxgi == DXGI_FORMAT_R8G8B8A8_UNORM:
			save_texture_2D(data, width, height, output_name_base + ".png")
		elif dxgi == DXGI_FORMAT_BC1_UNORM:
			save_dxt1(data, width, height, output_name_base + ".dds")
		elif dxgi == DXGI_FORMAT_BC3_UNORM:
			save_dxt5(data, width, height, output_name_base + ".dds")
		elif dxgi == DXGI_FORMAT_BC4_UNORM:
			if os.path.exists(output_name_base + ".dds"):
				os.remove(output_name_base + ".dds")
			save_bc4(data, width, height, output_name_base + ".png")
		# most probably used by normal map to take advantages of the `SNORM` part
		elif dxgi == DXGI_FORMAT_BC5_SNORM:
			if os.path.exists(output_name_base + ".dds"):
				os.remove(output_name_base + ".dds")			
			save_bc5(data, width, height, output_name_base + ".png")
		else:
			assert False, "unsupported dxgi format %d" % dxgi
	
	f.close()
	
def save_texture_2D(data, width, height, fname):
	from PIL import Image
	image = Image.frombuffer("RGBA", (width, height), data)
	image.transpose(Image.FLIP_TOP_BOTTOM).save(fname)

def save_dxt1(data, width, height, fname):
	header = util.gen_dxt1_header(width, height)
	fout = open(fname, "wb")
	fout.write(header + data)
	fout.close()
	
def save_dxt5(data, width, height, fname):
	header = util.gen_dxt5_header(width, height)
	fout = open(fname, "wb")
	fout.write(header + data)
	fout.close()
	
def _bc5_extract_component(d):
	red_0 = ord(d[0])
	red_1 = ord(d[1])
	lut = [red_0, red_1, ]
	if red_0 > red_1: # 6 interpolated color values
		lut.append((6*red_0 + 1*red_1)/7.0)
		lut.append((5*red_0 + 2*red_1)/7.0)
		lut.append((4*red_0 + 3*red_1)/7.0)
		lut.append((3*red_0 + 4*red_1)/7.0)
		lut.append((2*red_0 + 5*red_1)/7.0)
		lut.append((1*red_0 + 6*red_1)/7.0)
	else:	# 4 interpolated color values
		lut.append((4*red_0 + 1*red_1)/5.0)
		lut.append((3*red_0 + 2*red_1)/5.0)
		lut.append((2*red_0 + 3*red_1)/5.0)
		lut.append((1*red_0 + 4*red_1)/5.0)
		lut.append(0)
		lut.append(255)
	ret = []
	v = struct.unpack(">Q", d)[0]
	for bit in xrange(47, -1, -3):
		cidx = (v >> (bit - 2)) & 0b111
		ret.append(lut[cidx])
	return ret
	
def save_bc5(data, width, height, fname):
	pixel_count = width * height
	ret = [None] * pixel_count
	x_nblock = width / 4
	for block_idx in xrange(len(data) / 16):
		# red component
		d = data[16 * block_idx: 16 * block_idx + 8]
		red = _bc5_extract_component(d)
		# green component
		d = data[16 * block_idx + 8: 16 * block_idx + 16]
		green = _bc5_extract_component(d)
		
		y_start = block_idx / x_nblock
		x_start = block_idx - x_nblock * y_start
		x_start *= 4
		y_start *= 4
		for i in xrange(16):
			y = i / 4
			x = i - y * 4
			ret[x_start + x + (y_start + y) * width] = (red[i], green[i])
	buff = ""
	for r, g in ret:
		buff += chr(int(r)) + chr(int(g)) + "\x00"
	from PIL import Image
	image = Image.frombuffer("RGB", (width, height), buff)
	image.transpose(Image.FLIP_TOP_BOTTOM).save(fname)

def save_bc4(data, width, height, fname):
	pixel_count = width * height
	ret = [None] * pixel_count
	x_nblock = width / 4
	for block_idx in xrange(len(data) / 8):
		# red component
		d = data[8 * block_idx: 8 * block_idx + 8]
		red = _bc5_extract_component(d)
		
		y_start = block_idx / x_nblock
		x_start = block_idx - x_nblock * y_start
		x_start *= 4
		y_start *= 4
		for i in xrange(16):
			y = i / 4
			x = i - y * 4
			ret[x_start + x + (y_start + y) * width] = (red[i], )
	buff = ""
	for r, in ret:
		buff += chr(int(r))
	from PIL import Image
	image = Image.frombuffer("L", (width, height), buff)
	image.transpose(Image.FLIP_TOP_BOTTOM).save(fname)
	
def test_all(test_count=-1):
	ROM_ROOT = os.path.join(os.environ["DMC4SE_DATA_DIR"], "rom")
	for top, dirs, files in os.walk(ROM_ROOT):
		for fname in files:
			if fname.endswith(".TEX"):
				print "-" * 30
				print "parsing", fname
				# print "fullpath", os.path.join(top, fname)
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