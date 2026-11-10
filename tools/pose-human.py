"""Anatomical static poses for the MPFB game-engine rig (Blender only).

Use build_poses(rig) during asset generation. The elbow is a hinge, not an
independently aimed/twisted ball joint. Construct the shoulder's entire frame
from the upper-arm direction AND elbow plane, then flex the forearm in that
plane. This avoids residual roll from composing arbitrary pre-rotations with
shortest-arc aiming. Coordinates here are Blender's +Z up, -Y forward.
"""
import math
import bpy
from mathutils import Vector, Matrix, Quaternion

POSE_NAMES = ('relaxed', 'tpose', 'wave', 'stride')


def reset_pose(rig):
    if rig.animation_data:
        rig.animation_data.action = None
    for bone in rig.pose.bones:
        bone.rotation_mode = 'QUATERNION'
        bone.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def _aim(bone, direction):
    bpy.context.view_layer.update()
    rotation = (bone.tail-bone.head).rotation_difference(Vector(direction))
    matrix = rotation.to_matrix().to_4x4() @ bone.matrix
    matrix.translation = bone.head.copy()
    bone.matrix = matrix
    bpy.context.view_layer.update()


def _frame(direction, normal):
    y = Vector(direction).normalized()
    z = Vector(normal)
    z = (z-y*z.dot(y)).normalized()
    x = y.cross(z).normalized()
    return Matrix((x, y, z)).transposed()


def _arm(rig, suffix, upper_direction, fore_direction, clavicle_lift):
    sign = 1 if suffix == 'l' else -1
    clavicle = rig.pose.bones['clavicle_'+suffix]
    # Let the shoulder girdle follow elevation rather than pulling the whole
    # armpit across one fixed humerus pivot.
    direction = clavicle.bone.tail_local-clavicle.bone.head_local
    direction = Quaternion((0, 1, 0), math.radians(-sign*clavicle_lift)) @ direction
    _aim(clavicle, direction)
    upper = rig.pose.bones['upperarm_'+suffix]
    lower = rig.pose.bones['lowerarm_'+suffix]
    rest_u = (upper.bone.tail_local-upper.bone.head_local).normalized()
    rest_f = (lower.bone.tail_local-lower.bone.head_local).normalized()
    target_u, target_f = Vector(upper_direction).normalized(), Vector(fore_direction).normalized()
    normal = target_u.cross(target_f)
    if normal.length < .001:
        # A straight elbow has an underdetermined plane. Retain forward flexion
        # and palms down instead of introducing arbitrary axial rotation.
        normal = Vector((0, 0, -sign))
    rotation = _frame(target_u, normal) @ _frame(rest_u, rest_u.cross(rest_f)).transposed()
    matrix = rotation.to_4x4() @ upper.bone.matrix_local
    matrix.translation = upper.head.copy()
    upper.matrix = matrix
    bpy.context.view_layer.update()
    _aim(lower, target_f)
    _aim(rig.pose.bones['hand_'+suffix], target_f)


def _world_rotate(bone, axis, degrees):
    # Actual parent-pose basis, not just the rest basis, defines local rotation.
    bpy.context.view_layer.update()
    rotation = Quaternion(Vector(axis), math.radians(degrees))
    matrix = rotation.to_matrix().to_4x4() @ bone.matrix
    matrix.translation = bone.head.copy()
    bone.matrix = matrix
    bpy.context.view_layer.update()


def apply_pose(rig, name):
    if name not in POSE_NAMES:
        raise ValueError('Unknown pose: '+name)
    reset_pose(rig)
    if name == 'tpose':
        for suffix, sign in [('l', 1), ('r', -1)]:
            _arm(rig, suffix, (sign, 0, 0), (sign, 0, 0), 12)
    elif name == 'wave':
        _arm(rig, 'l', (.82, -.12, .56), (.04, -.08, 1), 20)
    elif name == 'stride':
        for bone, angle in [('thigh_l', -20), ('thigh_r', 18), ('calf_r', -18),
                            ('upperarm_l', 20), ('upperarm_r', -20)]:
            _world_rotate(rig.pose.bones[bone], (1, 0, 0), angle)
    bpy.context.view_layer.update()


