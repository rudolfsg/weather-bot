# AWS lambda has a 50mb limit on package zip
import pathlib
import shutil
for p in pathlib.Path('.').rglob('tests'):
    if p.is_file():
        p.unlink()
    else:
        shutil.rmtree(p)

for p in pathlib.Path('.').rglob('__pycache__'):
    if not p.is_file():
        shutil.rmtree(p)
        
for p in pathlib.Path('.').rglob('*.dist-info'):
    if p.is_file():
        p.unlink()
    else:
        shutil.rmtree(p)

for lib in ["libharfbuzz", "libfreetype"]:
    for p in pathlib.Path('.').rglob(f"{lib}*"):
        if p.is_file():
            p.unlink()

# [p.unlink() for p in pathlib.Path('.').rglob('*.dist-info')]
[p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]

shutil.rmtree("venv/lib/python3.9/site-packages/matplotlib/mpl-data/fonts")