#!/usr/bin/env python3
"""Validate packages, the immutable version ledger, and generated schema."""
import argparse
from pathlib import Path
import sys

try:
    from .registry import ROOT, Invalid, render, validate
except ImportError:
    from registry import ROOT, Invalid, render, validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--baseline-ref', default='HEAD')
    parser.add_argument('--update-lock', action='store_true', help='registrar somente novas versões')
    args = parser.parse_args()
    try:
        packages = validate(args.root.resolve(), args.baseline_ref, args.update_lock)
        render(packages)
    except (Invalid, OSError) as exc:
        print(f'ERRO: {exc}', file=sys.stderr)
        return 1
    print(f'Validação concluída: {len(packages)} versões.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
