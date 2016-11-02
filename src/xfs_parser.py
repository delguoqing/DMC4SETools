# -*- coding: utf-8 -*-
import util
import sys

def parse(path):
	with open(path, "rb") as f:
		data = f.read()
	getter = util.get_getter(data, "<")
	
	header = getter.block(0x18)
	fourcc = header.get("4s")
	assert fourcc == "XFS\x00"
	unk0 = header.get("H")
	unk1 = header.get("H")
	assert unk0 & 0x7FFF == 0xF
	subdata_cnt = header.get("I", offset=0x10)
	subdatablock_sz = header.get("I", offset=0x14)
	
	subdatablock = getter.block(subdatablock_sz)
	off_lst = subdatablock.get("%dI" % subdata_cnt, force_tuple=True)
	xml_defs = []
	for i, off in enumerate(off_lst):
		if i + 1 < len(off_lst):
			sz = off_lst[i + 1] - off
		else:
			sz = subdatablock_sz - off
		subdatablock.seek(off)
		subdata = subdatablock.block(sz)
		def_ = parse_subdata(subdatablock, subdata)
		xml_defs.append(def_)
		
	n = getter.get("I")
	assert n == 1
	sz = getter.get("I")
	blk = getter.block(sz - 4)

	for i, (name, node_type) in enumerate(xml_defs[0]):
		print "retrieving value for %s 0x%x" % (name, node_type)
		nn = blk.get("I")
		base_type = node_type & 0xFF
		# assert nn == 1, "nn=%d, offset=0x%x" % (nn, blk.offset)
		for j in xrange(nn):
			if base_type == 6:
				v = blk.get("I")
			elif base_type == 0xc:
				v = blk.get("f")
			elif base_type == 0x14:
				v = blk.get("4f")
			elif base_type == 0x3:
				v = blk.get("B")
			elif base_type == 0x9:
				v = blk.get("H")
			elif base_type == 0x1:
				# class_ref
				
			else:
				print "offset = 0x%x" % (blk.offset + getter.offset - blk.size)
				assert False, "unknown type! %d" % base_type
			print ("\t%d: " % j), v
		
def parse_subdata(subdatablock, subdata):
	cls_hash = subdata.get("I")
	print "Parsing cls: 0x%x" % cls_hash
	node_count = subdata.get("I")
	xml_def = []
	for i in xrange(node_count):
		node_name_off = subdata.get("I")
		node_name = subdatablock.data[node_name_off: subdatablock.data.find("\x00", node_name_off)]
		node_type = subdata.get("I")
		mt_type = (node_type & 0xFF) | (((node_type & 0xFF00) << 8) & 0xFFFF0000)
		print "\t", node_name, hex(mt_type), hex(node_type)
		subdata.skip(0x10)
		xml_def.append((node_name, node_type))
	return xml_def
		
if __name__ == '__main__':
	parse(sys.argv[1])