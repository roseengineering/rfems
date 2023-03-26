
import os, zipfile, tempfile, subprocess

def render_stl(name, d):
    buf = None
    dirname = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdirname:
        os.chdir(tmpdirname)
        scad_filename = 'model.scad'
        stl_filename = 'model.stl'
        d.save_as_scad(scad_filename)
        cmd = [ 'openscad', '--export', 'asciistl', '-o', stl_filename, scad_filename ]
        res = subprocess.run(cmd, capture_output=True)
        if 'model.stl' in os.listdir():
            with open(stl_filename, 'rb') as f:
                buf = f.read()
    if not buf:
        raise ValueError(f'Bad stl file: {name}')
    os.chdir(dirname)
    return buf


class openzip(object):
    def __init__(self, filename):
        self.filename = filename
        self.manifest = []

    def save(self, filename, solid):
        self.manifest.append((filename, solid)) 

    def __enter__(self):
        return self

    def __exit__(self, *args):
        filename = self.filename
        root, ext = os.path.splitext(filename)
        if ext != '.zip':
            filename = f'{root}.zip'
        with zipfile.ZipFile(filename, mode='w') as zf:
            for name, solid in self.manifest:
                buf = render_stl(name, solid)
                name = f'{name}.stl'
                if name in zf.namelist():
                   print(f'already exists in archive: {name}')
                else:
                   zinfo = zipfile.ZipInfo(name)
                   zf.writestr(zinfo, buf, compress_type=zipfile.ZIP_DEFLATED)

    def save(self, filename, solid):
        self.manifest.append([ filename, solid ]) 



