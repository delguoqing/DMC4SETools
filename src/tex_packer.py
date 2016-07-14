import sys
from PIL import Image

# Very Simple Packer
# packs UI texture with no compression
def pack(path):
	f = open(path, "rb")
	header = f.read(20)
	f.close()
	
	image = Image.open(path.replace(".tex", ".png"))
	fout = open(path + ".mod", "wb")
	fout.write(header + image.tobytes())
	fout.close()
	
if __name__ == '__main__':
	pack(sys.argv[1])