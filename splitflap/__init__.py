from . import utils, models, controller, ui
from .models import *

# Load SOuP plugin
from maya import cmds
if not cmds.pluginInfo('SOuP', q=True, loaded=True):
    cmds.loadPlugin('SOuP')
