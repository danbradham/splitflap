import pymel.core as pm
from .ui import split_flap_dialog
from .utils import undo_chunk
from .uiutils import get_maya_window
from .models import SplitFlapWall, SplitFlap
from functools import partial


def create_base_flap(dialog):

    selection = pm.selected()
    if not selection:
        msg = 'Select a base mesh to use for the flaps'
        pm.headsUpMessage(msg)
        raise Exception('Select a base mesh to use for the flaps')

    user_input = dialog.split_flap.get_value()

    with undo_chunk(auto_undo=True):
        SplitFlap.create(
            base_flaps=selection,
            **user_input
        )


def create_wall(dialog):

    selection = pm.selected()
    if not selection:
        msg = 'Select the root of the base flap hierarchy'
        pm.headsUpMessage(msg)
        raise Exception(msg)

    user_input = dialog.wall.get_value()

    with undo_chunk(auto_undo=True):
        SplitFlapWall.create(
            SplitFlap(selection[0]),
            **user_input
        )


def add_base_dynamics():

    selection = pm.selected()
    if not selection:
        msg = 'Select base flap hierarchy to add dynamics'
        pm.headsUpMessage(msg)
        raise Exception(msg)

    SplitFlap(selection[0]).make_dynamic()


def rem_base_dynamics():
    pass


def add_wall_dynamics():

    selection = pm.selected()
    if not selection:
        msg = 'Select wall hierarchy to add dynamics'
        pm.headsUpMessage(msg)
        raise Exception(msg)

    SplitFlapWall(selection[0]).make_dynamic()


def show(cache=[]):
    if cache:
        return cache[0]

    dialog = split_flap_dialog(parent=get_maya_window())
    dialog.create_base.clicked.connect(partial(create_base_flap, dialog))
    dialog.add_base_dynamics.clicked.connect(add_base_dynamics)
    dialog.rem_base_dynamics.clicked.connect(rem_base_dynamics)

    dialog.create_wall_button.clicked.connect(partial(create_wall, dialog))
    dialog.add_wall_dynamics.clicked.connect(add_wall_dynamics)
    dialog.show()

    cache.append(dialog) # append to cache
    return dialog
