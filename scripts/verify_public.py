#!/usr/bin/env python3
"""Verify TLS, catalog, caching and every published file against local dist."""
import argparse
import sys
from urllib.error import URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

try:
    from .registry import ROOT, MAX_CATALOG, Invalid, parse_json, require, sha
except ImportError:
    from registry import ROOT, MAX_CATALOG, Invalid, parse_json, require, sha


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Invalid(f'redirecionamento inesperado: {newurl}')


def verify(endpoint, local=ROOT / 'dist'):
    require(urlsplit(endpoint).scheme == 'https', 'HTTPS obrigatório')
    opener = build_opener(NoRedirect())

    def fetch(url, limit, cache):
        with opener.open(url, timeout=15) as response:
            require(response.status == 200, f'HTTP inesperado: {url}')
            require(response.headers.get('X-Content-Type-Options') == 'nosniff', 'nosniff ausente')
            require(response.headers.get('Access-Control-Allow-Origin') == '*', 'CORS ausente')
            require(cache in response.headers.get('Cache-Control', ''), f'cache inválido: {url}')
            length = response.headers.get('Content-Length')
            require(length is None or int(length) <= limit, f'Content-Length excede limite: {url}')
            data = response.read(limit + 1)
            require(len(data) <= limit, f'download excede limite: {url}')
            require(length is None or int(length) == len(data), f'download truncado: {url}')
            return data
    raw = fetch(endpoint, MAX_CATALOG, 'no-cache')
    require(raw == (local / 'v1/catalog.json').read_bytes(), 'catálogo público difere de dist local')
    catalog = parse_json(raw)
    count = 0
    for package in catalog['packages']:
        for file in package['files']:
            data = fetch(urljoin(endpoint, file['url']), file['size'], 'public, max-age=31536000, immutable')
            require(len(data) == file['size'] and sha(data) == file['sha256'], f'integridade inválida: {file["url"]}')
            count += 1
        for key in ('license_url', 'provenance_url'):
            if key in package:
                name = package[key]
                data = fetch(urljoin(endpoint, name), MAX_CATALOG, 'public, max-age=31536000, immutable')
                require(data == (local / 'v1' / name).read_bytes(), f'metadados divergentes: {name}')
    print(f'HTTPS, catálogo, headers, licenças e {count} arquivos verificados.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='https://libs-microarca.traceedu.com.br/v1/catalog.json')
    args = parser.parse_args()
    try:
        verify(args.url)
    except (Invalid, OSError, URLError, ValueError) as exc:
        print(f'ERRO: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
