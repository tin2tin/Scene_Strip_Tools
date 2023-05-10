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


# Update to 3.4
# Using Linked scene as intermediate to get preview and render of strips referencing the current scene.

bl_info = {
    "name": "Scene Strip Tools",
    "author": "Tintwotin",
    "version": (1, 0),
    "blender": (3, 4, 0),
    "location": "Sequencer Sidebar Scene Strip Tools, Add Menu and Context Menu",
    "description": "Preview Sequencer Scene Strip edits in the 3D Viewport",
    "warning": "",
    "wiki_url": "",
    "category": "Sequencer"}


import bpy
import mathutils
from mathutils import Matrix
from bpy.utils import register_class, unregister_class
from bpy.props import BoolProperty, EnumProperty
from bpy.types import Panel, Menu
from rna_prop_ui import PropertyPanel
from operator import attrgetter
import os


def act_strip(context):
    try:
        return context.scene.sequence_editor.active_strip
    except AttributeError:
        return False

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

oldStrip = ""


def swich_camera_at_frame_change(*pArgs):
    global oldStrip
    scene = bpy.context.scene
    sequences = scene.sequence_editor.sequences
    sequences = sorted(sequences, key=lambda x: (-x.channel, x.frame_final_start))
    cf = scene.frame_current

    try:
        for seq in sequences:
            if hasattr(seq, 'type') and seq.type == 'SCENE' and seq.scene_camera.name != oldStrip:
                if seq.scene.name[:-4] == scene.name and not seq.mute:
                    if seq.frame_final_start <= cf < seq.frame_final_end:
                        for area in bpy.context.screen.areas:
                            if area.type == 'VIEW_3D':
                                scene.camera = bpy.data.objects[seq.scene_camera.name]
                                area.spaces.active.region_3d.view_perspective = 'CAMERA'
                                oldStrip = seq.scene_camera.name
                                return
                        return
    except AttributeError:
        pass
    return


def attach_as_handler():
    bpy.app.handlers.frame_change_post.append(swich_camera_at_frame_change)

def detach_as_handler():
    bpy.app.handlers.frame_change_post.clear()


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
        return bpy.context.scene.sequence_editor

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=(False))
        #col.use_property_split = False
        col = col.box()
        manager = context.scene.asset_manager

        col.prop(manager, "link_seq_to_3d_view", text="Link Sequencer to 3D Viewport", icon="LINKED")
        col.operator("view3d.add_scene_strip", text="Add Camera as Scene Strip", icon="CAMERA_DATA")
        col.operator("sequencer.convert_cameras", text="Convert Camera Markers to Strips", icon="MARKER")
        col.operator("sequencer.match_frame", text="Find Matching Frame", icon="IMAGE_REFERENCE")
        col.operator("sequencer.scene_change", text="Toggle Scene Strip", icon="VIEW3D")

        # check if bool property is enabled
        if (context.scene.asset_manager.link_seq_to_3d_view == True):
            swich_camera_at_frame_change()
            attach_as_handler()
        else:
            detach_as_handler()


class VIEW_3D_PT_add_scene_strip(bpy.types.Operator):
    """Adds current camera as a scene strip to the Sequencer"""
    bl_idname = "view3d.add_scene_strip"
    bl_label = "Camera"
    bl_options = {'REGISTER', "UNDO"}

    def invoke(self, context, event):
        # Ensure updates in preview on frame change
        ed = bpy.context.scene.sequence_editor
        ed.use_cache_raw = False
        ed.use_cache_preprocessed = False
        ed.use_cache_composite = False
        ed.use_cache_final = False

        if not bpy.context.scene.sequence_editor:
            bpy.context.scene.sequence_editor_create()
        scn = bpy.context.scene
        seq = scn.sequence_editor
        cf = scn.frame_current
        scene_name = bpy.context.scene.name
        bpy.data.scenes[scene_name].render.resolution_percentage = 100
        ns = bpy.data.scenes[scene_name].copy()
        bpy.data.scenes[scene_name].use_fake_user = True

        # Can't change name, as it is used to find the scene later on.         
        #        new_scene_name = os.path.splitext(ns.name)[0]+"_"+bpy.context.scene.camera.name
        #        bpy.data.scenes[ns.name].name = new_scene_name
        #        ns = bpy.data.scenes[ns.name]

        addSceneIn = cf
        addSceneOut = scn.frame_end
        addSceneChannel = 2
        addSceneTlStart = cf
        newScene = seq.sequences.new_scene('Scene', ns, addSceneChannel, addSceneTlStart)
        seq.sequences_all[newScene.name].scene_camera = bpy.data.objects[bpy.context.scene.camera.name]
        seq.sequences_all[newScene.name].frame_offset_start = addSceneIn
        seq.sequences_all[newScene.name].frame_final_end = addSceneOut
        seq.sequences_all[newScene.name].frame_start = 0

        # Get the current scene
        original_scene = bpy.context.scene
        
        # Change to the new scene
        bpy.context.window.scene = ns
        if bpy.context.scene.sequence_editor:
            bpy.ops.sequencer.select_all(action='SELECT')
            bpy.ops.sequencer.delete()

        # Change back to the original scene
        bpy.context.window.scene = original_scene

        return {"FINISHED"}


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


