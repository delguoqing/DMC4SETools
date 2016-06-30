import json
from pykd import dbgCommand as DBG

def parse(text):
	ret = []
	lines = text.split("\n")
	for line in lines:
		for tok in line.split()[1:]:
			ret.append(int(tok, 16))
	return ret
	
def run():
	link_list_head = parse( DBG("dd 12c9c90 L100") )
	hash_2_classname = {}
	
	for offset in link_list_head:
		while offset != 0:
			metainfo = parse( DBG("dd %x" % offset) )
			hashcode = metainfo[7]
			classname = DBG("da %x" % metainfo[1]).split()[1].strip("\"")
			offset = metainfo[5]
			hash_2_classname[hex(hashcode)] = classname
	
	f = open("hash_2_classname.json", "w")
	json.dump(hash_2_classname, f, indent=2)
	f.close()
				
if __name__ == '__main__':
	run()