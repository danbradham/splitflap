from __future__ import division, print_function
import pymel.core as pm
from . import utils
from .ui import ProgressBar


class SplitFlapWall(object):

    def __init__(self, pynode):
        self.pynode = pynode
        self._split_flaps = None
        self._world_grp = None
        self._flaps = None
        self._cloth = None
        self._collider = None
        self._anim_grp = None
        self._dyn_grp = None

    @property
    def flaps(self):
        if not self._flaps:
            self._flaps = self.pynode.flaps.inputs()[0]
        return self._flaps

    @property
    def cloth(self):
        if not self._cloth:
            self._cloth = self.pynode.cloth.inputs()[0]
        return self._cloth

    @property
    def collider(self):
        if not self._collider:
            self._collider = self.pynode.collider.inputs()[0]
        return self._collider

    @property
    def dyn_grp(self):
        if not self._dyn_grp:
            self._dyn_grp = self.pynode.dyn_grp.inputs()[0]
        return self._dyn_grp

    @property
    def is_dynamic(self):
        return bool(self.cloth.history(type='nCloth'))

    @property
    def ncloth_shape(self):
        cloth_shape = self.cloth.getShape(noIntermediate=True)
        return cloth_shape.inMesh.inputs(type='nCloth')[0]

    @classmethod
    def create(cls, split_flap, padding=(0.2, 0)):
        '''
        :param split_flap: SplitFlap object
        :param rows: Number of rows in layout
        :param columns: Number of columns in layout
        :param padding: Padding in cm between SplitFlaps
        '''

        ProgressBar.setup(
            title='Creating Split Flap Wall',
            text='Duplicating base split flap...',
            maximum=100,
            parent=utils.get_maya_window()
        )

        rows = split_flap.number_of_rows.get()
        columns = split_flap.number_of_columns.get()
        bounds = split_flap.flaps.boundingBox()
        x_step = bounds.width() + padding[0]
        y_step = bounds.height() + padding[1]
        x_offset = x_step * (columns - 1) * 0.5
        y_offset = y_step * (rows - 1)
        u_step = 1 / columns
        v_step = 1 / rows
        uvs = utils.get_uvs(split_flap.flaps)
        uvids = utils.get_uvs_in_range(uvs, 0, 0, 9999, 9999)

        world_grp = pm.group(name='world_grp', em=True)
        anim_grp = pm.group(name='anim_grp', em=True)

        # Create soup copiers
        arrays = []
        xforms = []

        ProgressBar.set(10, 'Copying rotate geo...')
        rotators = list(split_flap.rotators)
        rot_copier = utils.create_copier(
            [rotators.pop()],
            name=str(rotators) + '_cp')
        rot_xform, rot_copier, rot_array = rot_copier
        arrays.append(rot_array)
        xforms.append(rot_xform)

        while rotators:
            r = rotators.pop()
            copier = utils.create_copier(
                [r],
                name=str(r) + '_cp',
                in_array=rot_array
            )
            xforms.append(copier[0])

        ProgressBar.set(20, 'Copying translate geo...')
        copies = list(split_flap.copies)
        while copies:
            copy = copies.pop()
            static_copier = utils.create_copier(
                [copy],
                name=str(copy) + '_cp',
                in_array=rot_array,
                rotate=False
            )
            xforms.append(static_copier[0])

        ProgressBar.set(30, 'Copying cloth geo...')
        cloth_copier = utils.create_copier(
            [split_flap.cloth],
            name='ncloth_cp',
            in_array=rot_array
        )
        cloth_xform, cloth_copier, cloth_array = cloth_copier
        cloth_xform.hide()

        ProgressBar.set(40, 'Copying collider geo...')
        cldr_copier = utils.create_copier(
            [split_flap.collider],
            'nrigid_cp',
            rotate=False,
            in_array=rot_array)
        cldr_xform, cldr_copier, cldr_array = cldr_copier
        cldr_xform.hide()

        dyn_grp = pm.group([cldr_xform, cloth_xform], name='dynamics_grp')

        split_flaps = []
        step = 30 / rows * columns
        i = 0
        for r in xrange(rows):
            for c in xrange(columns):
                ProgressBar.set(
                    40 + i * step,
                    'Creating Split Flap {}'.format(i + 1)
                )
                index_name = '{:02d}{:02d}'.format(r, c)
                name = str(split_flap.flaps).replace('BASE', index_name)
                new_flap = split_flap.flaps.duplicate(
                    name=name,
                    un=True,
                    rc=False)[0]
                translate = (c * x_step - x_offset, r * -y_step + y_offset, 0)

                # Translate flaps
                new_flap.setTranslation(translate)

                # Create animation hierarchy
                loc = pm.spaceLocator(name='world_{}_xform'.format(index_name))
                loc.hide()
                loc.setTranslation(translate)

                jnt_name = 'anim_{}_xform'.format(index_name)
                anim_jnt = utils.create_joint(jnt_name)
                anim_jnt.setTranslation(translate)
                anim_jnt.rotateX.setKey(v=0, t=1)
                anim_jnt.rotateX.setKey(v=90, t=24)
                parent = anim_jnt
                for i in range(6):
                    rot_name = 'rot_{}_{:02d}'.format(index_name, i)
                    rot_grp = pm.group(em=True, name=rot_name)
                    pm.parent(rot_grp, parent, relative=True)
                    parent = rot_grp

                pm.parent(anim_jnt, anim_grp)
                pm.parent(loc, world_grp)
                pm.parentConstraint(parent, loc)

                # Shift uvs
                mesh_uvs = list(uvs)
                utils.shift_uvs(mesh_uvs, uvids, c * u_step, r * -v_step)
                utils.set_uvs(new_flap, mesh_uvs)

                split_flaps.append(new_flap)
                i += 1

        ProgressBar.set(75, 'Connecting xforms to copier arrays...')
        for i, l in enumerate(world_grp.getChildren()):
            l.rotateOrder.connect(rot_array.inTransforms[i].inRotateOrder)
            l.worldMatrix[0].connect(rot_array.inTransforms[i].inMatrix)

        ProgressBar.set(80, 'Combining flap geometry...takes awhile')
        flaps_geo = pm.polyUnite(
            split_flaps,
            ch=False,
            mergeUVSets=True,
            name='flaps_geo'
        )[0]

        ProgressBar.set(95, 'Grouping and adding attributes...')
        split_flap.pynode.hide()
        grp = pm.group(
            [flaps_geo, xforms, world_grp, anim_grp, dyn_grp],
            name='wall_grp')
        grp.addAttr('world_grp', at='message')
        grp.addAttr('flaps', at='message')
        grp.addAttr('cloth', at='message')
        grp.addAttr('collider', at='message')
        grp.addAttr('anim_grp', at='message')
        grp.addAttr('dyn_grp', at='message')
        world_grp.message.connect(grp.world_grp)
        flaps_geo.message.connect(grp.flaps)
        anim_grp.message.connect(grp.anim_grp)
        cloth_xform.message.connect(grp.cloth)
        cldr_xform.message.connect(grp.collider)
        dyn_grp.message.connect(grp.dyn_grp)

        ProgressBar.set(100, 'Done!')
        ProgressBar.hide()
        return cls(grp)

    def make_dynamic(self):
        if self.is_dynamic:
            return

        ncloth_shapes, ncloth_transforms = utils.make_nCloth(self.cloth)
        ncol_shapes, ncol_transforms = utils.make_nCollider(self.collider)
        wrap, base = utils.create_wrap_deformer(self.cloth, self.flaps)

        pm.parent(ncloth_transforms, self.dyn_grp)
        pm.parent(ncol_transforms, self.dyn_grp)
        pm.parent(base, self.dyn_grp)


