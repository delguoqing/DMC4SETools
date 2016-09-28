import os
import bpy
import random
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props import (CollectionProperty, StringProperty, BoolProperty, EnumProperty, FloatProperty)

class PlayMotionOperator(bpy.types.Operator):
	bl_idname = "dmc4se.play_motion"
	bl_label = "Play Motion"
	
	def execute(self, context):
		motion = context.scene.motion
		model = context.scene.model
		play = getattr(self, "play_motion_%s" % model, self.play_motion_default)
		play(context, model, motion)		
		return {"FINISHED"}