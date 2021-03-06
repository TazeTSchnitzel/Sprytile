import bpy
import bgl
import blf
import bmesh
from bmesh.types import BMVert, BMEdge, BMFace
from mathutils import Matrix, Vector
from . import sprytile_modal
from . import addon_updater_ops


def get_grid_matrix(sprytile_grid):
    """Returns the transform matrix of a sprytile grid"""
    offset_mtx = Matrix.Translation((sprytile_grid.offset[0], sprytile_grid.offset[1], 0))
    rotate_mtx = Matrix.Rotation(sprytile_grid.rotate, 4, 'Z')
    return offset_mtx * rotate_mtx


def get_grid_texture(obj, sprytile_grid):
    mat_idx = obj.material_slots.find(sprytile_grid.mat_id)
    if mat_idx == -1:
        return None
    material = obj.material_slots[mat_idx].material
    if material is None:
        return None
    target_img = None
    for texture_slot in material.texture_slots:
        if texture_slot is None:
            continue
        if texture_slot.texture is None:
            continue
        if texture_slot.texture.type == 'NONE':
            continue
        if texture_slot.texture.image is None:
            continue
        if texture_slot.texture.type == 'IMAGE':
            # Cannot use the texture slot image reference directly
            # Have to get it through bpy.data.images to be able to use with BGL
            target_img = bpy.data.images.get(texture_slot.texture.image.name)
            break
    return target_img


def get_selected_grid(context):
    obj = context.object
    scene = context.scene

    mat_list = scene.sprytile_mats
    grid_id = obj.sprytile_gridid

    for mat_data in mat_list:
        for grid in mat_data.grids:
            if grid.id == grid_id:
                return grid
    return None


def get_grid(context, grid_id):
    mat_list = context.scene.sprytile_mats
    for mat_data in mat_list:
        for grid in mat_data.grids:
            if grid.id == grid_id:
                return grid
    return None


def get_highest_grid_id(context):
    highest_id = -1
    mat_list = context.scene.sprytile_mats
    for mat_data in mat_list:
        for grid in mat_data.grids:
            highest_id = max(grid.id, highest_id)
    return highest_id


def get_mat_data(context, mat_id):
    mat_list = context.scene.sprytile_mats
    for mat_data in mat_list:
        if mat_data.mat_id == mat_id:
            return mat_data
    return None


def label_wrap(col, text, area="VIEW_3D", region_type="TOOL_PROPS", tab_str="    ", scale_y=0.55):
    a_id = -1
    r_id = -1
    new_line = "\n"
    tab = "\t"
    tabbing = False
    n_line = False
    col.scale_y = scale_y
    areas = bpy.context.screen.areas
    for i, a in enumerate(areas):
        if a.type == area:
            a_id = i
        reg = a.regions
        for ir, r in enumerate(reg):
            if r.type == region_type:
                r_id = ir
    if a_id < 0 or r_id < 0:
        return

    p_width = areas[a_id].regions[r_id].width
    char_width = 7  # approximate width of each character
    line_length = int(p_width / char_width)
    last_space = line_length  # current position of last space character in text
    while last_space > 0:
        split_point = line_length  # where to split the text
        if split_point > len(text):
            split_point = len(text) - 1

        cr = text.find(new_line, 0, len(text))

        if (cr > 0) and (cr <= split_point):
            n_line = True
            last_space = cr  # Position of new line symbol, if found
        else:
            tabp = text.find("\t", 0, split_point)
            if tabp >= 0:
                text = text.replace(tab, "", 1)
                tabbing = True
                n_line = False
            last_space = text.rfind(" ", 0, split_point)  # Position of last space character in text

        if (last_space == -1) or len(text) <= line_length:  # No more spaces found, or its the last line of text
            last_space = len(text)
        line = text[0:last_space]
        if tabbing:
            line = tab_str + line
        col.label(line)
        if n_line:
            tabbing = False
        text = text[last_space + 1:len(text)]

