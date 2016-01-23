from __future__ import print_function, division
import pymel.core as pm
import re
import math
from pymel.core.runtime import nClothCreate, nClothMakeCollide
from contextlib import contextmanager
from random import choice


@contextmanager
def selection(nodes):
    '''
    Selection context manager...sets selection then restores old selection on
    close
    '''

    old_selection = pm.selected()
    try:
        pm.select(nodes, replace=True)
        yield
    finally:
        pm.select(old_selection, replace=True)


@contextmanager
def undo_chunk(auto_undo=False, exc_callback=None):
    '''
    Undo chunk context manager...
    '''

    try:
        pm.undoInfo(openChunk=True)
        yield
    except Exception as e:
        pm.undoInfo(closeChunk=True)
        if auto_undo:
            pm.undo()
        if exc_callback:
            exc_callback(e)
        raise
    else:
        pm.undoInfo(closeChunk=True)


def replace_in_hierarchy(root, regex, substitute):

    hierarchy = pm.ls(root, dag=True)
    for node in hierarchy:
        old_name = str(node)
        new_name = re.sub(regex, substitute, old_name)
        if old_name != new_name:
            node.rename(new_name)


def set_uvs(mesh, uvs, uvSet=None):
    '''
    Set all the uv values of a mesh at once.

    :param mesh: pymel.Mesh node
    :param uvs: List of tuples representing uv values [(u, v)...]
    :param uvSet: UV set to use (default: "map1")
    '''

    uvSet = uvSet or 'map1'
    mesh.setUVs(*zip(*uvs), uvSet=uvSet)


def get_uvs(mesh):
    '''
    Get a list of uv values for the specified pymel.Mesh
    [(u,v)...]
    '''

    return zip(*mesh.getUVs())


def get_uvs_in_range(uvs, u_min, v_min, u_max, v_max):
    '''
    Get the indices of uvs that fall within the specified uv range.

    :param uvs: List of tuples representing uv values [(u, v)...]
    :param u_min: Minimum u value
    :param v_min: Minimum v value
    :param u_max: Maximum u value
    :param v_max: Maximum v value
    '''

    uvids = []
    for i, (u, v) in enumerate(uvs):
        if u_min < u < u_max and v_min < v < v_max:
            uvids.append(i)
    return uvids


def get_row_col(index, max_index, num_columns):
    '''
    Get the row and coloumn for the specified index.

    :param index: Index of item
    :param max_index: Maximum number of items in loop
    :param num_colums: Number of columns
    '''

    if max_index:
        if index >= max_index:
            index -= max_index

    row = index/(num_columns)
    col = index%(num_columns)
    return math.floor(row), math.floor(col)


def pack_uvs(uvs, uvids, i, rows, columns):
    '''
    Pack the specified uvs into a specific uv space based on index in a row,
    column layout.

    :param uvs: List of tuples representing uv values [(u, v)...]
    :param uvids: List of uvids to shift [0, 2, 10...]
    :param i: Layout index
    :param rows: Number of rows in layout
    :param columns: Number of columns in layout
    '''
    r, c = get_row_col(i, None, columns)
    sx = 1 / columns
    sy = 1 / rows

    for uvid in uvids:
        u, v = uvs[uvid]
        u = u * sx + c * sx
        v = v * sy + (1 - sy - r * sy)
        uvs[uvid] = (u, v)


def index_to_udim(i, max_i, columns=10):
    '''
    Convert index to udim column and row
    '''

    r, c = get_row_col(i, max_i, columns)
    return c, r


def shift_uvs(uvs, uvids, u_shift, v_shift):
    '''
    Shift the uvs matched uvids in place, by a specific u and v amount.

    :param uvs: List of tuples representing uv values [(u, v)...]
    :param uvids: List of uvids to shift [0, 2, 10...]
    :param u_shift: Amount in u to shift
    :param v_shift: Amount in v to shift
    '''

    for uvid in uvids:
        u, v = uvs[uvid]
        u += u_shift
        v += v_shift
        uvs[uvid] = (u, v)


def create_cloth_flap(flap, subdivisions_width=1, subdivisions_height=1):
    '''
    Create flap geometry that will be used for nCloth simulation.

    :param flap: Flap object that will later be wrap deformed
    :param subdivisions_width: Number of subdivisions along X-axis
    :param subdivisions_height: Number of subdivisions in Y-axis
    '''

    bounds = flap.boundingBox()
    plane, plane_shape = pm.polyPlane(
        width=bounds.width(),
        height=bounds.height(),
        sx=subdivisions_width,
        sy=subdivisions_height,
        axis=[0, 0, 1],
        cuv=1,
    )
    plane.setTranslation(bounds.center())
    pm.makeIdentity(plane, apply=True, t=True, r=True, s=True, n=False)
    plane.setPivots([0, 0, 0])
    return plane


