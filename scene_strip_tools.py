# Scene Strip Tools

# About:
# Sequencer Preview in 3D Viewport sets up the Video Editor to
# control the camera selection in the 3D View on frame updates.
# Which makes it possible to edit the clip timings on the same
# screen and at the same time as editing cameras and everything
# else in the 3D Viewport.

# Run the script:
# 1. Run the script in the text-editor.
# 2. Find the functions in the bottom of the right-hand-side
#    properties menu of the 3D View.

# Functions:
# "Add 3D Camera to Sequencer" will add a scene strip
# in the Sequencer with the current camera starting from the
# current frame.

# "Link Sequencer to 3D Viewport" will switch cameras in the 3D
# View acording to the timings of the scene strips in the sequencer.

# Convert 'Bind Camera to Markes' to Scene Strips

# Toggle to Scene Strip Scene changes the scene to the scene linked from the Scene Strip.

# NB.:
# - Jitter in the Sequencer playback means hit "Refresh Sequencer" button.


bl_info = {
    "name": "Scene Strip Tools",
    "author": "Tintwotin",
    "version": (0, 2),
    "blender": (2, 80, 0),
    "location": "Sequencer Sidebar Scene Strip Tools, Add Menu and Context Menu",
    "description": "Preview Sequencer Scene Strip edits in the 3D Viewport",
    "warning": "",
    "wiki_url": "https://github.com/tin2tin/PrevizCameraTools/",
    "category": "Sequencer"}


import bpy
import mathutils
from mathutils import Matrix
from bpy.utils import register_class, unregister_class
from bpy.props import BoolProperty, EnumProperty
from bpy.types import Panel, Menu
from rna_prop_ui import PropertyPanel
from operator import attrgetter

# Set 3D View to Global. Cameras can't be switched in local.
# Def currently not working


def set3d_view_global():
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces[0]
            if space.local_view:  # check if using local view
                for region in area.regions:
                    if region.type == 'WINDOW':
                        override = {'area': area, 'region': region}  # override context
                        bpy.ops.view3d.localview(override)  # switch to global view


# ------------------------------------------------------------------------
#     Swich 3D Viewport-Cameras from Sequencer
# ------------------------------------------------------------------------

oldStrip = ""


def swich_camera_at_frame_change(*pArgs):

    global oldStrip
    scn = bpy.context.scene
    seq = scn.sequence_editor.sequences
    seq = sorted(seq, key=attrgetter('channel', 'frame_final_start'))
    cf = scn.frame_current

    for i in seq:
        try:
            if i.type == "SCENE" and i.name != oldStrip:
                if (i.frame_final_start <= cf
                and i.frame_final_end > cf
                and i.scene.name == bpy.context.scene.name  # Only if current scene in scene-strip
                and not i.mute):
                    for area in bpy.context.screen.areas:
                        if area.type == 'VIEW_3D':
                            bpy.context.scene.camera = bpy.data.objects[i.scene_camera.name]  # Select camera as view
                            area.spaces.active.region_3d.view_perspective = 'CAMERA'  # Use camera view
                            oldStrip = i.name
                            break

        except AttributeError:
            pass


# ------------------------------------------------------------------------
#     Un/link 3D Cameras from/to Sequencer at frame change
# ------------------------------------------------------------------------

def attach_as_handler():
    bpy.app.handlers.frame_change_pre.append(swich_camera_at_frame_change)


def detach_as_handler():
    bpy.app.handlers.frame_change_pre.clear()


# ------------------------------------------------------------------------
#     Make 3D Preview Panel
# ------------------------------------------------------------------------

class PropertyGroup(bpy.types.PropertyGroup):

    link_seq_to_3d_view: bpy.props.BoolProperty(
        name='Link Sequencer to 3D View',
        description='Let scene strips swich cameras in 3D Viewport')


class SEQUENCER_PT_scene_tools(Panel):
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'
    bl_idname = "SEQUENCER_PT_scene_tools"
    bl_label = "Scene Strip Tools"
    bl_category = "Scene Strip Tools"

    @classmethod
    def poll(cls, context):
#        if not cls.has_sequencer(context):
#            return False

        return True

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=(False))
        #col.use_property_split = False
        col = col.box()
        manager = context.scene.asset_manager

        col.prop(manager, "link_seq_to_3d_view", text="Link Sequencer to 3D Viewport", icon="LINKED")
        col.operator("view3d.add_scene_strip", text="Add Camera as Scene Strip", icon="CAMERA_DATA")
        col.operator("sequencer.convert_cameras", text="Convert Camera Markers to Strips", icon="MARKER")
        col.operator("sequencer.change_scene", text="Toggle Scene Strip", icon="VIEW3D")

        # check if bool property is enabled
        if (context.scene.asset_manager.link_seq_to_3d_view == True):
            swich_camera_at_frame_change()
            attach_as_handler()
        else:
            detach_as_handler()


