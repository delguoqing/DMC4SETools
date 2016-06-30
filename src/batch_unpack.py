import os
import sys
import arc_unpack

LANG_SUFFIX = ("_eng.arc", "_fre.arc", "_ger.arc", "_ita.arc", "_jpn.arc", "_spa.arc")

root = r"F:\Games\dmc4_special\DMC4.Special.Edition-RAS\Special Edition\nativeDX10"
for top, folders, files in os.walk(root):
	for fname in files:
		if fname.endswith(".arc"):
			# localization package
			is_lang_pack = False
			for lang_suffix in LANG_SUFFIX:
				if fname.endswith(lang_suffix):
					is_lang_pack = True
					break
			# extract japanese version
			if is_lang_pack and not fname.endswith("_jpn.arc"):
				continue
			full_path = os.path.join(top, fname)
			print "unpacking", full_path
			rel_path = os.path.relpath(full_path, root)
			out_root = r"E:\dmc4se_data2"
			# out_root = os.path.join(r"E:\dmc4se_data2", rel_path)[:-len(".arc")]
			arc_unpack.unpack(full_path, out_root)