bl_info = {
	"name": "DMC4SE tool",
	"author": "Qing Guo",
	"blender": (2, 76, 0),
	"location": "View3D -> Tool Shelf -> DMC4SE tool",
	"description": "Tool that assists loading model & motion for DMC4SE.",
	"warning": "",
	"category": "Game Tool"}

import os
import bpy
import random
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props import (CollectionProperty, StringProperty, BoolProperty, EnumProperty, FloatProperty)
from .load_model_operator import LoadModelOperator
from .load_motion_operator import LoadMotionOperator, MOTION_FOLDER_MAP
		
def get_model_list():
	root = os.environ["DMC4SE_DATA_DIR"]
	model_root = os.path.join(root, "model/game")
	fnames = os.listdir(model_root)
	model_list = []
	for name in fnames:
		path = os.path.join(model_root, name)
		if not os.path.isdir(path):
			continue
		model_list.append((
			name, # identifier,
			name, # name,
			"", # description
			# icon(optional)
			# number(optional)
		))
	return model_list

def get_motion_list(self, context):
	model = context.scene.model
	root = os.environ["DMC4SE_DATA_DIR"]
	motion_folder = MOTION_FOLDER_MAP.get(model, model)
	motion_root = os.path.join(root, "motion/%s" % motion_folder)
	motion_list = []
	for dirpath, dirnames, filenames in os.walk(motion_root):
		for fname in filenames:
			if fname.endswith(".lmt"):
				name = os.path.splitext(fname)[0]
				name = os.path.normpath(os.path.join(dirpath, name))
				name = os.path.relpath(name, start=motion_root)
				motion_list.append((
					name, # identifier,
					name, # name,
					"", # description
					# icon(optional)
					# number(optional)
				))
	return motion_list

class DMC4SEPanel(bpy.types.Panel):
	bl_idname = "OBJECT_PT_dmc4se"
	bl_label = "DMC4SE Tool"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_context = 'objectmode'
	bl_category = 'Tools'
	
	def draw(self, context):
		layout = self.layout
		row = layout.row()
		row.prop(context.scene, "model", text="MOD")
		row.operator("dmc4se.load_model", text="Load")
		row = layout.row()
		row.prop(context.scene, "motion", text="MOT")
		row.operator("dmc4se.load_motion", text="Load")
	
def register():
	bpy.utils.register_class(DMC4SEPanel)
	bpy.utils.register_class(LoadModelOperator)
	bpy.utils.register_class(LoadMotionOperator)
	bpy.types.Scene.model = bpy.props.EnumProperty(
		items=get_model_list(),
		default="pl000",
		name="Model",
	)
	bpy.types.Scene.motion = bpy.props.EnumProperty(
		items=get_motion_list,
		name="Motion"
	)
	
def unregister():
	bpy.utils.unregister_class(DMC4SEPanel)
	bpy.utils.unregister_class(LoadModelOperator)
	bpy.utils.unregister_class(LoadMotionOperator)
	del bpy.types.Scene.model
	del bpy.types.Scene.motion

if __name__ == '__main__':
	register()