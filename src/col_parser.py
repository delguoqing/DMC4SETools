import sys
import os
import subprocess
import util


def parse(col_path):
	col_f = open(col_path, "rb")
	col = util.get_getter(spk_f, "<")

	fourcc = col.get("4s").rstrip("\x00")
	assert fourcc == "COL"
	

if __name__ == '__main__':
	parse(sys.argv[1])