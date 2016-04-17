import sys
import json

INPUT_LAYOUT_START_MARK = "============ InputLayout ========="
ELEMENT_COUNT_HEAD = "Element Count:"
SEMATIC_NAME_HEAD = "SematicName"
SEMATIC_INDEX_HEAD = "SematicIndex"
FORMAT_HEAD = "Format"

def gen(fpath, outpath):
	fvf_index_2_input_element_descs = {
	}
	
	i = 0
	f = open(fpath)
	for line in f:
		if line.startswith(INPUT_LAYOUT_START_MARK):
			i += 1
			fvf_index_2_input_element_descs[i] = []
		elif line.startswith(ELEMENT_COUNT_HEAD):
			pass
		elif line.startswith(SEMATIC_NAME_HEAD):
			fvf_index_2_input_element_descs[i].append({
				SEMATIC_NAME_HEAD: line[len(SEMATIC_NAME_HEAD):].strip()
			})
		elif line.startswith(SEMATIC_INDEX_HEAD):
			fvf_index_2_input_element_descs[i][-1][SEMATIC_INDEX_HEAD] = \
				int(line[len(SEMATIC_INDEX_HEAD):].strip())
		elif line.startswith(FORMAT_HEAD):
			fvf_index_2_input_element_descs[i][-1][FORMAT_HEAD] = \
				int(line[len(FORMAT_HEAD):].strip())
	
	fout = open(outpath, "w")
	json.dump(fvf_index_2_input_element_descs, fout, indent=2)
	fout.close()
			  
if __name__ == '__main__':
	gen(sys.argv[1], sys.argv[2])