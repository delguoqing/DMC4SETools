import os
import sys
import arc_unpack
root = r"F:\Games\dmc4_special\DMC4.Special.Edition-RAS\Special Edition\nativeDX10"
for top, folders, files in os.walk(root):
	for fname in files:
		if fname.endswith(".arc"):
			full_path = os.path.join(top, fname)
			print "unpacking", full_path
			rel_path = os.path.relpath(full_path, root)
			out_root = os.path.join(r"E:\dmc4se_data", rel_path)[:-len(".arc")]
			arc_unpack.unpack(full_path, out_root)