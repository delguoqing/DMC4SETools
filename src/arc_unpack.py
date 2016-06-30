import os
import sys
import util
import zlib
import json

FOURCC = "ARC\x00"
VERSION = 0x7
ENDIAN = "<"

f = open("windbg/hash_2_classname.json", "r")
hash_2_classnames = json.load(f)
f.close()

def unpack(fpath, out_root="."):
	f = open(fpath, "rb")
	getter = util.get_getter(f, ENDIAN)
	get = getter.get
	seek = getter.seek
	# header
	fourcc, version, filecnt = get("4s2H")
	assert fourcc == FOURCC
	assert version == VERSION
	
	arc_prefix = os.path.splitext(os.path.split(fpath)[1])[0]
	# filelist
	filelist = []
	for file_idx in xrange(filecnt):
		offset = getter.offset
		file_path = get("64s").rstrip("\x00")
		assert "\x00" not in file_path
		unk1, comp_size, unk2, offset = get("4I")
		filelist.append((file_path, offset, comp_size, unk1, unk2))
	
	# unk1: hashcode for reflecting a runtime class
	for file_path, offset, size, unk1, unk2 in filelist:
		seek(offset)
		data = getter.get_raw(size)
		data_decomp = zlib.decompress(data)
		
		type_hex = unk1
		
		class_name = hash_2_classnames.get(hex(type_hex), "")
		ext = class_name
		if not ext:
			if data_decomp.startswith("<?xml"):
				ext = "xml"
			elif data_decomp.startswith("MOT"):
				ext = "MOT"
			else:
				assert False, "unknown file extension!"
		outpath = file_path		
		final_outpath = outpath + "." + ext
		print hex(offset), final_outpath
		
		final_outpath = os.path.join(out_root, final_outpath)
		# sometimes, the same file from different arc file will collide
		# mostly in gui localization. It doesn't matter too much for me though.
		need_write = True
		while os.path.exists(final_outpath):
			print final_outpath
			f_old = open(final_outpath, "rb")
			data_old = f_old.read()
			f_old.close()
			if data_decomp == data_old:
				need_write = False
				break
			final_outpath += ".alias"
			
		if need_write:
			try:
				util.dump_bin(data_decomp, final_outpath, mkdir=True)
			except IOError as e:
				print "hex_format", hex(unk1)
				util.dump_bin(data_decomp, outpath + "_debug", mkdir=True)
				raise
	
	f.close()

if __name__ == '__main__':
	unpack(sys.argv[1])