class SprytileGridAdd(bpy.types.Operator):
    bl_idname = "sprytile.grid_add"
    bl_label = "Add New Grid"

    def execute(self, context):
        return self.invoke(context, None)

    def invoke(self, context, event):
        self.add_new_grid(context)
        return {'FINISHED'}

    @staticmethod
    def add_new_grid(context):
        mat_list = context.scene.sprytile_mats
        target_mat = None

        if len(mat_list) > 0:
            target_mat = mat_list[0]

        grid_id = context.object.sprytile_gridid

        target_grid = get_grid(context, grid_id)
        if target_grid is not None:
            for mat in mat_list:
                if mat.mat_id == target_grid.mat_id:
                    target_mat = mat
                    break

        if target_mat is None:
            return

        grid_idx = -1
        for idx, grid in enumerate(mat.grids):
            if grid.id == grid_id:
                grid_idx = idx
                break

        new_idx = len(target_mat.grids)

        new_grid = target_mat.grids.add()
        new_grid.mat_id = target_mat.mat_id
        new_grid.id = get_highest_grid_id(context) + 1

        if grid_idx > -1:
            new_grid.grid = target_mat.grids[grid_idx].grid
            target_mat.grids.move(new_idx, grid_idx + 1)

        bpy.ops.sprytile.build_grid_list()


class SprytileGridRemove(bpy.types.Operator):
    bl_idname = "sprytile.grid_remove"
    bl_label = "Remove Grid"

    def execute(self, context):
        return self.invoke(context, None)

    def invoke(self, context, event):
        self.delete_grid(context)
        return {'FINISHED'}

    @staticmethod
    def delete_grid(context):
        mat_list = context.scene.sprytile_mats
        target_mat = None

        if len(mat_list) > 0:
            target_mat = mat_list[0]

        grid_id = context.object.sprytile_gridid

        target_grid = get_grid(context, grid_id)
        if target_grid is not None:
            for mat in mat_list:
                if mat.mat_id == target_grid.mat_id:
                    target_mat = mat
                    break

        if target_mat is None or len(target_mat.grids) <= 1:
            return

        grid_idx = -1
        for idx, grid in enumerate(target_mat.grids):
            if grid.id == grid_id:
                grid_idx = idx
                break

        target_mat.grids.remove(grid_idx)
        bpy.ops.sprytile.build_grid_list()


class SprytileGridCycle(bpy.types.Operator):
    bl_idname = "sprytile.grid_cycle"
    bl_label = "Cycle grid settings"

    direction = bpy.props.IntProperty(default=1)

    def execute(self, context):
        return self.invoke(context, None)

    def invoke(self, context, event):
        self.cycle_grid(context)
        return {'FINISHED'}

    def cycle_grid(self, context):
        obj = context.object
        curr_grid = get_grid(context, obj.sprytile_gridid)
        if curr_grid is None:
            return

        curr_mat = get_mat_data(context, curr_grid.mat_id)
        if curr_mat is None:
            return

        idx = -1
        for grid in curr_mat.grids:
            idx += 1
            if grid.id == curr_grid.id:
                break

        idx += self.direction
        if idx < 0:
            idx = len(curr_mat.grids)-1
        if idx >= len(curr_mat.grids):
            idx = 0

        obj.sprytile_gridid = curr_mat.grids[idx].id
        bpy.ops.sprytile.build_grid_list()


class SprytileStartTool(bpy.types.Operator):
    bl_idname = "sprytile.start_tool"
    bl_label = "Start Sprytile Paint"

    mode = bpy.props.IntProperty(default=3)

    def execute(self, context):
        return self.invoke(context, None)

    def invoke(self, context, event):
        if self.mode is 0:
            context.scene.sprytile_data.paint_mode = 'SET_NORMAL'
        if self.mode is 1:
            context.scene.sprytile_data.paint_mode = 'PAINT'
        if self.mode is 2:
            context.scene.sprytile_data.paint_mode = 'MAKE_FACE'
        bpy.ops.sprytile.modal_tool('INVOKE_REGION_WIN')
        return {'FINISHED'}


