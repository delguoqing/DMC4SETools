import os
import bpy
import random
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props import (CollectionProperty, StringProperty, BoolProperty, EnumProperty, FloatProperty)

class LoadModelOperator(bpy.types.Operator):
	bl_idname = "dmc4se.load_model"
	bl_label = "Load Model"
	
	def execute(self, context):
		# clear all model & armature
		if context.scene.objects:
			bpy.ops.object.mode_set(mode='OBJECT')
			bpy.ops.object.select_by_type(type='MESH')
			bpy.ops.object.delete(use_global=False)
			bpy.ops.object.select_by_type(type='ARMATURE')
			bpy.ops.object.delete(use_global=False)
		
		model = context.scene.model
		load = getattr(self, "load_model_%s" % model, self.load_model_default)
		load(context, model)
		
		return {"FINISHED"}
	
	def load_model_default(self, context, model):
		self._load_mod_file(model, model + ".gtb")
		
	def load_model_em000(self, context, model):
		self._load_mod_file(model, random.choice(("em000", "em000_01")) + ".gtb")

	def load_model_em001(self, context, model):
		self._load_mod_file(model, random.choice(("em001", "em001_02")) + ".gtb")
		
	def load_model_em009(self, context, model):
		self._load_model_parts(model, 6)
	
	def load_model_em015(self, context, model):
		self._load_model_parts(model, 3)

	def load_model_em018(self, context, model):
		self._load_model_parts(model, 2)
		
	def load_model_em021(self, context, model):
		self.load_model_default(context, model)
		for i in range(1, 6):
			self._load_mod_file(model, model + "_%02d" % i + ".gtb")

	def load_model_em026(self, context, model):
		self._load_model_parts(model, 2)
		
	def load_model_pl000(self, context, model):
		self._load_mod_file(model, "pl000.gtb", armat_name="armat_body")
		self._load_mod_file(model, "pl000_01.gtb", armat_name="armat_head")
		self._load_mod_file(model, "pl000_02.gtb", armat_name="armat_hair")
		self._load_mod_file(model, "pl000_03.gtb", armat_name="armat_coat")
		
		body = context.scene.objects["armat_body"]
		head = context.scene.objects["armat_head"]
		hair = context.scene.objects["armat_hair"]
		coat = context.scene.objects["armat_coat"]
		self._copy_transform(head, body, zip((0, 1, 2, 3, 4), (2, 3, 4, 5, 32)))
		self._copy_transform(hair, head, zip((0, 1), (1, 2)))
		self._copy_transform(coat, body, zip((0, ), (2, )))
		
	def load_model_pl000_ex00(self, context, model):
		self._load_mod_file(model, "pl000.gtb")

	def load_model_pl000_ex01(self, context, model):
		self._load_mod_file(model, "pl000.gtb")

	def load_model_pl006_ex00(self, context, model):
		self._load_mod_file(model, "pl006.gtb")

	def load_model_pl006_ex01(self, context, model):
		self._load_mod_file(model, "pl006.gtb")

	def load_model_pl007_ex01(self, context, model):
		self._load_mod_file(model, "pl007.gtb")

	def load_model_pl008_ex01(self, context, model):
		self._load_mod_file(model, "pl008.gtb")

	def load_model_pl024_ex00(self, context, model):
		self._load_mod_file(model, "pl024.gtb")

	def load_model_pl024_ex01(self, context, model):
		self._load_mod_file(model, "pl024.gtb")
		
	def load_model_pl030_ex00(self, context, model):
		self._load_mod_file(model, "pl030.gtb")

	def load_model_pl030_ex01(self, context, model):
		self._load_mod_file(model, "pl030.gtb")

	def _load_model_parts(self, model, n):
		for i in range(n):
			self._load_mod_file(model, model + "_%02d" % i + ".gtb")
			
	def _load_mod_file(self, model, mod_file, armat_name="armat"):
		bpy.ops.import_mesh.gtb(
			'EXEC_DEFAULT',
			directory=os.path.join(os.environ["DMC4SE_DATA_DIR"], "model/game/%s" % model),
			files=[{"name": mod_file}],
			armat_name=armat_name,
		)
	
	def _copy_transform(self, armt_dst, armt_src, bone_pairs):
		bpy.ops.object.mode_set(mode='OBJECT')
		bpy.context.scene.objects.active = armt_dst
		armt_dst.select = True
		bpy.ops.object.mode_set(mode='POSE')
		for i, j in bone_pairs:
			b = armt_dst.pose.bones["Bone%d" % i]
			armt_dst.data.bones.active = b.bone	# wtf, poorly documented
			bpy.ops.pose.constraint_add(type='COPY_TRANSFORMS')
			cns = b.constraints['Copy Transforms']
			cns.target = armt_src
			cns.subtarget = "Bone%d" % j
		bpy.ops.object.mode_set(mode='OBJECT')
		armt_dst.select = False
	