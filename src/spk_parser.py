import sys
import os
import subprocess
import util

FXC = os.path.join(os.environ["DXSDK_DIR"], r"Utilities\bin\x86\fxc.exe")

def parse(spk_fpath):
	spk_f = open(spk_fpath, "rb")
	spk = util.get_getter(spk_f, "<")
	
	spk_header = spk.block(0x24)
	assert spk_header.get("4s") == "SPK\x00"
	assert spk_header.get("I") == 0xe11e1e22
	assert spk_header.get("H") == 0x24
	shader_pair_count = spk_header.get("H")
	vs_count = spk_header.get("H")
	ps_count = spk_header.get("H")
	gs_count = spk_header.get("H")
	input_layout_count = spk_header.get("H")
	assert vs_count == input_layout_count
	spk_header.skip(0x8)
	dxbc_size = spk_header.get("I")
	spk_info_size = spk_header.get("I")
	assert dxbc_size + spk_info_size == spk.size
	spk_header.assert_end()
	
	spk_metadata = spk.block(spk_info_size - 0x24)
	dxbc = spk.block(dxbc_size)
	spk.assert_end()
	
	spk_f.close()

	pair_info_list = get_shader_pair_info(spk_metadata, shader_pair_count)
	assert_shader_pair_info_list(pair_info_list, vs_count, ps_count, gs_count)
	
	dump_vertex_shaders(spk_metadata, dxbc, 0, vs_count)
	dump_pixel_shaders(spk_metadata, dxbc, 0, ps_count)
	dump_shader_pair_info(spk_metadata, shader_pair_count)
	
	return spk_header, spk_metadata, dxbc, pair_info_list

def _dump_shaders(spk_metadata, dxbc, shader_info_off, start_index, shader_count,
				  ext=".txt"):
	spk_metadata.seek(shader_info_off + start_index * 0xc)
	for shader_index in range(start_index, start_index + shader_count):
		shader_size = spk_metadata.get("I") >> 0xA
		if shader_size == 0:
			continue
		spk_metadata.skip(4)
		dxbc_off = spk_metadata.get("I")
		dxbc.seek(dxbc_off)
		bytecode = dxbc.get_raw(shader_size)
		
		tmp = open("tmp.dxbc", "wb")
		tmp.write(bytecode)
		tmp.close()
		
		cmd = "%s /dumpbin /Fc tmp\\%d%s tmp.dxbc" % (FXC, shader_index, ext)
		print(cmd)
		subprocess.call(cmd)

def _dump_one_shader(spk_metadata, dxbc, shader_info_off, index, name):
	spk_metadata.seek(shader_info_off + index * 0xc)
	shader_size = spk_metadata.get("I") >> 0xA
	if shader_size == 0:
		return
	spk_metadata.skip(4)
	dxbc_off = spk_metadata.get("I")
	dxbc.seek(dxbc_off)
	bytecode = dxbc.get_raw(shader_size)
	
	tmp = open("tmp.dxbc", "wb")
	tmp.write(bytecode)
	tmp.close()
		
	cmd = "%s /dumpbin /Fc tmp\\%s tmp.dxbc" % (FXC, name)
	print(cmd)
	subprocess.call(cmd)
		
def dump_vertex_shaders(spk_metadata, dxbc, index, count):
	spk_metadata.seek(0xc)
	vs_info_off = spk_metadata.get("I")
	_dump_shaders(spk_metadata, dxbc, vs_info_off, index, count, ".vs")
		
def dump_pixel_shaders(spk_metadata, dxbc, index, count):
	spk_metadata.seek(0x10)
	ps_info_off = spk_metadata.get("I")
	_dump_shaders(spk_metadata, dxbc, ps_info_off, index, count, ".ps")

def dump_shader_pair_info(spk_metadata, shader_pair_count):
	pair_info_list = get_shader_pair_info(spk_metadata, shader_pair_count)
	for pair_index in range(shader_pair_count):
		vs_index, ps_index, gs_index, slot_desc_hashes, unknown_values = pair_info_list[pair_index]
		print("=========================")
		print("Shader Pair %d" % pair_index)
		print("Shaders:", vs_index, ps_index, gs_index, end=' ')
		print("Input Slot Desc Hashes", list(map(hex, slot_desc_hashes)))
		print("Unknowns", list(map(hex, unknown_values)))

