from PySide import QtGui, QtCore
from psforms import *
from psforms.validators import required
from psforms.fields import *


class SplitFlapForm(Form):

    meta = FormMetaData(
        title='Base Flap Options',
        description='Create a base split flap object',
        header=False,
    )

    num_images = IntField('Number of Images', range=(8, 100), default=24)
    rows = IntField('Number of Rows', range=(1, 100), default=2)
    columns = IntField('Number of Columns', range=(1, 100), default=2)
    radius = FloatField('Radius', default=0.2)


class WallForm(Form):

    meta = FormMetaData(
        title='Wall Options',
        description='Create a split flap wall',
        header=False,
    )

    padding = FloatField('Padding', default=0.1)


class CompositeForm(Form):
    meta = FormMetaData(
        title='Split Flap',
        description='Create a dynamic split flap display',
        header=True
    )
    split_flap = SplitFlapForm()
    wall = WallForm()



def split_flap_dialog(parent=None):

    dialog = CompositeForm.as_dialog(parent=parent)

    dialog.cancel_button.clicked.disconnect()
    dialog.accept_button.clicked.disconnect()
    dialog.cancel_button.setParent(None)
    dialog.accept_button.setParent(None)

    dialog.create_base = QtGui.QPushButton('Create Base Flaps')
    dialog.add_base_dynamics = QtGui.QPushButton('Add Dynamics')
    dialog.rem_base_dynamics = QtGui.QPushButton('Remove Dynamics')
    basebutton_layout = QtGui.QHBoxLayout()
    basebutton_layout.setSpacing(10)
    basebutton_layout.setContentsMargins(20, 0, 20, 20)
    basebutton_layout.addWidget(dialog.create_base)
    basebutton_layout.addWidget(dialog.add_base_dynamics)
    basebutton_layout.addWidget(dialog.rem_base_dynamics)

    dialog.create_wall_button = QtGui.QPushButton('Create Wall')
    dialog.add_wall_dynamics = QtGui.QPushButton('Add Dynamics')
    wallbutton_layout = QtGui.QHBoxLayout()
    wallbutton_layout.setSpacing(10)
    wallbutton_layout.setContentsMargins(20, 0, 20, -20)
    wallbutton_layout.addWidget(dialog.create_wall_button)
    wallbutton_layout.addWidget(dialog.add_wall_dynamics)

    dialog.split_flap.layout.addLayout(basebutton_layout)
    dialog.wall.layout.addLayout(wallbutton_layout)

    dialog.setStyleSheet(stylesheet)
    return dialog


if __name__ == '__main__':
    import signal
    import sys
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QtGui.QApplication(sys.argv)
    split_flap_dialog().show()
    sys.exit(app.exec_())
