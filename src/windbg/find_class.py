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
				
if __name__ == '__main__':
	run(sys.argv[1])