class SplitFlap(object):

    def __init__(self, pynode):
        self.pynode = pynode
        self._flaps = None
        self._cloth = None
        self._collider = None
        self._rotators = None

    @property
    def layout_index(self):
        return self.pynode.layout_index

    @property
    def layout_row(self):
        return self.pynode.layout_row

    @property
    def layout_column(self):
        return self.pynode.layout_column

    @property
    def number_of_rows(self):
        return self.pynode.number_of_rows

    @property
    def number_of_columns(self):
        return self.pynode.number_of_columns

    @property
    def flaps(self):
        if not self._flaps:
            self._flaps = self.pynode.flaps.inputs()[0]
        return self._flaps

    @property
    def cloth(self):
        if not self._cloth:
            self._cloth = self.pynode.cloth.inputs()[0]
        return self._cloth

    @property
    def collider(self):
        if not self._collider:
            self._collider = self.pynode.collider.inputs()[0]
        return self._collider

    @property
    def rotators(self):
        rotate_grp = self.pynode.rotate_grp.inputs()[0]
        for t in rotate_grp.getChildren():
            if t != self.cloth:
                yield t

    @property
    def copies(self):
        copy_grp = self.pynode.copy_grp.inputs()[0]
        for t in copy_grp.getChildren():
            yield t

    @property
    def is_dynamic(self):
        return bool(self.cloth.history(type='nCloth'))

    @property
    def ncloth_shape(self):
        cloth_shape = self.cloth.getShape(noIntermediate=True)
        return cloth_shape.inMesh.inputs(type='nCloth')[0]

    @classmethod
    def create(cls, base_flaps, num_images,
               rows, columns, radius, layout_index=0):
        '''
        :param base_flaps: Base flaps to choose from
        :param num_images: Number of images in sequence
        :param rows: Number of rows in layout
        :param columns: Number of columns in layout
        :param radius: Radius
        :param layout_index: Index in row column layout
        '''

        ProgressBar.setup(
            title='Creating Split Flaps',
            text='...',
            maximum=100,
            parent=utils.get_maya_window()
        )

        flaps = utils.create_flaps(
            num_images,
            base_flaps,
            layout_index,
            rows,
            columns)

        ProgressBar.set(10, 'Creating cloth flaps...')
        cloth_flaps = [utils.create_cloth_flap(flaps[0])]
        cloth_flaps.extend([cloth_flaps[0].duplicate(rc=True)[0]
                            for i in xrange(num_images - 1)])

        ProgressBar.set(20, 'Radially arranging flaps...')
        utils.radial_arrangement(flaps, radius)

        ProgressBar.set(30, 'Radially arranging cloth flaps')
        utils.radial_arrangement(cloth_flaps, radius)

        r, c = utils.get_row_col(layout_index, None, columns)
        rowcol = '{:02d}{:02d}'.format(int(r), int(c))
        cloth_name = 'cloth_flap_{}'.format(rowcol)
        flaps_name = 'flaps_{}'.format(rowcol)

        ProgressBar.set(50, 'Combining cloth geo...')
        cloth = pm.polyUnite(
            cloth_flaps,
            ch=False,
            mergeUVSets=True,
            name=cloth_name + '_geo',
        )[0]
        ProgressBar.set(60, 'Combining flap geo...')
        flaps = pm.polyUnite(
            flaps,
            ch=False,
            mergeUVSets=True,
            name=flaps_name + '_geo',
        )[0]
        pm.hide(cloth)

        # Create colliders
        ProgressBar.set(70, 'Creating Collider...')
        collider = utils.create_collider(flaps, radius)

        ProgressBar.set(80, 'Grouping geometry...')
        flaps_grp = pm.group([flaps, collider],
                             name='flaps_{}_geo_grp'.format(rowcol))
        rotate_grp = pm.group(cloth, name='rotate_{}_grp'.format(rowcol))
        copy_grp = pm.group(em=True, name='copy_{}_grp'.format(rowcol))
        split_flap = pm.group(
            [copy_grp, rotate_grp, flaps_grp],
            name=flaps_name + '_grp'
        )
        ProgressBar.set(90, 'Adding attributes...')
        split_flap.addAttr('split_flap', at='bool', dv=True)
        split_flap.addAttr('layout_index', at='long', dv=layout_index)
        split_flap.addAttr('layout_row', at='long', dv=r)
        split_flap.addAttr('layout_column', at='long', dv=c)
        split_flap.addAttr('number_of_rows', at='long', dv=rows)
        split_flap.addAttr('number_of_columns', at='long', dv=columns)
        split_flap.addAttr('flaps', at='message')
        split_flap.addAttr('cloth', at='message')
        split_flap.addAttr('collider', at='message')
        split_flap.addAttr('rotate_grp', at='message')
        split_flap.addAttr('copy_grp', at='message')
        copy_grp.message.connect(split_flap.copy_grp)
        rotate_grp.message.connect(split_flap.rotate_grp)
        flaps.message.connect(split_flap.flaps)
        cloth.message.connect(split_flap.cloth)
        collider.message.connect(split_flap.collider)

        # Rename hierarchy
        ProgressBar.set(95, 'Renaming hierarchy')
        utils.replace_in_hierarchy(split_flap, r'\d+', 'BASE')

        ProgressBar.set(100, 'Done!')
        ProgressBar.hide()
        return cls(split_flap)

    def make_dynamic(self):
        if self.is_dynamic:
            print('Already dynamic')
            return

        ncloth_shapes, ncloth_transforms = utils.make_nCloth(self.cloth)
        ncol_shapes, ncol_transforms = utils.make_nCollider(self.collider)
        _, base = utils.create_wrap_deformer(influence=self.cloth,
            deformed=self.flaps)

        pm.group(ncloth_transforms + ncol_transforms + [base],
                 name='dynamics_grp',
                 parent=self.pynode)
