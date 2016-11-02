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
	off_cnt = header.get("I", offset=0x10)
	subdata_sz = header.get("I")
	
	subdata = getter.block(subdata_sz)
	
	off_lst = subdata.get("%dI" % off_cnt, force_tuple=True)
	print "subdata_item offset = ", map(hex, off_lst)
	for i, off in enumerate(off_lst):
		if i < len(off_lst) - 1:
			sz = off_lst[i + 1] - off
		else:
			sz = subdata.size
		subdata.seek(off)
		subdata_item = subdata.block(sz)
		parse_subdata_item(subdata, subdata_item)
		
	v = getter.get("I")
	assert ((v >> 1) & 0x7FFF) != 0x7FFF
	
	sz = getter.get("I")	# remain size?
	
		
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
	
def parse_subdata_item(subdata, item):
	item.seek(0)
	cls_hash = item.get("I")
	hash_2_classname = get_hash_2_classname()
	cls_name = hash_2_classname[cls_hash]
	print "Parsing", cls_name
	key_cnt = item.get("I") & 0x7FFF
	for i in xrange(key_cnt):
		key_off = item.get("I")
		key = subdata.data[key_off: subdata.data.find("\x00", key_off)]
		node_type = item.get("I")
		mtobj_type = (node_type & 0xFF) | (((node_type & 0xFF00) << 8) & 0xFFFF0000)
		item.skip(0x10)
		print "\t", key, hex(mtobj_type)
	
	

	
if __name__ == '__main__':
	parse(sys.argv[1])