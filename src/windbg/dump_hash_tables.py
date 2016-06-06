import cPickle
from pykd import dbgCommand as DBG

def parse(text):
	ret = []
	lines = text.split("\n")
	for line in lines:
		for tok in line.split()[1:]:
			ret.append(int(tok, 16))
	return ret
	
def run():
	# table size: 0x1000, element size: 2 dword
	table1 = []
	raw = parse( DBG("dd @esi L2000") )
	for i in xrange(0, len(raw), 2):
		flag, pidx = raw[i: i + 2]
		next1 = ()
		next2 = ()
		if flag & 0x3F00000:
			loop_count = ((flag & 0x3F00000) >> 20)
			next1 = parse( DBG("dw %x L%x" % (pidx, loop_count)) )
			pidx += loop_count * 2
		if flag & 0xFC000000:
			loop_count = ((flag & 0xFC000000) >> 26)
			next2 = parse( DBG("dw %x L%x" % (pidx, loop_count)) )
			pidx += loop_count * 2
		table1.append((flag, tuple(next1), tuple(next2)))
		
	# table2
	table2 = parse( DBG("dd poi(@esp+40) L2000") )[1::2]
	
	fout = open("hashtable.bin", "wb")
	cPickle.dump((tuple(table1), tuple(table2)), fout)
	fout.close()
	
if __name__ == '__main__':
	run()