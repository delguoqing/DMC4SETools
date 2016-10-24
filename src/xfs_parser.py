# -*- coding: utf-8 -*-
import util

def parse(path):
	with open(path, "rb") as f:
		data = f.read()
	getter = util.get_getter(data, "<")
	
	header = getter.block(0x18)
	fourcc = header.get("4s")
	assert fourcc == "XFS\x00"
	unk0 = header.get("H")
	unk1 = header.get("H")
	assert unk0 & 0x7FFF == 0xF
	
	