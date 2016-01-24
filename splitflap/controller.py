import pymel.core as pm
from .ui import Dialog
from .utils import undo_chunk, get_maya_window
from .models import SplitFlapWall, SplitFlap
from functools import partial


class SplitFlapDialog(Dialog):

    def __init__(self, parent=None):
        super(SplitFlapDialog, self).__init__(parent)

        self.generate_base_flaps.connect(self.create_base_flaps)
        self.generate_wall.connect(self.create_wall)

    def create_base_flaps(self):

        selection = pm.selected()
        if not selection:
            msg = 'Select a base mesh to use for the flaps'
            pm.headsUpMessage(msg)
            raise Exception('Select a base mesh to use for the flaps')

        with undo_chunk(auto_undo=True):
            SplitFlap.create(
                base_flaps=selection,
                num_images=32,
                rows=3,
                columns=10,
                radius=0.225,
            )

    def create_wall(self):
        selection = pm.selected()
        if not selection:
            msg = 'Select the root of the base flap hierarchy'
            pm.headsUpMessage(msg)
            raise Exception(msg)

        with undo_chunk(auto_undo=True):
            SplitFlapWall.create(
                pm.selected(),
                padding=(0.2, -0.1)
            ).make_dynamic()


def show(cache=[]):
    if cache:
        return cache[0]

    dialog = SplitFlapDialog(parent=get_maya_window())
    dialog.show()

    cache.append(dialog)
    return dialog
