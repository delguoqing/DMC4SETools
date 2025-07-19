"""
because there're a LOT of shader compiled with different macros can't get much useful
information.
"""
import os
import subprocess
import argparse

SA_ROOT = os.path.join(os.environ["DMC4SE_DATA_DIR"], "sa")
FXC = os.path.join(os.environ["DXSDK_DIR"], r"Utilities\bin\x86\fxc.exe")

def run(root):
	bytecodes = []
	for top, dirs, files in os.walk(root):
		for fname in files:
			if fname.endswith(".SPK"):
				print("finding DXBC in", fname)
				spk_path = os.path.join(top, fname)
				bytecodes.extend(get_dxbc(spk_path))
				print("DXBC Set Size = %d" % (len(bytecodes)))
				
	for i, dxbc in enumerate(bytecodes):
		tmp = open("tmp.dxbc", "wb")
		tmp.write(dxbc)
		tmp.close()
		
		cmd = "%s /dumpbin /Fc tmp\\%d.txt tmp.dxbc" % (FXC, i)
		print(cmd)
		subprocess.call(cmd)
	
def get_dxbc(spk_path):
	f = open(spk_path, "rb")
	bytecodes = ["DXBC" + v for v in f.read().split("DXBC")[1:]]
	f.close()
	return bytecodes

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description="disassemble all shaders in a directory.")
	parser.add_argument("root", default=SA_ROOT)
	args = parser.parse_args()
	run(args.root)