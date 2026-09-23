#!/usr/bin/env python3
"""Build a complete tree before atomically exchanging it with dist (Linux)."""
import argparse
import ctypes
import fcntl
import os
from pathlib import Path
import shutil
import sys
import tempfile

try:
    from .registry import ROOT, Invalid, inventory, render, require, validate
except ImportError:
    from registry import ROOT, Invalid, inventory, render, require, validate


def exchange(left, right):
    libc = ctypes.CDLL(None, use_errno=True)
    require(hasattr(libc, 'renameat2'), 'substituição atômica requer Linux/glibc com renameat2')
    rename = libc.renameat2
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(-100, os.fsencode(left), -100, os.fsencode(right), 2):
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))


def expected_tree(files):
    result = dict(files)
    for name in files:
        for parent in Path(name).parents:
            if str(parent) != '.':
                result[parent.as_posix() + '/'] = b''
    return result


def build(root=ROOT, check=False, baseline='HEAD'):
    root = Path(root).resolve()
    dist = root / 'dist'
    # --check never creates files, locks, or temporary trees.
    if check:
        wanted = expected_tree(render(validate(root, baseline)))
        require(inventory(dist) == wanted, 'dist/ desatualizado; execute build_catalog.py')
        return
    lock_path = root / '.catalog-build.lock'
    require(not lock_path.is_symlink(), 'lock não pode ser link simbólico')
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        files = render(validate(root, baseline))
        require(not dist.is_symlink(), 'dist não pode ser link simbólico')
        if dist.exists() and inventory(dist) == expected_tree(files):
            return
        stage = Path(tempfile.mkdtemp(prefix='.catalog-stage-', dir=root))
        try:
            stage.chmod(0o755)
            for name, data in files.items():
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('wb') as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                target.chmod(0o644)
            require(inventory(stage) == expected_tree(files), 'verificação temporária falhou')
            if dist.exists():
                exchange(stage, dist)
            else:
                os.replace(stage, dist)
        finally:
            if stage.exists():
                shutil.rmtree(stage)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--baseline-ref', default='HEAD')
    args = parser.parse_args()
    try:
        build(args.root, args.check, args.baseline_ref)
    except (Invalid, OSError) as exc:
        print(f'ERRO: {exc}', file=sys.stderr)
        return 1
    print('dist/ sincronizado.' if args.check else 'Catálogo validado e gerado.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
