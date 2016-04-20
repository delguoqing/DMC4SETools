import struct
import numpy
from dxgi_format import *

ENDIAN = "<"

def get_format_size(fmt):
	size = {
		DXGI_FORMAT_R32G32B32_FLOAT: 0Xc,
		DXGI_FORMAT_R16G16B16A16_SNORM: 0x8,
		DXGI_FORMAT_R10G10B10A2_UNORM: 0x4,
		DXGI_FORMAT_R16G16_FLOAT: 0x4,
		DXGI_FORMAT_R8G8B8A8_UNORM: 0x4,
		DXGI_FORMAT_R8G8B8A8_SNORM: 0x4,
		DXGI_FORMAT_R16G16B16A16_FLOAT: 0x8,
		DXGI_FORMAT_R16G16_UINT: 0x4,
		DXGI_FORMAT_R8G8B8A8_UINT: 0x4,
	}.get(fmt)
	assert size is not None, "unsupported fmt: %d" % fmt
	return size

def parse_format(data, fmt):
	if fmt == DXGI_FORMAT_R16G16B16A16_SNORM:
		return (_parse_snorm16(data[0:2]),
				_parse_snorm16(data[2:4]),
				_parse_snorm16(data[4:6]),
				_parse_snorm16(data[6:8]))
	elif fmt == DXGI_FORMAT_R32G32B32_FLOAT:
		return (_parse_float(data[0:4]),
				_parse_float(data[4:8]),
				_parse_float(data[8:0xc]),
				1.0)
	elif fmt == DXGI_FORMAT_R10G10B10A2_UNORM:
		v = struct.unpack(ENDIAN + "I", data)[0]
		return (
			((v >> 0) & 1023) / 1023.0,
			((v >> 10) & 1023) / 1023.0,
			((v >> 20) & 1023) / 1023.0,
			((v >> 30) & 3) / 3.0,
		)
	elif fmt == DXGI_FORMAT_R16G16_FLOAT:
		return (
			_parse_float16(data[0:2]),
			_parse_float16(data[2:4]),
		)
	elif fmt == DXGI_FORMAT_R8G8B8A8_UNORM:
		return (
			_parse_unorm8(data[0:1]),
			_parse_unorm8(data[1:2]),
			_parse_unorm8(data[2:3]),
			_parse_unorm8(data[3:4]),
		)
	elif fmt == DXGI_FORMAT_R8G8B8A8_SNORM:
		return (
			_parse_snorm8(data[0:1]),
			_parse_snorm8(data[1:2]),
			_parse_snorm8(data[2:3]),
			_parse_snorm8(data[3:4]),
		)
	elif fmt == DXGI_FORMAT_R16G16B16A16_FLOAT:
		return (
			_parse_float16(data[0:2]),
			_parse_float16(data[2:4]),
			_parse_float16(data[4:6]),
			_parse_float16(data[6:8]),
		)
	elif fmt == DXGI_FORMAT_R16G16_UINT:
		return (
			_parse_uint16(data[0:2]),
			_parse_uint16(data[2:4]),
		)
	elif fmt == DXGI_FORMAT_R8G8B8A8_UINT:
		return struct.unpack("4B", data)
	else:
		assert False, "unsupported fmt: %d" % fmt

def _parse_snorm8(data):
	return struct.unpack(ENDIAN + "b", data)[0] / 127.0

def _parse_unorm8(data):
	return struct.unpack(ENDIAN + "B", data)[0] / 255.0

def _parse_snorm16(data):
	return struct.unpack(ENDIAN + "h", data)[0] / 32767.0

def _parse_float(data):
	return struct.unpack(ENDIAN + "f", data)[0]

def _parse_uint16(data):
	return struct.unpack(ENDIAN + "H", data)[0]

def _parse_float16(data):
	return numpy.frombuffer(data, dtype=numpy.dtype(ENDIAN + "f2"))[0]