def build_poses(rig):
    """Create four exportable actions; leave the rig in its unposed rest state."""
    for name in POSE_NAMES:
        apply_pose(rig, name)
        for frame in (0, 1):
            for bone in rig.pose.bones:
                bone.keyframe_insert('rotation_quaternion', frame=frame, group=bone.name)
        action = rig.animation_data.action
        action.name = name
        action.use_fake_user = True
        track = rig.animation_data.nla_tracks.new()
        track.name = name
        track.strips.new(name, 0, action)
        track.mute = True
    reset_pose(rig)
    bpy.context.scene.frame_set(0)
    return POSE_NAMES


POSE_CORRECTIVES = {name: 'Pose'+name.title() for name in POSE_NAMES if name != 'relaxed'}


def bake_pose_correctives(rig, meshes):
    """Bake preserve-volume skinning into portable, pre-skin pose morphs.

    glTF clients use linear blend skinning, not Blender's preserve-volume mode.
    For each static pose, invert the blended skin matrix at each vertex to bake
    the DQ-minus-LBS displacement into a normal morph. At its matching pose,
    that morph reproduces DQ exactly. The regular skeleton, editable body
    morphs, weights, and all four actual poses remain intact.

    Clients should set only POSE_CORRECTIVES[current_pose] to 1, after setting
    the appearance morphs. These corrective targets are not appearance sliders.
    """
    report = {}
    for ob in meshes:
        if not ob.data.shape_keys:
            ob.shape_key_add(name='Basis')
        for key in ob.data.shape_keys.key_blocks:
            key.value = 0
        report[ob.name] = {}
    for pose, key_name in POSE_CORRECTIVES.items():
        apply_pose(rig, pose)
        for ob in meshes:
            modifier = next((m for m in ob.modifiers if m.type == 'ARMATURE' and m.object == rig), None)
            if modifier is None:
                continue
            def evaluated(preserve):
                modifier.use_deform_preserve_volume = preserve
                bpy.context.view_layer.update()
                return [v.co.copy() for v in ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
            linear, volume = evaluated(False), evaluated(True)
            modifier.use_deform_preserve_volume = False
            to_mesh = ob.matrix_world.inverted() @ rig.matrix_world
            to_rig = to_mesh.inverted()
            transforms = {
                group.index: to_mesh @ rig.pose.bones[group.name].matrix @ rig.data.bones[group.name].matrix_local.inverted() @ to_rig
                for group in ob.vertex_groups if group.name in rig.pose.bones
            }
            key = ob.data.shape_keys.key_blocks.get(key_name) or ob.shape_key_add(name=key_name)
            maximum = 0
            for vertex, dst, dq, lbs in zip(ob.data.vertices, key.data, volume, linear):
                weights = [(g.weight, transforms[g.group]) for g in vertex.groups if g.group in transforms]
                total = sum(w for w, _ in weights)
                if total < 1e-8:
                    continue
                matrix = Matrix(tuple(tuple(sum(w*m[row][col] for w,m in weights)/total for col in range(3)) for row in range(3)))
                if abs(matrix.determinant()) < 1e-8:
                    raise ValueError(f'Singular skin matrix in {ob.name}, {pose}, vertex {vertex.index}')
                correction = matrix.inverted() @ (dq-lbs)
                dst.co = ob.data.shape_keys.key_blocks[0].data[vertex.index].co + correction
                maximum = max(maximum, correction.length)
            key.value = 0
            report[ob.name][pose] = {'maxPreSkinCorrection': maximum}
    reset_pose(rig)
    bpy.context.view_layer.update()
    return report
