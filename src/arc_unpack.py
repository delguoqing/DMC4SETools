import os
import sys
import util
import zlib

FOURCC = "ARC\x00"
VERSION = 0x7
ENDIAN = "<"

type_hex_2_fourcc = {
	0x12f6d523: "xml1",
	0x6edd0dee: "xml",
	0x3b5a0da5: "unk0",
	0x12bfaf39: "unk1",
	0xb2aac9a: "XFS0",
	0x1162be6: "XFS1",
	0x5a7bfe3f: "XFS2",
	0x66299460: "XFS3",
	0x46810940: "XFS4",
	0x538120de: "XFS5",
	0x409ec9ca: "XFS6",
	0xdfb06d1: "XFS7",
	0x7ee5207a: "XFS8",
	
	0x1aed0687: "XFS9",
	0x35de00c1: "XFS10",
	0x7098d320: "XFS11",
	0x1341a167: "XFS12",
}

def_ext = type_hex_2_fourcc.values()

def get_type_hex_by_fourcc(fourcc):
	for k, v in type_hex_2_fourcc.iteritems():
		if v == fourcc:
			return k
	return None
		
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
	
	for file_path, offset, size, unk1, unk2 in filelist:
		seek(offset)
		data = getter.get_raw(size)
		data_decomp = zlib.decompress(data)
		
		type_hex = unk1
		fourcc = data_decomp[:4].rstrip("\x00")
		_fourcc = type_hex_2_fourcc.get(type_hex)
		if _fourcc is None:
			_type_hex = get_type_hex_by_fourcc(fourcc)
			if _type_hex is not None:
				print hex(type_hex)
				print ("FOURCC: %s already used by type hex 0x%x" % (fourcc, _type_hex))
				return
			_fourcc = type_hex_2_fourcc[type_hex] = fourcc
		else:
			assert _fourcc in def_ext or fourcc == _fourcc
		
		outpath = file_path		
		final_outpath = outpath + "." + _fourcc
		# print hex(offset), final_outpath, "Type:", hex(type_hex)
		
		final_outpath = os.path.join(out_root, final_outpath)
		
		if os.path.exists(final_outpath):
			print final_outpath
			f_old = open(final_outpath, "rb")
			data_old = f_old.read()
			f_old.close()
			assert data_decomp == data_old	# make sure no identical files are overwritten
		else:
			try:
				util.dump_bin(data_decomp, final_outpath, mkdir=True)
			except IOError as e:
				print "hex_format", hex(unk1)
				util.dump_bin(data_decomp, outpath + "_debug", mkdir=True)
	
	f.close()

if __name__ == '__main__':
	unpack(sys.argv[1])