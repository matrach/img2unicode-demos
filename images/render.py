import time

from img2unicode import *
from pathlib import Path


this = Path(__file__).parent
dual_renderer = Renderer(max_w=160, max_h=60, default_optimizer=FastGenericDualOptimizer("block"))
gamma_renderer = GammaRenderer(max_w=160, max_h=60, default_optimizer=FastGammaOptimizer(charmask="no_block"))

dirs = [('dual', dual_renderer),
        ('gamma', gamma_renderer),
]
print("""
| Dual | Gamma |
| ---- | ----- |
""", end='')
for img_path in this.glob('*.[pj][np]g'): # {png, jpg}
    print('| ', end='')
    for dirname, renderer in dirs:
        basedir = this / dirname
        basedir.mkdir(exist_ok=True, parents=True)
        renderer.render_terminal(img_path, (basedir/img_path.stem).with_suffix('.txt'))
        img_fn = (basedir/img_path.stem).with_suffix('.png')
        renderer.prerender(img_path).save(img_fn)
        print(f"![]({img_fn}) | ", end='')
    print('')