class SprytileGridMove(bpy.types.Operator):
    bl_idname = "sprytile.grid_move"
    bl_label = "Move Grid"

    direction = bpy.props.IntProperty(default=1)

    def execute(self, context):
        return self.invoke(context, None)

    def invoke(self, context, event):
        self.move_grid(context)
        return {'FINISHED'}

    def move_grid(self, context):
        obj = context.object
        curr_grid = get_grid(context, obj.sprytile_gridid)
        if curr_grid is None:
            return

        curr_mat = get_mat_data(context, curr_grid.mat_id)
        if curr_mat is None:
            return

        idx = -1
        for grid in curr_mat.grids:
            idx += 1
            if grid.id == curr_grid.id:
                break

        old_idx = idx
        idx = old_idx + self.direction
        if idx < 0:
            idx = len(curr_mat.grids)-1
        if idx >= len(curr_mat.grids):
            idx = 0

        curr_mat.grids.move(old_idx, idx)
        obj.sprytile_gridid = curr_mat.grids[idx].id
        bpy.ops.sprytile.build_grid_list()


class SprytileNewMaterial(bpy.types.Operator):
    bl_idname = "sprytile.add_new_material"
    bl_label = "New Shadeless Material"

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def invoke(self, context, event):
        obj = context.object

        mat = bpy.data.materials.new(name="Material")

        set_idx = len(obj.data.materials)
        obj.data.materials.append(mat)
        obj.active_material_index = set_idx

        bpy.ops.sprytile.material_setup()
        bpy.ops.sprytile.validate_grids()
        return {'FINISHED'}


class SprytileSetupMaterial(bpy.types.Operator):
    bl_idname = "sprytile.material_setup"
    bl_label = "Set Material to Shadeless"

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def execute(self, context):
        return self.invoke(context, None)

    def invoke(self, context, event):
        mat = bpy.data.materials[context.object.active_material_index]
        mat.use_shadeless = True
        mat.use_transparency = True
        mat.transparency_method = 'Z_TRANSPARENCY'
        mat.alpha = 0.0
        return {'FINISHED'}


class SprytileSetupTexture(bpy.types.Operator):
    bl_idname = "sprytile.texture_setup"
    bl_label = "Setup Pixel Texture"

    def execute(self, context):
        return self.invoke(context, None)

    def invoke(self, context, event):
        self.setup_tex(context)
        return {'FINISHED'}

    @staticmethod
    def setup_tex(context):
        """"""
        material = bpy.data.materials[context.object.active_material_index]
        target_texture = None
        target_img = None
        target_slot = None
        for texture_slot in material.texture_slots:
            if texture_slot is None:
                continue
            if texture_slot.texture is None:
                continue
            if texture_slot.texture.type == 'NONE':
                continue
            if texture_slot.texture.type == 'IMAGE':
                # Cannot use the texture slot image reference directly
                # Have to get it through bpy.data.images to be able to use with BGL
                target_texture = bpy.data.textures.get(texture_slot.texture.name)
                target_img = bpy.data.images.get(texture_slot.texture.image.name)
                target_slot = texture_slot
                break
        if target_texture is None or target_img is None:
            return

        target_texture.use_preview_alpha = True
        target_texture.use_alpha = True
        target_texture.use_interpolation = False
        target_texture.use_mipmap = False
        target_texture.filter_type = 'BOX'
        target_texture.filter_size = 0.10
        target_img.use_alpha = True

        target_slot.use_map_color_diffuse = True
        target_slot.use_map_alpha = True
        target_slot.alpha_factor = 1.0
        target_slot.diffuse_color_factor = 1.0


