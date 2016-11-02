# -*- coding: utf-8 -*-
import sys
import util
import json
	
def parse(path):
	with open(path, "rb") as f:
		data = f.read()
	getter = util.get_getter(data, "<")
	
	header = getter.block(0x18)
	fourcc = header.get("4s")
	assert fourcc == "XFS\x00"
	unk0 = header.get("H")
	unk1 = header.get("H")
	unk_cnt = header.get("I")
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
	assert ((n >> 1) & 0x7FFF) != 0x7FFF
	assert n == 1
	sz = getter.get("I")
	blk = getter.block(sz - 4)

	parse_object(xml_defs, 0, blk)
		
# should parse recursively
def parse_object(xml_defs, i, blk, depth=0):
	xml_def = xml_defs[i]
	if i == 0:
		next_xml_def = 1
	else:
		next_xml_def = None
	indent = "\t" * depth
	def log(*args):
		print indent + " ".join(map(str, args))
	for i, (name, node_type) in enumerate(xml_def):
		log("offset = 0x%x, retrieving value for %s 0x%x" % (blk.offset, name, node_type))
		nn = blk.get("I") & 0x7FFF
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
				log("object%d" % j)
				parse_object(xml_defs, 1, blk, depth + 1)
				continue
			else:
				log("offset = 0x%x" % (blk.offset + getter.offset - blk.size))
				assert False, "unknown type! %d" % base_type
			log(("\t%d: " % j), v)
	
def parse_subdata(subdatablock, subdata):
	cls_hash = subdata.get("I")
	hash_2_classname = get_hash_2_classname()
	cls_name = hash_2_classname[cls_hash]
	print "Parsing cls: 0x%x" % cls_hash
	node_count = subdata.get("I") & 0x7FFF
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
		
hash_2_classname = None
def get_hash_2_classname():
	global hash_2_classname
	if hash_2_classname is None:
		hash_2_classname = {}
		with open("windbg/hash_2_classname.json", "rb") as f:
			tmp = json.load(f)
			for k, v in tmp.iteritems():
				hash_2_classname[int(k, 16)] = v
	return hash_2_classname

def parse_mtobj_type(t):
	print "is_array", (t >> 17) & 1
	print "is_what", (t >> 15) & 1
	
if __name__ == '__main__':
	parse(sys.argv[1])