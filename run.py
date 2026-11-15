"""SARWatch: run the web, verify inputs, or reproduce the scientific analysis."""
import argparse
import errno
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent


def module(name,*args):
    subprocess.run([sys.executable,'-m',name,*args],cwd=ROOT,check=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',nargs='?',default='serve',choices=[
        'serve','check','manifest','build','test','radar','train','impact','reference','reproduce','package','notebook'])
    parser.add_argument('--port',type=int,default=8000)
    parser.add_argument('--open',action='store_true')
    args=parser.parse_args()
    if args.command=='serve':
        import threading
        import webbrowser
        from app.server.web_server import create_server
        try:
            server=create_server(ROOT,args.port)
        except OSError as error:
            if error.errno != errno.EADDRINUSE and getattr(error,'winerror',None) != 10048:
                raise
            print(f'Port {args.port} is busy; choosing an available port.',flush=True)
            server=create_server(ROOT,0)
        url=f'http://127.0.0.1:{server.server_port}'
        print('SARWatch:',url,flush=True)
        print('Keep this window open. Press Ctrl+C to stop.',flush=True)
        if args.open:threading.Timer(.5,lambda:webbrowser.open(url)).start()
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:server.server_close()
    elif args.command in ['check','manifest']:
        module('dev.build.verify_repository',*(['--write-manifest'] if args.command=='manifest' else []))
    elif args.command=='build':
        module('dev.build.build_science_summary');module('dev.build.build_standalone')
    elif args.command=='test':
        module('dev.build.verify_repository');module('dev.build.build_science_summary');module('dev.build.build_standalone')
        subprocess.run([sys.executable,'-m','unittest','discover','-s','dev/tests','-p','test_*.py'],cwd=ROOT,check=True)
    elif args.command=='radar':
        for name in ['radar','screening','comparison','radiometry']:module('pipeline.'+name)
    elif args.command=='train':
        if not all((ROOT/'data/products/radar_rerun'/f'{date}_{ch}_db.tif').exists() for date in ['before','after'] for ch in ['HH','HV']):
            module('pipeline.radar')
        module('pipeline.training')
    elif args.command=='impact':module('pipeline.exposure')
    elif args.command=='reference':module('pipeline.reference');module('pipeline.controls')
    elif args.command=='notebook':module('dev.build.build_notebook')
    elif args.command=='reproduce':
        for name in ['pipeline.radar','pipeline.screening','pipeline.comparison','pipeline.radiometry','pipeline.training',
                     'pipeline.exposure','pipeline.reference','pipeline.controls','dev.build.build_science_summary','dev.build.build_standalone']:
            print('Running:',name,flush=True);module(name)
        module('dev.build.verify_repository','--write-manifest')
    elif args.command=='package':module('dev.build.package_repository')


if __name__=='__main__':main()
