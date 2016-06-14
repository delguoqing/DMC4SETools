bl_info = {
	"name": "Game To Blender Format",
	"author": "Qing Guo",
	"blender": (2, 76, 0),
	"location": "File > Import-Export",
	"description": "Import GTB mesh file.",
	"warning": "",
	"category": "Import-Export"}

# To support reload properly, try to access a package var,
# if it's there, reload everything
if "bpy" in locals():
	import importlib
	if "gtb_importer" in locals():
		importlib.reload(gtb_importer)
		
import os
import bpy
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props import (CollectionProperty, StringProperty, BoolProperty, EnumProperty, FloatProperty)
		
class ImportGTB(bpy.types.Operator, ImportHelper):
	"""Load a GTB mesh file."""
	bl_idname = "import_mesh.gtb"
	bl_label = "Import GTB"
	bl_options = {'UNDO'}

	files = CollectionProperty(name="File Path",
						  description="File path used for importing the GTB mesh file",
						  type=bpy.types.OperatorFileListElement)

	directory = StringProperty()

	filename_ext = ".gtb"
	filter_glob = StringProperty(default="*.gtb", options={'HIDDEN'})

	def execute(self, context):
		path = os.path.join(self.directory, self.files[0].name)

		from . import gtb_importer
		gtb_importer.import_gtb(path)

		return {'FINISHED'}

def menu_func_import(self, context):
	self.layout.operator(ImportGTB.bl_idname, text="Game To Blender Mesh (.gtb)")
		
def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_file_import.append(menu_func_import)
	
def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_file_import.remove(menu_func_import)

if __name__ == '__main__':
	register()