class SprytileValidateGridList(bpy.types.Operator):
    bl_idname = "sprytile.validate_grids"
    bl_label = "Validate Material Grids"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        return self.invoke(context, None)

    def invoke(self, context, event):
        self.validate_grids(context)
        return {'FINISHED'}

    @staticmethod
    def validate_grids(context):
        mat_list = bpy.data.materials
        mat_data_list = context.scene.sprytile_mats

        # Validate the material IDs in scene.sprytile_mats
        for check_mat_data in mat_data_list:
            mat_idx = mat_list.find(check_mat_data.mat_id)
            if mat_idx > -1:
                continue

            # This mat data id not found in materials
            # Loop through materials looking for one
            # that doesn't appear in sprytile_mats list
            for check_mat in mat_list:
                mat_unused = True
                for mat_data in mat_data_list:
                    if mat_data.mat_id == check_mat.name:
                        mat_unused = False
                        break

                if mat_unused:
                    target_mat_id = check_mat_data.mat_id
                    check_mat_data.mat_id = check_mat.name
                    for grid in check_mat_data.grids:
                        grid.mat_id = check_mat.name
                    for list_display in context.scene.sprytile_list.display:
                        if list_display.mat_id == target_mat_id:
                            list_display.mat_id = check_mat.name
                    break

        remove_idx = []

        # Filter out mat data with invalid IDs or users
        for idx, mat in enumerate(mat_data_list.values()):
            mat_idx = mat_list.find(mat.mat_id)
            if mat_idx < 0:
                remove_idx.append(idx)
                continue
            if mat_list[mat_idx].users == 0:
                remove_idx.append(idx)
            for grid in mat.grids:
                grid.mat_id = mat.mat_id
        remove_idx.reverse()
        for idx in remove_idx:
            mat_data_list.remove(idx)

        # Loop through available materials, checking if mat_data_list has
        # at least one entry for each material
        for mat in mat_list:
            if mat.users == 0:
                continue
            is_mat_valid = False
            for mat_data in mat_data_list:
                if mat_data.mat_id == mat.name:
                    is_mat_valid = True
                    break
            if is_mat_valid is False:
                mat_data_entry = mat_data_list.add()
                mat_data_entry.mat_id = mat.name
                mat_grid = mat_data_entry.grids.add()
                mat_grid.mat_id = mat.name
                mat_grid.id = get_highest_grid_id(context) + 1

        context.object.sprytile_gridid = get_highest_grid_id(context)
        bpy.ops.sprytile.build_grid_list()


class SprytileBuildGridList(bpy.types.Operator):
    bl_idname = "sprytile.build_grid_list"
    bl_label = "Sprytile Build Grid List"

    def execute(self, context):
        return self.invoke(context, None)

    def invoke(self, context, event):
        self.build_list(context)
        return {'FINISHED'}

    @staticmethod
    def build_list(context):
        """Build the scene.sprytile_list.display from scene.sprytile_mats"""
        display_list = context.scene.sprytile_list.display
        mat_list = context.scene.sprytile_mats

        display_list.clear()
        for mat_data in mat_list:
            mat_display = display_list.add()
            mat_display.mat_id = mat_data.mat_id
            if mat_data.is_expanded is False:
                continue
            for mat_grid in mat_data.grids:
                idx = len(display_list)
                grid_display = display_list.add()
                grid_display.grid_id = mat_grid.id
                if context.object.sprytile_gridid == grid_display.grid_id:
                    context.scene.sprytile_list.idx = idx


class SprytileRotateLeft(bpy.types.Operator):
    bl_idname = "sprytile.rotate_left"
    bl_label = "Rotate Sprytile Left"

    def execute(self, context):
        return self.invoke(context, None)

    def invoke(self, context, event):
        curr_rotation = context.scene.sprytile_data.mesh_rotate
        curr_rotation += 1.5708
        if curr_rotation > 6.28319:
            curr_rotation = 0
        context.scene.sprytile_data.mesh_rotate = curr_rotation
        return {'FINISHED'}


class SprytileRotateRight(bpy.types.Operator):
    bl_idname = "sprytile.rotate_right"
    bl_label = "Rotate Sprytile Right"

    def execute(self, context):
        return self.invoke(context, None)

    def invoke(self, context, event):
        curr_rotation = context.scene.sprytile_data.mesh_rotate
        curr_rotation -= 1.5708
        if curr_rotation < -6.28319:
            curr_rotation = 0
        context.scene.sprytile_data.mesh_rotate = curr_rotation
        return {'FINISHED'}


class SprytileReloadImages(bpy.types.Operator):
    bl_idname = "sprytile.reload_imgs"
    bl_label = "Reload All Images"

    def invoke(self, context, event):
        for img in bpy.data.images:
            if img is None:
                continue
            img.reload()
        return {'FINISHED'}


class SprytileReloadImagesAuto(bpy.types.Operator):
    bl_idname = "sprytile.reload_auto"
    bl_label = "Reload All Images (Auto)"

    _timer = None

    def modal(self, context, event):
        if event.type == 'TIMER':
            if context.scene.sprytile_data.auto_reload is False:
                self.cancel(context)
                return {'CANCELLED'}
            bpy.ops.sprytile.reload_imgs('INVOKE_DEFAULT')
        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(2, context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)