# ------------------------------------------------------------------------
#     Add Camera as Scene Strip in Sequencer
# ------------------------------------------------------------------------

class THREEDPREVIEW_PT_add_scene_strip(bpy.types.Operator):
    """Adds current camera as a scene strip to the Sequencer"""
    bl_idname = "view3d.add_scene_strip"
    bl_label = "Camera"
    bl_options = {'REGISTER', "UNDO"}

    def invoke(self, context, event):

        if not bpy.context.scene.sequence_editor:
            bpy.context.scene.sequence_editor_create()
        scn = bpy.context.scene
        seq = scn.sequence_editor
        cf = scn.frame_current
        addSceneIn = cf
        addSceneOut = scn.frame_end
        addSceneChannel = 2
        addSceneTlStart = cf
        newScene = seq.sequences.new_scene('Scene', bpy.context.scene, addSceneChannel, addSceneTlStart)
        seq.sequences_all[newScene.name].scene_camera = bpy.data.objects[bpy.context.scene.camera.name]
        seq.sequences_all[newScene.name].animation_offset_start = addSceneIn
        seq.sequences_all[newScene.name].frame_final_end = addSceneOut
        seq.sequences_all[newScene.name].frame_start = cf

        return {"FINISHED"}


# ------------------------------------------------------------------------
#     Add Camera Markers as Scene Strips in Sequencer
# ------------------------------------------------------------------------

class SEQUENCE_PT_convert_cameras(bpy.types.Operator):
    """Converts 'Bind Camera To Markers' to Scene Strips"""
    bl_label = "Convert Camera Markers"
    bl_idname = "sequencer.convert_cameras"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = bpy.context.scene

        if not bpy.context.scene.sequence_editor:  # create sequence, if missing
            bpy.context.scene.sequence_editor_create()

        marker_camera = []
        marker_frame = []
        marker_name = []
        cam_marker = []
        cnt = 0
        mi = bpy.context.scene.timeline_markers.items()
        for marker in scene.timeline_markers:  # find the cameras and their frame

            if marker.camera:
                cam_marker.insert(cnt, [marker.frame, marker.camera.name])  # mi[cnt][0]])
                cnt += 1

        if len(cam_marker) == 0:         # cancel if no cameras
            return {'CANCELLED'}

        cam_marker = sorted(cam_marker, key=lambda mark: mark[0])  # Sort the markers after frame nr.

        # add cameras to sequencer
        cnt = 0  # counter
        for i in cam_marker:
            cf = cam_marker[cnt][0]
            addSceneIn = cf

            if cnt < len(cam_marker)-1:  # find out frame
                addSceneOut = cam_marker[cnt+1][0]
            else:
                addSceneOut = addSceneIn+151  # last clip extented 30 fps*5 frames + an ekstra frame for the hack.
                bpy.context.scene.frame_end = addSceneIn+150  # extent preview area or add scene strip may fail

            addSceneChannel = 1          # attempt to add in this channel - if full, strips will be moved upwards
            addSceneTlStart = cf

            # Hack: adding a scene strip will make a hard cut one frame before preview area end.
            bpy.context.scene.frame_end = bpy.context.scene.frame_end+1

            # add scene strip in current scene at in and out frame numbers
            newScene = bpy.context.scene.sequence_editor.sequences.new_scene(cam_marker[cnt][1], bpy.context.scene, addSceneChannel, addSceneTlStart)
            newScene.scene_camera = bpy.data.objects[cam_marker[cnt][1]]
            newScene = bpy.context.scene.sequence_editor.sequences_all[newScene.name]
            newScene.animation_offset_start = addSceneIn
            newScene.frame_final_end = addSceneOut
            newScene.frame_start = cf
            cnt += 1

            # Hack: remove the extra frame again of the preview area.
            bpy.context.scene.frame_end = bpy.context.scene.frame_end-1

        return {'FINISHED'}

# ------------------------------------------------------------------------
#     Toggle change to scene strip in 3d view
# ------------------------------------------------------------------------


def act_strip(context):
    try:
        return context.scene.sequence_editor.active_strip
    except AttributeError:
        return False


class values():
    prev_scene_change = ""


