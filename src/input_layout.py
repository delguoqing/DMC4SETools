# vertex data in DMC4SE are stored in a very compact way and the SematicName isn't quite
# reflect what it really is.
# One has to inspect the shader bytecode to see what that data are used for.
# Or One has to guess
def parse(vertex, input_layout_index):
	vertex_out = {
		"POSITION": vertex["POSITION"],
	}	
	if input_layout_index == 47:
		vertex_out["TEXCOORD"] = (vertex["BINORMAL"][2], vertex["BINORMAL"][3])
	elif input_layout_index == 56:
		vertex_out["TEXCOORD"] = (vertex["TANGENT"][0], vertex["TANGENT"][1])
	elif input_layout_index == 25:
		vertex_out["TEXCOORD"] = (vertex["BINORMAL"][0], vertex["BINORMAL"][1])
	elif input_layout_index == 20:
		vertex_out["TEXCOORD"] = (vertex["NORMAL"][0], vertex["NORMAL"][1])
	elif input_layout_index == 42:
		vertex_out["TEXCOORD"] = (vertex["BINORMAL"][0], vertex["BINORMAL"][1])
	elif input_layout_index == 55:
		vertex_out["TEXCOORD"] = (vertex["TANGENT"][0], vertex["TANGENT"][1])
	elif input_layout_index == 27:
		vertex_out["TEXCOORD"] = (vertex["BINORMAL"][0], vertex["BINORMAL"][1])
	elif input_layout_index == 43:
		vertex_out["TEXCOORD"] = (vertex["BINORMAL"][0], vertex["BINORMAL"][1])
	elif input_layout_index == 57:
		vertex_out["TEXCOORD"] = (vertex["TANGENT"][0], vertex["TANGENT"][1])
	elif input_layout_index == 25:
		
	else:
		assert False, "unsupported input layout index %d" % input_layout_index
	return vertex_out
	
		