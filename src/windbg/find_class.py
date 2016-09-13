import json
import sys
from pykd import dbgCommand as DBG

def parse(text):
	ret = []
	lines = text.split("\n")
	for line in lines:
		for tok in line.split()[1:]:
			ret.append(int(tok, 16))
	return ret
	
def run(class_hash):
	class_hash = int(class_hash, 16)
	link_list_head = parse( DBG("dd 12c9c90 L100") )
	offset = link_list_head[class_hash & 0xFF]
	while offset != 0:
		metainfo = parse( DBG("dd %x" % offset) )
		hashcode = metainfo[7]
		classname = DBG("da %x" % metainfo[1]).split()[1].strip("\"")
		if hashcode == class_hash:
			print "offset = %x, %s" % (offset, classname)
			vtable = metainfo[0]
			print "vtable: %x" % vtable
			methods = parse( DBG("dd %x" % (vtable - 36)) )
			print "Method: Get Extendsion At: %x" % methods[0]
			break
		offset = metainfo[5]
	
def iter_metainfo():
	link_list_head = parse( DBG("dd 12c9c90 L100") )
	for offset in link_list_head:
		while offset != 0:
			metainfo = parse( DBG("dd %x" % offset) )
			yield offset, metainfo
			offset = metainfo[5]
			
def rfind_int(value_offset, value):
	for offset, metainfo in iter_metainfo():
		cmp_value = metainfo[value_offset / 4]
		if cmp_value == value:
			print "Offset = 0x%x" % offset
			return
	print "not found!"

def rfind_string(value_offset, value):
	for offset, metainfo in iter_metainfo():
		cmp_value = metainfo[value_offset / 4]
		string = eval(DBG("da %x" % cmp_value).split()[1])
		if string == value:
			print "Offset = 0x%x" % offset
			return
	print "not found!"
			
if __name__ == '__main__':
	find_method = sys.argv[1]
	if find_method == "hash":
		run(sys.argv[2])
	elif find_method == "int":
		rfind_int(int(sys.argv[2], 16), int(sys.argv[3], 16))
	elif find_method == "string":
		rfind_string(int(sys.argv[2], 16), sys.argv[3])