class values():
    prev_scene_change = ""


class SEQUENCER_OT_scene_change(bpy.types.Operator):
    """Change scene to active strip scene"""
    bl_idname = "sequencer.scene_change"
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
                    print(camera)

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
                strip_scene = bpy.context.scene.name
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


class SEQUENCER_OT_match_frame(bpy.types.Operator):
    """Jump to a matching frame in a different scene."""

    bl_idname = "sequencer.match_frame"
    bl_label = "Match Frame"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        current_scene = bpy.context.scene
        current_frame = current_scene.frame_current
        try:
            active = current_scene.sequence_editor.active_strip
        except AttributeError:
            return {"CANCELLED"}
        if not active:
            return {"CANCELLED"}
        frame_start = active.frame_start + active.frame_offset_start
        frame_end = (
            int(active.frame_start + active.frame_offset_start + active.frame_final_duration)
        )

        if current_frame >= frame_start and current_frame <= frame_end:
            find_frame = current_frame - active.frame_start
        else:
            find_frame = 0
        for sce in bpy.data.scenes:
            seq = sce.sequence_editor

            if seq and (active.type == "MOVIE" or active.type == "SOUND"):
                for strip in seq.sequences_all:
                    if strip.type == active.type == "MOVIE":
                        strip_file_path = strip.filepath
                        active_file_path = active.filepath
                    elif strip.type == active.type == "SOUND":
                        strip_file_path = strip.sound.filepath
                        active_file_path = active.sound.filepath
                    if (
                        find_frame
                        and current_scene.name != sce.name
                        and active.type == strip.type
                        and active_file_path == strip_file_path
                    ):
                        frame_current = find_frame + strip.frame_start
                        frame_start = strip.frame_start + strip.frame_offset_start
                        frame_end = (
                            strip.frame_start
                            + strip.frame_offset_start
                            + strip.frame_final_duration
                        )
                        print("frame_current " + str(frame_current))
                        print("frame_start " + str(frame_start))
                        print("frame_end " + str(frame_end))
                        if frame_current >= frame_start and frame_current <= frame_end:
                            win = bpy.context.window_manager.windows[0]
                            win.scene = bpy.data.scenes[sce.name]
                            bpy.context.scene.frame_current = frame_current
                            bpy.ops.sequencer.select_all(action="DESELECT")
                            strip.select = True
                            bpy.context.scene.sequence_editor.active_strip = strip
                            bpy.ops.sequencer.view_all()
                            break
                            break
            elif active.type == "SCENE":
                scene_name = active.scene.name
                if scene_name == sce.name:
                    camera_name = ""
                    if active.scene_input == "CAMERA":
                        if active.scene_camera:
                            camera_name = active.scene_camera.name
                    if find_frame and current_scene.name != sce.name:
                        frame_current = find_frame
                        print("frame_current " + str(frame_current))
                        win = bpy.context.window_manager.windows[0]
                        win.scene = bpy.data.scenes[sce.name]
                        bpy.context.scene.frame_current = int(frame_current)

                        if camera_name:
                            for area in bpy.context.screen.areas:
                                if area.type == "VIEW_3D":
                                    bpy.context.scene.camera = bpy.data.objects[
                                        camera_name
                                    ]  # Select camera as view
                                    area.spaces.active.region_3d.view_perspective = (
                                        "CAMERA"  # Use camera view
                                    )
                                    break
                        break
                        break
        return {"FINISHED"}


def menu_toggle_scene(self, context):
    self.layout.separator()
    self.layout.operator("sequencer.scene_change")
    self.layout.operator("sequencer.match_frame")


def menu_add_camera(self, context):
    self.layout.operator("view3d.add_scene_strip", icon="VIEW_CAMERA")


def menu_link_tdview(self, context):
    layout = self.layout
    col = layout.column(align=(False))
    #col = col.use_property_split = True
    #col = col.alignment = 'RIGHT'
    manager = context.scene.asset_manager
    col.prop(manager, "link_seq_to_3d_view", text="", icon="LINKED", toggle=True)


def menu_convert_markers(self, context):
    self.layout.separator()
    self.layout.operator("sequencer.convert_cameras")


classes = (
    VIEW_3D_PT_add_scene_strip,
    PropertyGroup,
    SEQUENCE_PT_convert_cameras,
    SEQUENCER_PT_scene_tools,
    SEQUENCER_OT_scene_change,
    SEQUENCER_OT_match_frame,
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
