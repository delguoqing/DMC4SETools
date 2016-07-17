import os
import sys
import cPickle
import ctypes

# win32api
from win32api import OpenProcess, GetProcAddress, GetModuleHandle
from win32con import *
from ctypes import wintypes
VirtualAllocEx = ctypes.windll.kernel32.VirtualAllocEx
WriteProcessMemory = ctypes.windll.kernel32.WriteProcessMemory
CreateRemoteThread = ctypes.windll.kernel32.CreateRemoteThread
WaitForSingleObject = ctypes.windll.kernel32.WaitForSingleObject
	
def get_func():
	f = open("windbg/hashtable.bin", "rb")
	table1, table2 = cPickle.load(f)
	print table2[0x330]
	def func(v, result, depth=0):
		def debug(*args):
			print "\t" * depth,
			print " ".join(map(str, args))
		debug("-------")
		debug("depth %d" % depth)
		if v & 0xFFFFF000:
			debug("[append 0x%x]" % (v & 0xFFFFF000))
			result.append(v & 0xFFFFFF000)
		idx = v & 0xFFF
		debug("idx=0x%x" % idx)
		flag, next1, next2 = table1[idx]
		debug("hex flag=0x%x" % flag)
		if flag & 0x3F00000:
			debug("=> flollow path 1")
			for idx2 in next1:
				debug("follow~ 0x%x" % idx2)
				v2 = table2[idx2]
				func(v2, result, depth+1)
		if flag & 0xFC000000:
			debug("=> flollow path 2")
			for idx2 in next2:
				v2 = table2[idx2]
				debug("follow~ 0x%x, v = 0x%x" % (idx2, v2))
				if v2:
					result.append(v2)
	return func

def test_get_func(v):
	func = get_func()
	result = []
	func(v, result)
	print map(hex, result)

def find_proc_id(proc_name):
	hSnapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot(2, None)
	# How do I pass an in/out parameter?
	lppe = ctypes.windll.kernel32.Process32First(hSnapshot, None)
	print lppe
	
def dll_inject(proc_id_or_name, dll_path):
	try:
		proc_id = int(proc_id_or_name)
	except ValueError:	# TODO: support proc_name later
		print "Do not support proc_name yet!"
		return
	# Attach
	hHandle = OpenProcess(
		(PROCESS_CREATE_THREAD | PROCESS_QUERY_INFORMATION | PROCESS_VM_OPERATION | \
		 PROCESS_VM_WRITE | PROCESS_VM_READ),
		FALSE, proc_id
	)
	print hHandle, int(hHandle)
	# Allocate memory
	full_path = os.path.normpath(os.path.abspath(dll_path))
	mem_addr = VirtualAllocEx(wintypes.HANDLE(int(hHandle)),
							  wintypes.LPVOID(0),
							  len(full_path) + 1,
							  wintypes.DWORD(MEM_RESERVE | MEM_COMMIT),
							  wintypes.DWORD(PAGE_EXECUTE_READWRITE))
	# Copy dll path
	WriteProcessMemory(wintypes.HANDLE(int(hHandle)), mem_addr, full_path, len(full_path),
					   None)
	# Get execution start point
	exe_start_addr = GetProcAddress(GetModuleHandle("kernel32.dll"), "LoadLibraryA")
	# Start thread
	thread = CreateRemoteThread(wintypes.HANDLE(int(hHandle)), None, 0, exe_start_addr,
								mem_addr, 0, None)
	WaitForSingleObject(thread, 0xFFFFFFFF)

if __name__ == '__main__':
	exp_id = 2
	
	if exp_id == 0:
		v = int(sys.argv[1], 16)
		test_get_func(v)
	elif exp_id == 1:
		dll_inject(14644, r"D:\Program Files (x86)\WinHex\zlib1.dll")
	elif exp_id == 2:
		find_proc_id("DevilMayCry4SpecialEdition.exe")
	
	
