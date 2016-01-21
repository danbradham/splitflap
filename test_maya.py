import sys

sys.path.insert(1, 'Y:/BNS_Pipeline/development/projects/splitflap')

import splitflap
reload(splitflap)
import pymel.core as pm


sf = splitflap.SplitFlap.create(
    base_flaps=pm.selected(),
    num_images=24,
    rows=2,
    columns=4,
    radius=0.2,
)

wall = splitflap.SplitFlapWall.create(
    splitflap.SplitFlap(pm.selected()[0]),
    rows=7,
    columns=13,
    padding=0.1,
)