class SprytileUpdateCheck(bpy.types.Operator):
    bl_idname = "sprytile.update_check"
    bl_label = "Check for Update"

    def invoke(self, context, event):
        print("Check itch.io API")
        import sys
        print(sys.modules['sprytile'].bl_info.get('version', (-1, -1, -1)))
        import urllib.request
        import json
        url = "https://itch.io/api/1/x/wharf/latest?game_id=98966&channel_name=addon"
        response = urllib.request.urlopen(url)
        data = response.read()
        encoding = response.info().get_content_charset('utf-8')
        json_data = json.loads(data.decode(encoding))
        print(json_data)
        return {'FINISHED'}


class SprytileMakeDoubleSided(bpy.types.Operator):
    bl_idname = "sprytile.make_double_sided"
    bl_label = "Make Double Sided (Sprytile)"
    bl_description = "Duplicate selected faces and flip normals"

    def execute(self, context):
        self.invoke(context, None)

    def invoke(self, context, event):
        print("Invoked make double sided")
        if context.object is None or (context.object.type != 'MESH' or context.object.mode != 'EDIT'):
            print("Nope")
            return {'FINISHED'}
        mesh = bmesh.from_edit_mesh(context.object.data)
        double_face = []
        for face in mesh.faces:
            if not face.select:
                continue
            double_face.append(face)
        for face in double_face:
            face.copy(True, True)
            face.normal_flip()
            face.normal_update()

        mesh.faces.index_update()
        mesh.faces.ensure_lookup_table()
        bmesh.update_edit_mesh(context.object.data, True, True)
        return {'FINISHED'}