def create_flaps(num_flaps, base_flaps, layout_index, rows, columns):
    '''
    Create flaps from a set of base flap geometry and pack_uvs according to
    index in a set of rows and columns.

    :param num_flaps: Number of flaps to create
    :param base_flaps: List of base flap geometry to choose at random
    :param layout_index: Index of the flaps in the row column layout
    :param rows: Number of rows in layout
    :param columns: Number of columns in layout
    '''

    # Name and group geometry
    r, c = get_row_col(layout_index, None, columns)
    flaps = [choice(base_flaps).duplicate(rc=True)[0]
             for i in xrange(num_flaps)]

    # Pack UVS
    uvs = get_uvs(flaps[0].getShape(noIntermediate=True))
    top_uvids = get_uvs_in_range(uvs, 0, 0.5, 1, 1)
    bottom_uvids = get_uvs_in_range(uvs, 0, 0, 1, 0.5)
    pack_uvs(
        uvs,
        top_uvids + bottom_uvids,
        layout_index,
        rows,
        columns
    )

    for i, flap in enumerate(flaps):
        mesh = flap.getShape(noIntermediate=True)

        # Shift UVS according to UDIM
        mesh_uvs = list(uvs)
        shift_uvs(mesh_uvs, top_uvids, *index_to_udim(i, num_flaps))
        shift_uvs(mesh_uvs, bottom_uvids, *index_to_udim(i + 1, num_flaps))
        set_uvs(mesh, mesh_uvs)

    return flaps


def radial_arrangement(transforms, radius):
    '''
    Arrange transforms radially at a specific radius around the X-axis.

    :param transforms: List of pymel.PyNode transforms to align
    :param radius: Radius of arrangement
    '''

    rotate_step = 360 / len(transforms)
    radians = math.pi / 180

    for i, t in enumerate(transforms):
        rx = rotate_step * i
        theta = rx * radians
        translation = [0, math.cos(theta) * radius, -math.sin(theta) * radius]
        pm.xform(t, rotation=[-rx, 0, 0], translation=translation)


def create_wrap_deformer(influence, deformed, **kwargs):
    '''
    Create a wrap deformer object

    :param influence: pymel.PyNode influence object
    :param deformed: pymel.PyNode deformed object
    :param kwargs: Wrap attribute values
    '''


    pm.select(deformed, replace=True)

    kwargs.setdefault('weightThreshold', 0.0)
    kwargs.setdefault('maxDistance', 1.0)
    kwargs.setdefault('exclusiveBind', False)
    kwargs.setdefault('autoWeightThreshold', True)
    kwargs.setdefault('falloffMode', 1)

    wrap = pm.deformer(type='wrap')[0]
    for k, v in kwargs.iteritems():
        wrap.attr(k).set(v)

    if not influence.hasAttr('dropoff'):
        influence.addAttr('dropoff', sn='dr', dv=4, min=0, max=20, k=True)
    if not influence.hasAttr('smoothness'):
        influence.addAttr('smoothness', sn='smt', dv=0, min=0, k=True)
    if not influence.hasAttr('inflType'):
        influence.addAttr('inflType', sn='ift', at='short', dv=2, min=1, max=2)

    influence.dropoff.connect(wrap.dropoff[0])
    influence.smoothness.connect(wrap.smoothness[0])
    influence.inflType.connect(wrap.inflType[0])

    influence_shape = influence.getShape(noIntermediate=True)
    influence_shape.worldMesh.connect(wrap.driverPoints[0])

    base = influence.duplicate(name=influence + 'Shape', rc=True)[0]
    base_shape = base.getShape(noIntermediate=True)
    base.hide()
    base_shape.worldMesh.connect(wrap.basePoints[0])

    deformed.worldMatrix.connect(wrap.geomMatrix)

    return wrap, base