def get_shader_pair_info(spk_metadata, shader_pair_count):
	spk_metadata.seek(0x4020)
	pair_info_list = []
	for pair_index in range(shader_pair_count):
		unknown_values = []
		pair_info = spk_metadata.block(0x2c)
		block0_index = pair_info.get("I")
		
		#pair_info.skip(0xc)
		unknown_values.extend(pair_info.get("3I"))
		
		vs_index, ps_index, gs_index = pair_info.get("IIi")
		input_layout_index = pair_info.get("I")
		block4_index = pair_info.get("I")
		
		#pair_info.skip(0x8)
		unknown_values.extend(pair_info.get("2I"))
		
		pair_info.assert_end()
		
		offset_backup = spk_metadata.offset
		spk_metadata.seek(0x8)
		input_layout_block_off = spk_metadata.get("I")
		spk_metadata.seek(input_layout_block_off + input_layout_index * 0x18)
		slot_desc_hashes = spk_metadata.get("4I")
		spk_metadata.seek(offset_backup)
		pair_info_list.append((vs_index, ps_index, gs_index, slot_desc_hashes, unknown_values))
		
	return pair_info_list

def assert_shader_pair_info(shader_pair_info, vs_count, ps_count, gs_count):
	vs_index, ps_index, gs_index = shader_pair_info[:3]
	assert vs_index < vs_count
	assert ps_index < ps_count
	assert gs_index == -1 or gs_index < gs_count

def assert_shader_pair_info_list(pair_info_list, vs_count, ps_count, gs_count):
	vs_range = set()
	ps_range = set()
	gs_range = set()
	for pair_info in pair_info_list:
		vs_index, ps_index, gs_index = pair_info[:3]
		assert_shader_pair_info(pair_info, vs_count, ps_count, gs_count)
		vs_range.add(vs_index)
		ps_range.add(ps_index)
		if gs_index != -1:
			gs_range.add(gs_index)

	assert sorted(list(vs_range)) == list(range(vs_count))
	assert sorted(list(ps_range)) == list(range(ps_count))
	assert sorted(list(gs_range)) == list(range(gs_count))
	
def test_all():
	SA_ROOT = os.path.join(os.environ["DMC4SE_DATA_DIR"], "sa")
	for top, dirs, files in os.walk(SA_ROOT):
		for fname in files:
			if fname.endswith(".SPK"):
				print("parsing", fname)
				parse(os.path.join(top, fname))

def find_shader(input_layout_index):
	from input_layout_hash_2_index import DATA as HASH2INDEX
	SA_ROOT = os.path.join(os.environ["DMC4SE_DATA_DIR"], "sa")
	hit_index = 0
	for top, dirs, files in os.walk(SA_ROOT):
		for fname in files:
			if fname.endswith(".SPK"):
				print("parsing", fname)
				spk_header, spk_metadata, dxbc, shader_pair_info_list = \
															parse(os.path.join(top, fname))
				for vs_index, ps_index, gs_index, slot_descs_hashes, unkown_values in shader_pair_info_list:
					cmp_index = HASH2INDEX[slot_descs_hashes[0] >> 0xc]
					print("comparing with", cmp_index, input_layout_index)
					if cmp_index == input_layout_index:
						spk_metadata.seek(0xc)
						vs_info_off = spk_metadata.get("I")
						_dump_one_shader(spk_metadata, dxbc, vs_info_off, vs_index, "%d.vs" % hit_index)
						spk_metadata.seek(0x10)
						ps_info_off = spk_metadata.get("I")
						_dump_one_shader(spk_metadata, dxbc, ps_info_off, ps_index, "%d.ps" % hit_index)
						hit_index += 1
				
if __name__ == '__main__':
	#find_shader(int(sys.argv[1]))
	#test_all()
	parse(sys.argv[1])