class SprytileGridTranslate(bpy.types.Operator):
    bl_idname = "sprytile.translate_grid"
    bl_label = "Pixel Translate (Sprytile)"

    @staticmethod
    def draw_callback(self, context):
        if self.exec_counter != -1 or self.ref_pos is None:
            return None

        check_pos = self.get_ref_pos(context)
        measure_vec = check_pos - self.ref_pos
        pixel_unit = 1 / context.scene.sprytile_data.world_pixels
        for i in range(3):
            measure_vec[i] = int(round(measure_vec[i] / pixel_unit))

        screen_y = context.region.height - 45
        screen_x = 20
        padding = 5

        font_id = 0
        font_size = 16
        blf.size(font_id, font_size, 72)

        bgl.glColor4f(1, 1, 1, 1)

        readout_axis = ['X', 'Y', 'Z']
        for i in range(3):
            blf.position(font_id, screen_x, screen_y, 0)
            blf.draw(font_id, "%s : %d" % (readout_axis[i], measure_vec[i]))
            screen_y -= font_size + padding

    def modal(self, context, event):
        # User cancelled transform
        if event.type == 'ESC':
            return self.exit_modal(context)
        if event.type == 'RIGHTMOUSE' and event.value == 'RELEASE':
            return self.exit_modal(context)
        # On the timer events, count down the frames and execute the
        # translate operator when reach 0
        if event.type == 'TIMER':
            if self.exec_counter > 0:
                self.exec_counter -= 1

            if self.exec_counter == 0:
                self.exec_counter -= 1
                up_vec, right_vec, norm_vec = sprytile_modal.get_current_grid_vectors(context.scene)
                norm_vec = sprytile_modal.snap_vector_to_axis(norm_vec)
                axis_constraint = [
                    abs(norm_vec.x) == 0,
                    abs(norm_vec.y) == 0,
                    abs(norm_vec.z) == 0
                ]
                tool_value = bpy.ops.transform.translate(
                    'INVOKE_DEFAULT',
                    constraint_axis=axis_constraint,
                    snap=self.restore_settings is not None
                )
                # Translate tool moved nothing, exit
                if 'CANCELLED' in tool_value:
                    return self.exit_modal(context)

        # When the active operator changes, we know that translate has been completed
        if context.active_operator != self.watch_operator:
            return self.exit_modal(context)

        return {'PASS_THROUGH'}

    def get_ref_pos(self, context):
        if context.object.mode != 'EDIT':
            return None
        if self.bmesh is None:
            self.bmesh = bmesh.from_edit_mesh(context.object.data)
        if len(self.bmesh.select_history) <= 0:
            for vert in self.bmesh.verts:
                if vert.select:
                    return vert.co.copy()
            return None

        target = self.bmesh.select_history[0]
        if isinstance(target, BMFace):
            return target.verts[0].co.copy()
        if isinstance(target, BMEdge):
            return target.verts[0].co.copy()
        if isinstance(target, BMVert):
            return target.co.copy()
        return None

    def execute(self, context):
        return self.invoke(context, None)

    def invoke(self, context, event):
        # When this tool is invoked, change the grid settings so that snapping
        # is on pixel unit steps. Save settings to restore later
        self.restore_settings = None
        space_data = context.space_data
        if space_data.type == 'VIEW_3D':
            self.restore_settings = {
                "grid_scale": space_data.grid_scale,
                "grid_sub": space_data.grid_subdivisions,
                "show_floor": space_data.show_floor,
                "pivot": context.space_data.pivot_point,
                "orient": context.space_data.transform_orientation,
                "use_snap": context.scene.tool_settings.use_snap,
                "snap_element": context.scene.tool_settings.snap_element
            }
            pixel_unit = 1 / context.scene.sprytile_data.world_pixels
            space_data.grid_scale = pixel_unit
            space_data.grid_subdivisions = 1
            space_data.show_floor = False
            space_data.pivot_point = 'CURSOR'
            space_data.transform_orientation = 'GLOBAL'
            context.scene.tool_settings.use_snap = True
            context.scene.tool_settings.snap_element = 'INCREMENT'
        # Remember what the current active operator is, when it changes
        # we know that the translate operator is complete
        self.watch_operator = context.active_operator

        # Countdown the frames passed through the timer. For some reason
        # the translate tool will not use the new grid scale if we switch
        # over immediately to translate.
        self.exec_counter = 5

        if context.object.mode == 'OBJECT':
            view_axis = sprytile_modal.SprytileModalTool.find_view_axis(context)
            if view_axis is not None:
                context.scene.sprytile_data.normal_mode = view_axis

        # Save the bmesh, and reference position
        self.bmesh = None
        self.ref_pos = self.get_ref_pos(context)

        args = self, context
        self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback, args, 'WINDOW', 'POST_PIXEL')

        win_mgr = context.window_manager
        self.timer = win_mgr.event_timer_add(0.1, context.window)
        win_mgr.modal_handler_add(self)
        # Now go up to modal function to read the rest
        return {'RUNNING_MODAL'}

    def exit_modal(self, context):
        pixel_unit = 1 / context.scene.sprytile_data.world_pixels
        # Restore grid settings if changed
        if self.restore_settings is not None:
            context.space_data.grid_scale = self.restore_settings['grid_scale']
            context.space_data.grid_subdivisions = self.restore_settings['grid_sub']
            context.space_data.show_floor = self.restore_settings['show_floor']
            context.space_data.pivot_point = self.restore_settings['pivot']
            context.space_data.transform_orientation = self.restore_settings['orient']
            context.scene.tool_settings.use_snap = self.restore_settings['use_snap']
            context.scene.tool_settings.snap_element = self.restore_settings['snap_element']
        # Didn't snap to grid, force to grid by calculating what the snapped translate would be
        else:
            op = context.active_operator
            if op is not None and op.bl_idname == 'TRANSFORM_OT_translate':
                # Take the translated value and snap it to pixel units
                translation = op.properties.value.copy()
                for i in range(3):
                    translation[i] = int(round(translation[i] / pixel_unit))
                    translation[i] *= pixel_unit
                # Move selection to where snapped position would be
                offset = translation - op.properties.value
                bpy.ops.transform.translate(value=offset)

        # Loop through the selected of the bmesh
        if context.object.mode == 'EDIT' and context.scene.sprytile_data.snap_translate:
            for sel in self.bmesh.select_history:
                vert_list = []
                if isinstance(sel, BMFace) or isinstance(sel, BMEdge):
                    for vert in sel.verts:
                        vert_list.append(vert)
                if isinstance(sel, BMVert):
                    vert_list.append(sel)
                cursor_pos = context.scene.cursor_location
                for vert in vert_list:
                    vert_offset = vert.co - cursor_pos
                    vert_int = Vector((
                                int(round(vert_offset.x / pixel_unit)),
                                int(round(vert_offset.y / pixel_unit)),
                                int(round(vert_offset.z / pixel_unit))
                                ))
                    new_vert_pos = cursor_pos + (vert_int * pixel_unit)
                    vert.co = new_vert_pos

        self.bmesh = None
        bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle, 'WINDOW')
        context.window_manager.event_timer_remove(self.timer)
        return {'FINISHED'}


