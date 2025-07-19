import os
import sys
import arc_unpack

LANG_SUFFIX = ("_eng.arc", "_fre.arc", "_ger.arc", "_ita.arc", "_jpn.arc", "_spa.arc")
			
def batch_unpack(lang="eng"):
	root = r"H:\GameInsider\GameRes\DMC4SE\DMC4SEM8\nativeDX10"
	for top, folders, files in os.walk(root):
		for fname in files:
			if fname.endswith(".arc"):
				# localization package
				is_lang_pack = False
				for lang_suffix in LANG_SUFFIX:
					if fname.endswith(lang_suffix):
						is_lang_pack = True
						break
				# extract the specified language version
				if is_lang_pack and not fname.endswith("_%s.arc" % lang):
					continue
				full_path = os.path.join(top, fname)
				print("unpacking", full_path)
				rel_path = os.path.relpath(full_path, root)
				out_root = r"H:\GameInsider\GameRes\DMC4SE\unpacked"
				# out_root = os.path.join(r"E:\dmc4se_data2", rel_path)[:-len(".arc")]
				arc_unpack.unpack(full_path, out_root)	
	
if __name__ == '__main__':
	kwargs = {}
	if len(sys.argv) > 1:
		kwargs["lang"] = sys.argv[1]
	batch_unpack(**kwargs)