import os
import sys
import util
import zlib
import json

FOURCC = "ARC\x00"
VERSION = 0x7
ENDIAN = "<"

f = open("windbg/hash_2_classname.json", "r")
hash_2_classnames = json.load(f)
f.close()

class_name_to_extension = {
	"rTexture": "tex",
	"rSoundStreamRequest": "stqr",
	"rEffectList": "efl",
	"rArchive": "arc",
	"rEffectAnim": "ean",
	"rMaterial": "mrl",
	"rModel": "mod",
	"rMotionList": "lmt",
	"rCnsChain": "clt",
	"rCollisionShape": "col",
	"rStreamScheduler": "ssd",
	"rCameraList": "lcm",
	"rScheduler": "sdl",
	"rMessage": "msg",
	"rEffectStrip": "efs",
	"rSoundBank": "sbkr",
	"rSoundRandom": "srd",
	"rSoundRequest": "srqr",
	"rVibration": "vib",
	"rGUI": "gui",
	"rGUIIconInfo": "gii",
	"rGUIFont": "gfd",
	"rRenderTargetTexture": "rtex",
	"rSoundCurveSet": "scsr",
	"rSoundDirectionalSet": "sdsr",
	"rSoundReverb": "revr",
	"rSoundEQ": "equr",
	"rCnsTinyChain": "ctc",
	"rEffect2D": "e2d",
	"rShaderCache": "sch",
	"rAttackStatusData": "atk",
	"rDefendStatusData": "dfd",
	"rCollisionIdxData": "idx",
	"rCollision": "sbc",
	"rChainCol": "ccl",
	"rGeometry3": "geo3",
	"rGeometry2": "geo2",
	"rAttributeSe": "ase",
	"rMotionSe": "msse",
	"rSndIf": "sif",
	"rSoundEngine": "engr",
	"rSoundEngineValue": "egvr",
	"rRouteNode": "rut",
	"rGUIMessage": "gmd",
	"rSprAnm": "anm",
	"rSoundSeg": "seg",
	"rCharTbl": "bin",
	"rPlParamTbl": "bin",
	"rPlayerParamLady": "ppl",
	"rPlAutomaticTable": "pat",
	"rPlayerParamTrish": "ppt",
	"rPlayerParamVergil": "ppv",
	"rRoomDefault": "rdf",
	"rPlacement": "pla",
	"rEventHit": "evh",
	"rDevilCamera": "cam",
	"rShaderPackage": "spkg",
	"rMotionEffect": "mef",
	"rMotionWind": "mwd",
	"rSprLayout": "sprmap",
	"rSoundSourceMSADPCM": "wav",
	"rSoundSourceOggVorbis": "sngw",
}

def unpack(fpath, out_root=".", dry_run=False):
	f = open(fpath, "rb")
	getter = util.get_getter(f, ENDIAN)
	get = getter.get
	seek = getter.seek
	# header
	fourcc, version, filecnt = get("4s2H")
	assert fourcc == FOURCC
	assert version == VERSION
	
	arc_prefix = os.path.splitext(os.path.split(fpath)[1])[0]
	# filelist
	filelist = []
	for file_idx in xrange(filecnt):
		offset = getter.offset
		file_path = get("64s").rstrip("\x00")
		assert "\x00" not in file_path
		unk1, comp_size, unk2, offset = get("4I")
		filelist.append((file_path, offset, comp_size, unk1, unk2))
	
	for file_path, offset, size, class_hash, crc32 in filelist:
		seek(offset)
		data = getter.get_raw(size)
		data_decomp = zlib.decompress(data)
		
		class_name = hash_2_classnames.get(hex(class_hash), "")
		ext = class_name_to_extension.get(class_name, "")
		if not ext:
			if class_name:
				ext = class_name
			elif data_decomp.startswith("<?xml"):
				ext = "xml"
			elif data_decomp.startswith("MOT"):
				ext = "mot"

		outpath = file_path		
		final_outpath = outpath + "." + ext
		print hex(offset), final_outpath
		
		final_outpath = os.path.join(out_root, final_outpath)
		# sometimes, the same file from different arc file will collide
		# mostly in gui localization. It doesn't matter too much for me though.
		need_write = True
		while os.path.exists(final_outpath):
			print final_outpath
			f_old = open(final_outpath, "rb")
			data_old = f_old.read()
			f_old.close()
			if data_decomp == data_old:
				need_write = False
				break
			final_outpath += ".alias"
		if dry_run:
			need_write = False
			
		if need_write:
			try:
				util.dump_bin(data_decomp, final_outpath, mkdir=True)
			except IOError as e:
				print "hex_format", hex(class_hash)
				util.dump_bin(data_decomp, outpath + "_debug", mkdir=True)
				raise
	
	f.close()

if __name__ == '__main__':
	unpack(sys.argv[1], dry_run=True)