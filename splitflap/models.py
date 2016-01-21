from __future__ import division, print_function
import pymel.core as pm
from . import utils
reload(utils)


class SplitFlapWall(object):

    def __init__(self, pynode):
        self.pynode = pynode
        self._split_flaps = None

    @property
    def split_flaps(self):
        if not self._split_flaps:
            self._split_flaps = []
            for node in pm.ls(self.pynode, dag=True):
                if node.hasAttr('split_flap'):
                    self._split_flaps.append(SplitFlap(node))
        return self._split_flaps

    @classmethod
    def create(cls, split_flap, padding=0.2):
        '''
        :param split_flap: SplitFlap object
        :param rows: Number of rows in layout
        :param columns: Number of columns in layout
        :param padding: Padding in cm between SplitFlaps
        '''

        rows = split_flap.number_of_rows.get()
        columns = split_flap.number_of_columns.get()
        bounds = split_flap.flaps.boundingBox()
        x_step = bounds.width() + padding
        y_step = bounds.height() + padding
        u_step = 1 / columns
        v_step = 1 / rows
        uvs = utils.get_uvs(split_flap.flaps)
        uvids = utils.get_uvs_in_range(uvs, 0, 0, 9999, 9999)

        split_flaps = []
        i = 0
        for r in xrange(rows):
            for c in xrange(columns):
                index_name = '{:02d}{:02d}'.format(r, c)
                new_flap = split_flap.pynode.duplicate(
                    name='flaps_{}_grp'.format(index_name),
                    un=True,
                    rc=False)[0]

                # Translate group
                new_flap.setTranslation([c * x_step, r * -y_step, 0])
                new_flap.layout_index.set(i)
                new_flap.layout_row.set(r)
                new_flap.layout_column.set(c)

                # Shift uvs
                new_split_flap = SplitFlap(new_flap)
                flaps = new_split_flap.flaps
                mesh_uvs = list(uvs)
                utils.shift_uvs(mesh_uvs, uvids, c * u_step, r * -v_step)
                utils.set_uvs(flaps, mesh_uvs)

                # Rename Hierarchy
                utils.replace_in_hierarchy(new_flap, 'BASE', index_name)

                split_flaps.append(new_split_flap)
                i += 1

        grp = pm.group([f.pynode for f in split_flaps], name='split_flap_wall')
        return cls(grp)

    def make_dynamic(self):
        needs_ncloth = []
        colliders = []

        for split_flap in self.split_flaps:
            if not split_flap.is_dynamic:
                needs_ncloth.append(split_flap.cloth)
                colliders.append(split_flap.collider)

        if needs_ncloth:
            ncloth_shapes, ncloth_transforms = utils.make_nCloth(needs_ncloth)
            ncol_shapes, ncol_transforms = utils.make_nCollider(colliders)

        wrap_nodes = []
        for split_flap in self.split_flaps:
            _, base = utils.create_wrap_deformer(
                influence=split_flap.cloth,
                deformed=split_flap.flaps)
            wrap_nodes.append(base)

        pm.group(ncloth_transforms + ncol_transforms,
                 name='dynamics_grp',
                 parent=self.pynode)


class SplitFlap(object):

    def __init__(self, pynode):
        self.pynode = pynode
        self._flaps = None
        self._cloth = None
        self._collider = None

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

        flaps = utils.create_flaps(
            num_images,
            base_flaps,
            layout_index,
            rows,
            columns)
        cloth_flaps = [utils.create_cloth_flap(flaps[0])]
        cloth_flaps.extend([cloth_flaps[0].duplicate(rc=True)[0]
                            for i in xrange(num_images - 1)])
        utils.radial_arrangement(flaps, radius)
        utils.radial_arrangement(cloth_flaps, radius)

        r, c = utils.get_row_col(layout_index, None, columns)
        rowcol = '{:02d}{:02d}'.format(int(r), int(c))
        cloth_name = 'cloth_flap_{}'.format(rowcol)
        flaps_name = 'flaps_{}'.format(rowcol)

        cloth = pm.polyUnite(
            cloth_flaps,
            ch=False,
            mergeUVSets=True,
            name=cloth_name + '_geo',
        )[0]
        flaps = pm.polyUnite(
            flaps,
            ch=False,
            mergeUVSets=True,
            name=flaps_name + '_geo',
        )[0]
        pm.hide(cloth)

        # Create colliders
        collider = utils.create_collider(flaps, radius)

        flaps_grp = pm.group([flaps, collider],
                             name='flaps_{}_geo_grp'.format(rowcol))
        rotate_grp = pm.group(cloth, name='rotate_{}_grp'.format(rowcol))
        split_flap = pm.group([rotate_grp, flaps_grp], name=flaps_name + '_grp')
        split_flap.addAttr('split_flap', at='bool', dv=True)
        split_flap.addAttr('layout_index', at='long', dv=layout_index)
        split_flap.addAttr('layout_row', at='long', dv=r)
        split_flap.addAttr('layout_column', at='long', dv=c)
        split_flap.addAttr('number_of_rows', at='long', dv=rows)
        split_flap.addAttr('number_of_columns', at='long', dv=columns)
        split_flap.addAttr('flaps', at='message')
        split_flap.addAttr('cloth', at='message')
        split_flap.addAttr('collider', at='message')
        flaps.message.connect(split_flap.flaps)
        cloth.message.connect(split_flap.cloth)
        collider.message.connect(split_flap.collider)

        # Rename hierarchy
        utils.replace_in_hierarchy(split_flap, r'\d+', 'BASE')

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

    def rem_dynamic(self):
        if not self.is_dynamic:
            print('Not dynamic')
            return

        pass
