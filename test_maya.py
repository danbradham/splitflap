import sys

sys.path.insert(1, 'Y:/BNS_Pipeline/development/projects/splitflap')

import splitflap
reload(splitflap)
import pymel.core as pm


base_flap = splitflap.SplitFlap.create(
    base_flaps=pm.selected(),
    num_images=32,
    rows=3,
    columns=10,
    radius=0.225,
)

wall = splitflap.SplitFlapWall.create(
    base_flap,
    padding=(0.2, -0.1)
)

wall.make_dynamic()
