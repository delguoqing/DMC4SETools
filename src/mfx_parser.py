import os
import sys
import struct
import json
import util
from d3d10.dxgi_format import *
	
class CStringTable(object):
	
	def __init__(self, raw):
		self.off_2_str = {}
		self.raw = raw
		
	def get_string(self, offset):
		string = self.off_2_str.get(offset)
		if string is None:
			str_beg = offset
			str_end = self.raw.find("\x00", str_beg)
			string = self.off_2_str[offset] = self.raw[str_beg: str_end]
		return string
	
class CMfxHeader(object):
	
	def read(self, getter):
		fourcc = getter.get("4s")
		assert fourcc == "MFX\x00"
		reserved_4, reserved_6 = getter.get("HH")
		assert reserved_4 == 0x35 and reserved_6 == 0x21
	
		field_8 = getter.get("I")
		mfx_entry_count = getter.get("I") - 1
		self.string_table_offset = getter.get("I")
		field_14 = getter.get("I")
		self.mfx_entry_offsets = getter.get("%dI" % mfx_entry_count)
	
class CMfxEntry(object):
	
	def read(self, getter, string_table):
		self.input_layout = []
		str_offset = getter.get("I")
		str_offset2 = getter.get("I")
		string = string_table.get_string(str_offset)
		string2 = string_table.get_string(str_offset2)
		field_8 = getter.get("I")
		field_8_a = field_8 & 0x3F
		field_8_b = (field_8 >> 6) & 0xFFFF
		field_8_c = field_8 >> 22
		field_C = getter.get("I")
		field_10 = getter.get("I")
		field_14 = getter.get("I")
		print string, string2, field_8_a, hex(field_14)
		# parse an entry according to different types
		if field_8_a == 9:
			field_18 = getter.get("H")
			print "attribute count", field_18
			getter.skip(2 + 4)
			size = 0
			max_size = 0
			for i in xrange(field_18):
				_str_offset = getter.get("I")
				string = string_table.get_string(_str_offset)
				v = getter.get("I")
				comp_type = (v >> 6) & 0x1F	# component type
				comp_count = (v >> 11) & 0x7F	# component count?
				base_off = (v >> 22) & 0x1FF
				instancing = (v >> 31) & 0x1
				index = v & 0x3F	# e.g. suffix in TexcoordN
				# 0xe: Color
				# 0xb: Normal
				# 0xc: ?
				if comp_type in (0xe, 0xb, 0xc):
					size = 4
				else:
					size = comp_count * (0, 4, 2, 2, 2, 2, 2, 1, 1, 1, 1, 4, 4, 1, 4)[comp_type]
				max_size = max(max_size, base_off + size)
				print "name:%s, type:0x%x, count:%d, off=0x%x, size:0x%x, instancing:%d, index:%d" % (
					string, comp_type, comp_count, base_off, size, instancing, index,
				)
				
				# dump input layout
				self.input_layout.append({
					"sematics": string,
					"offset": base_off,
					"component_count": comp_count,
				})
				assert comp_type != 0xc
				if comp_type in (0xb, 0xe):
					self.input_layout[-1]["component_count"] = 4
				if index != 0:
					self.input_layout[-1]["sematics"] += str(index)
					
			print "total size", max_size
					
		elif field_8_a == 7:
			field_18 = getter.get("H")
		elif field_8_a == 2:	# kind of function
			pass
		elif field_8_a == 0:
			pass
		elif field_8_a == 8:
			pass				
		else:
			return
							
def parse(path):
	f = open(path, "rb")
	getter = util.get_getter(f, "<")
	# read header
	header = CMfxHeader()
	header.read(getter)
	# read string table
	getter.seek(header.string_table_offset)
	raw_string_table = getter.get_raw(getter.size - getter.offset)
	string_table = CStringTable(raw_string_table)
	# read MfxEntry
	mfx_entries = []
	for i, mfx_entry_offset in enumerate(header.mfx_entry_offsets):
		getter.seek(mfx_entry_offset)
		mfx_entry = CMfxEntry()
		print i,
		mfx_entry.read(getter, string_table)
		mfx_entries.append(mfx_entry)
		
	f.close()
	
	fout = open("windbg/input_layouts2.json", "w")
	input_layouts = [{}]
	for mfx_entry in mfx_entries:
		input_layouts.append(mfx_entry.input_layout)
	while input_layouts and not input_layouts[-1]:
		input_layouts.pop(-1)
	json.dump(input_layouts, fout, indent=2)
	fout.close()
				
if __name__ == '__main__':
	parse(sys.argv[1])