def create_collider(flaps, radius):
    '''
    Create collision geometry for combined flaps.

    :param flaps: Combined flaps geometry
    :param radius: Radius of inner wheel allows us to estimate collider geo
    '''

    tx = flaps.boundingBox().width() * 0.5
    ty = flaps.boundingBox().height() * 0.505 - radius
    tz = radius * 1.08
    tz2 = radius * 1.15
    cubea, cubea_shape = pm.polyCube(width=0.2, height=0.05, depth=0.05)
    cubeb, cubeb_shape = pm.polyCube(width=0.2, height=0.05, depth=0.05)
    cubec, cubec_shape = pm.polyCube(width=0.2, height=0.05, depth=0.05)
    cubed, cubed_shape = pm.polyCube(width=0.2, height=0.05, depth=0.05)
    cubea.setTranslation([tx, ty, tz])
    cubeb.setTranslation([-tx, ty, tz])
    cubec.setTranslation([tx, -ty, -tz2])
    cubed.setTranslation([-tx, -ty, -tz2])
    merge_verts(cubea, 7, 5)
    merge_verts(cubea, 6, 4)
    merge_verts(cubeb, 7, 5)
    merge_verts(cubeb, 6, 4)
    merge_verts(cubec, 3, 1)
    merge_verts(cubec, 2, 0)
    merge_verts(cubed, 3, 1)
    merge_verts(cubed, 2, 0)
    collider = pm.polyUnite(
        [cubea, cubeb, cubec, cubed],
        ch=False,
        mergeUVSets=True,
        name=flaps.replace('geo', 'collider_geo')
    )[0]
    return collider


def insert_parent(node):
    pass


def merge_verts(mesh, a, b):
    a = mesh.vtx[a]
    b = mesh.vtx[b]
    a.setPosition(b.getPosition(space='world'), space='world')
    pm.polyMergeVertex([a, b], d=0.0000001)


def make_nCloth(*args, **kwargs):
    '''
    Convert nodes to nCloth objects

    :param args: List of pymel.PyNode transforms
    :param kwargs: nCloth attribute values
    '''

    nodes = args
    kwargs.setdefault('stretchResistance', 20)
    kwargs.setdefault('compressionResistance', 10)
    kwargs.setdefault('bendResistance', 0.6)
    kwargs.setdefault('inputMeshAttract', 1)
    kwargs.setdefault('inputAttractMethod', 1)
    kwargs.setdefault('inputAttractDamp', 0)
    kwargs.setdefault('selfCollisionFlag', 4)
    kwargs.setdefault('thickness', 0.005)
    kwargs.setdefault('pointMass', 100)
    kwargs.setdefault('drag', 0.15)

    # Input attract weight ramp
    ramp = pm.createNode('ramp')
    ramp.colorEntryList[0].color.set(1, 1, 1)
    ramp.colorEntryList[1].position.set(0.1)
    ramp.colorEntryList[1].color.set(0, 0, 0)
    ramp.interpolation.set(0)

    with selection(nodes):
        nClothCreate()
        ncloth_shapes = pm.selected()
        for ncloth in ncloth_shapes:
            for attr, value in kwargs.iteritems():
                ncloth.attr(attr).set(value)
            ramp.outAlpha.connect(ncloth.inputAttractMap)
        ncloth_transforms = [n.getParent() for n in ncloth_shapes]

    return ncloth_shapes, ncloth_transforms


def make_nCollider(*args, **kwargs):
    '''
    Convert nodes to nRigid objects

    :param args: List of pymel.PyNode transforms
    :param kwargs: nRigid attribute values
    '''

    nodes = args
    kwargs.setdefault('collisionFlag', 3)
    kwargs.setdefault('collideStrength', 0.5)
    kwargs.setdefault('thickness', 0.005)

    with selection(nodes):
        nClothMakeCollide()
        collider_shapes = pm.selected()
        for collider in collider_shapes:
            for attr, value in kwargs.iteritems():
                collider.attr(attr).set(value)
        collider_transforms = [c.getParent() for c in collider_shapes]

    return collider_shapes, collider_transforms


def create_copier(in_meshes, name='out_geo#', in_array=None, rotate=True):

    # Create output mesh
    out_shape = pm.createNode('mesh')
    out_xform = out_shape.getParent()
    out_xform.rename(name)

    # Create copier node
    copier = pm.createNode('copier')
    copier.orient.set(1)
    copier.toggleUV.set(1)
    copier.outputMesh.connect(out_shape.inMesh)

    # Connect input meshes
    for i, mesh in enumerate(in_meshes):
        shape = mesh.getShape(noIntermediate=True)
        shape.worldMesh[0].connect(copier.inputMesh[i])

    if not in_array:
        # Connect input transforms
        array = pm.createNode('transformsToArrays')
    else:
        array = in_array

    array.outPositionPP.connect(copier.posArray)
    if rotate:
        array.outRotationPP.connect(copier.rotArray)

    return out_xform, copier, array


def create_joint(name):
    pm.select(clear=True)
    return pm.joint(name=name)
