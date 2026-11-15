"""Package the complete repository, including actual radar/OSM/model inputs."""
import hashlib
import json
from pathlib import Path
import zipfile
from dev.build.verify_repository import shipped_files

ROOT=Path(__file__).resolve().parents[2]


def main():
    out=ROOT/'data/products/releases';out.mkdir(parents=True,exist_ok=True)
    archive=out/'SARWatch-github.zip';files=shipped_files()
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=4) as z:
        for path in files:
            # These are generated from shipped binary crop inputs.
            if path.suffix=='.tif' and ('radar_rerun' in path.parts or path.name.endswith('_source_crop.tif')):continue
            z.write(path,'SARWatch/'+path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise RuntimeError('ZIP integrity check failed.')
    print(json.dumps(dict(file=str(archive),bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest())))


if __name__=='__main__':main()
