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
	
# uPlayerNero -> uPlayer -> uActor -> uDevil4Model -> uModel -> uBaseModel -> uCoord -> cUnit -> MtObject
# uPlayerDante -> uPlayer -> ...

# uPlayerVergil -> uPlayerSE -> uPlayer -> uActor -> uDevil4Model -> uModel -> uBaseModel -> uCoord -> cUnit -> MtObject
# uPlayerLady -> uPlayerSE -> ...
# uPlayerTrish -> uPlayerSE -> ...

# cCnsChain -> cConstraint -> uModel::Constraint -> MtObject
# 
def run(class_hash):
	"""
		+0: factory vtable,
		+4: name,
		+8: ptr to metainfo
		+c: parent class metainfo
		+10:
		+14: next
		+18: 
		+1c: hash
	"""
	class_hash = int(class_hash, 16)
	link_list_head = parse( DBG("dd 12c9c90 L100") )
	offset = link_list_head[class_hash & 0xFF]
	while offset != 0:
		metainfo = parse( DBG("dd %x" % offset) )
		hashcode = metainfo[7]
		classname = DBG("da %x" % metainfo[1]).split()[1].strip("\"")
		if hashcode == class_hash:
			print("offset = %x, %s" % (offset, classname))
			vtable = metainfo[0]
			print("vtable: %x" % vtable)
			methods = parse( DBG("dd %x" % (vtable - 36)) )
			print("Method: Get Extendsion At: %x" % methods[0])
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
			return offset
	return None

def rfind_string(value_offset, value):
	for offset, metainfo in iter_metainfo():
		cmp_value = metainfo[value_offset / 4]
		string = eval(DBG("da %x" % cmp_value).split()[1])
		if string == value:
			return offset
	return None
			
def rfind_parent(name):
	for offset, metainfo in iter_metainfo():
		cmp_value = metainfo[1]
		if name == eval(DBG("da %x" % cmp_value).split()[1]):
			return _rfind_parent(metainfo)
	return None

def _rfind_parent(metainfo):
	if metainfo is None:
		return []
	chain = []
	name = eval(DBG("da %x" % metainfo[1]).split()[1])
	chain.append(name)
	while chain[-1] != "MtObject":
		parent = metainfo[4]
		if not parent:
			break
		metainfo = parse( DBG("dd %x" % parent) )
		chain.append( eval(DBG("da %x" % metainfo[1]).split()[1]) )
	return chain			
	
def rfind_parent_all():
	chain_map = {}
	for offset, metainfo in iter_metainfo():
		chain = _rfind_parent(metainfo)
		chain_map[chain[0]] = tuple(chain)
		print("collected: %s" % chain[0])
	return chain_map

if __name__ == '__main__':
	find_method = sys.argv[1]
	if find_method == "hash":
		run(sys.argv[2])
	elif find_method == "parent":
		chain = rfind_parent(sys.argv[2])
		if not chain:
			print("not found!")
		else:
			print(" -> ".join(chain))
	elif find_method == "parent_all":
		chain_map = rfind_parent_all()
		f = open(sys.argv[2], "wb")
		for chain in chain_map.values():
			f.write((" -> ".join(chain)) + "\n")
		f.close()
	else:
		if find_method == "int":
			offset = rfind_int(int(sys.argv[2], 16), int(sys.argv[3], 16))
		elif find_method == "string":
			offset = rfind_string(int(sys.argv[2], 16), sys.argv[3])
		if offset is not None:
			print("Offset = 0x%x" % offset)
		else:
			print("not found!")			