class SprytileResetData(bpy.types.Operator):
    bl_idname = "sprytile.reset_sprytile"
    bl_label = "Reset Sprytile"
    bl_description = "In case sprytile breaks…"

    def invoke(self, context, event):
        context.scene.sprytile_data.auto_reload = False
        context.scene.sprytile_data.is_running = False
        return {'FINISHED'}


class SprytileObjectDropDown(bpy.types.Menu):
    bl_idname = "SPRYTILE_object_drop"
    bl_label = "Sprytile Utilites"

    def draw(self, context):
        layout = self.layout
        layout.operator("sprytile.reset_sprytile")
        layout.separator()


class SprytileObjectPanel(bpy.types.Panel):
    bl_label = "Sprytile Tools"
    bl_idname = "sprytile.panel_object"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Sprytile"

    @classmethod
    def poll(cls, context):
        if context.object and context.object.type == 'MESH':
            return context.object.mode == 'OBJECT'
        return True

    def draw(self, context):
        layout = self.layout
        layout.menu("SPRYTILE_object_drop")

        box = layout.box()
        box.label("Material Setup")
        box.operator("sprytile.material_setup")
        box.operator("sprytile.texture_setup")
        box.operator("sprytile.add_new_material")

        layout.separator()
        help_text = "Enter edit mode to use Sprytile Paint Tools"
        if context.object is None:
            help_text = "Select a mesh object to use Sprytile"
        elif context.object.type != 'MESH':
            help_text = "Select a mesh object to use Sprytile"
        label_wrap(layout.column(), help_text)

        layout.separator()
        box = layout.box()
        box.label("Pixel Translate Options")
        box.prop(context.scene.sprytile_data, "snap_translate", toggle=True)

        layout.separator()
        box = layout.box()
        box.label("Image Utilities")
        split = box.split(percentage=0.3, align=True)
        split.prop(context.scene.sprytile_data, "auto_reload", toggle=True)
        split.operator("sprytile.reload_imgs")


class SprytileWorkDropDown(bpy.types.Menu):
    bl_idname = "SPRYTILE_work_drop"
    bl_label = "Sprytile Utilites"

    def draw(self, context):
        layout = self.layout
        layout.operator("sprytile.reset_sprytile")
        layout.separator()
        layout.operator("sprytile.make_double_sided")


class SprytileWorkflowPanel(bpy.types.Panel):
    bl_label = "Workflow"
    bl_idname = "sprytile.panel_workflow"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Sprytile"

    @classmethod
    def poll(cls, context):
        if context.object and context.object.type == 'MESH':
            return context.object.mode == 'EDIT'

    def draw(self, context):
        addon_updater_ops.check_for_update_background(context)

        layout = self.layout
        data = context.scene.sprytile_data

        row = layout.row(align=False)
        row.label("", icon="VIEW3D_VEC")

        dropdown_icon = "TRIA_DOWN" if data.axis_plane_settings else "TRIA_RIGHT"

        sub_row = row.row(align=True)
        sub_row.prop(data, "axis_plane_settings", icon=dropdown_icon, emboss=False, text="")
        sub_row.prop(data, "axis_plane_display", expand=True)

        if data.axis_plane_settings:
            layout.prop(data, "axis_plane_color")
            layout.prop(data, "axis_plane_size")

        row = layout.row(align=False)
        row.label("", icon="SNAP_ON")
        row.prop(data, "cursor_snap", expand=True)

        row = layout.row(align=False)
        row.label("", icon="CURSOR")
        row.prop(data, "cursor_flow", toggle=True)

        layout.prop(data, "snap_translate", toggle=True)
        layout.prop(data, "world_pixels")
        layout.menu("SPRYTILE_work_drop")

        split = layout.split(percentage=0.3, align=True)
        split.prop(data, "auto_reload", toggle=True)
        split.operator("sprytile.reload_imgs")

        addon_updater_ops.update_notice_box_ui(self, context)


def register():
    bpy.utils.register_module(__name__)


def unregister():
    bpy.utils.unregister_module(__name__)


if __name__ == '__main__':
    register()