class SEQUENCER_OT_scene_change(bpy.types.Operator):
    """Change scene to active strip scene"""
    bl_idname = "sequencer.change_scene"
    bl_label = "Toggle Scene Strip"
    bl_description = "Change scene to active strip scene"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        if context.scene:
            return True
        else:
            return False

    def execute(self, context):
        if not bpy.context.scene.sequence_editor:
            bpy.context.scene.sequence_editor_create()
        strip = act_strip(context)
        scene = bpy.context.scene
        sequence = scene.sequence_editor

        if strip != None:                                                               # save camera
            if strip.type == "SCENE":
                if sequence.sequences_all[strip.name].scene_input == 'CAMERA' and strip.scene_camera != None:
                    camera = strip.scene_camera.name

        if strip == None:                                                               # no active strip
            if values.prev_scene_change != "":                                           # a previous scene - go back
                win = bpy.context.window_manager.windows[0]
                win.scene = bpy.data.scenes[values.prev_scene_change]
                return {"FINISHED"}
            elif values.prev_scene_change == "":                                         # no previous - do nothing
                return {"FINISHED"}

        else:                                                                           # an active strip exists

            if strip.type != "SCENE" and values.prev_scene_change != "":                 # wrong strip type, but a previous scene - go back
                win = bpy.context.window_manager.windows[0]
                win.scene = bpy.data.scenes[values.prev_scene_change]

            elif strip.type == "SCENE":                                                 # correct strip type
                strip_scene = bpy.context.scene.sequence_editor.active_strip.scene.name
                values.prev_scene_change = scene.name

                                                                                        # scene strip in 'Camera' and a camera is selected

                if sequence.sequences_all[strip.name].scene_input == 'CAMERA' and strip.scene_camera != None:
                    for area in bpy.context.screen.areas:
                        if area.type == 'VIEW_3D':
                            win = bpy.context.window_manager.windows[0]
                            win.scene = bpy.data.scenes[strip_scene]
                            bpy.context.scene.camera = bpy.data.objects[camera]         # select camera as view
                            area.spaces.active.region_3d.view_perspective = 'CAMERA'    # use camera view

                else:                                                                   # no scene strip in 'Camera' mode or a camera may not be selected

                    strip_scene = bpy.context.scene.sequence_editor.active_strip.scene.name
                    values.prev_scene_change = scene.name
                    win = bpy.context.window_manager.windows[0]
                    win.scene = bpy.data.scenes[strip_scene]

        return {"FINISHED"}


def menu_toggle_scene(self, context):
    self.layout.separator()
    self.layout.operator("sequencer.change_scene")


def menu_add_camera(self, context):
    self.layout.operator("view3d.add_scene_strip", icon="VIEW_CAMERA")


def menu_link_tdview(self, context):
    layout = self.layout
    col = layout.column(align=(False))
    #col = col.use_property_split = True
    #col = col.alignment = 'RIGHT'
    manager = context.scene.asset_manager
    col.prop(manager, "link_seq_to_3d_view", text="Link Sequencer to 3D Viewport")


def menu_convert_markers(self, context):
    self.layout.separator()
    self.layout.operator("sequencer.convert_cameras")


classes = (
    THREEDPREVIEW_PT_add_scene_strip,
    PropertyGroup,
    SEQUENCE_PT_convert_cameras,
    SEQUENCER_PT_scene_tools,
    SEQUENCER_OT_scene_change,
    )

register, unregister = bpy.utils.register_classes_factory(classes)

addon_keymaps = []


def register():

    bpy.types.SEQUENCER_MT_strip.append(menu_toggle_scene)
    bpy.types.SEQUENCER_MT_context_menu.append(menu_toggle_scene)
    bpy.types.SEQUENCER_HT_header.append(menu_link_tdview)
    bpy.types.SEQUENCER_MT_add.prepend(menu_add_camera)
    bpy.types.SEQUENCER_MT_marker.append(menu_convert_markers)

    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Scene Change', space_type='SEQUENCE_EDITOR')
    kmi = km.keymap_items.new(SEQUENCER_OT_scene_change.bl_idname, 'TAB', 'PRESS', ctrl=False, shift=True)
    addon_keymaps.append((km, kmi))

    for i in classes:
        register_class(i)
    bpy.types.Scene.asset_manager = bpy.props.PointerProperty(type=PropertyGroup)


def unregister():

    bpy.types.SEQUENCER_MT_strip.remove(menu_toggle_scene)
    bpy.types.SEQUENCER_MT_context_menu.remove(menu_toggle_scene)
    bpy.types.SEQUENCER_HT_header.remove(menu_link_tdview)
    bpy.types.SEQUENCER_MT_add.remove(menu_add_camera)
    bpy.types.SEQUENCER_MT_marker.remove(menu_convert_markers)

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    for i in classes:
        unregister_class(i)

if __name__ == "__main__":
    register()

# unregister()
