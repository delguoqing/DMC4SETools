import sys
import cPickle

def get_func():
	f = open("windbg/hashtable.bin", "rb")
	table1, table2 = cPickle.load(f)
	print table2[0x330]
	def func(v, result, depth=0):
		def debug(*args):
			print "\t" * depth,
			print " ".join(map(str, args))
		debug("-------")
		debug("depth %d" % depth)
		if v & 0xFFFFF000:
			debug("[append 0x%x]" % (v & 0xFFFFF000))
			result.append(v & 0xFFFFFF000)
		idx = v & 0xFFF
		debug("idx=0x%x" % idx)
		flag, next1, next2 = table1[idx]
		debug("hex flag=0x%x" % flag)
		if flag & 0x3F00000:
			debug("=> flollow path 1")
			for idx2 in next1:
				debug("follow~ 0x%x" % idx2)
				v2 = table2[idx2]
				func(v2, result, depth+1)
		if flag & 0xFC000000:
			debug("=> flollow path 2")
			for idx2 in next2:
				v2 = table2[idx2]
				debug("follow~ 0x%x, v = 0x%x" % (idx2, v2))
				if v2:
					result.append(v2)
	return func

func = get_func()

if __name__ == '__main__':
	v = int(sys.argv[1], 16)
	result = []
	func(v, result)
	print map(hex, result)
	
