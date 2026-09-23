#!/usr/bin/env python3
"""Validate direct DNS or the explicitly selected Cloudflare CNAME deployment."""
import argparse
import ipaddress
import json
import socket
import sys
from urllib.request import build_opener

try:
    from .registry import Invalid, require
    from .verify_public import NoRedirect
except ImportError:
    from registry import Invalid, require
    from verify_public import NoRedirect

DOMAIN = 'libs-microarca.traceedu.com.br'
CNAME_TARGET = 'traceedu.com.br'


def resolve(host):
    return {ipaddress.ip_address(s[4][0]) for s in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}


def cloudflare_networks():
    networks = []
    opener = build_opener(NoRedirect())
    with opener.open('https://api.cloudflare.com/client/v4/ips', timeout=15) as response:
        require(response.status == 200, 'lista de redes Cloudflare indisponível')
        data = response.read(65537)
        require(len(data) <= 65536, 'lista de redes Cloudflare excessiva')
        document = json.loads(data)
        require(document.get('success') is True, 'consulta de redes Cloudflare falhou')
        for version in (4, 6):
            values = document.get('result', {}).get(f'ipv{version}_cidrs', [])
            require(isinstance(values, list) and values, 'lista de redes Cloudflare ausente')
            group = [ipaddress.ip_network(value) for value in values]
            require(all(n.version == version and n.prefixlen > 0 for n in group),
                    'lista de redes Cloudflare inválida')
            networks.extend(group)
    return networks


def validate_addresses(actual, origin, *, cloudflare=False, target=None, networks=()):
    require(actual and origin, 'DNS ou endereços da VPS ausentes')
    if not cloudflare:
        require(actual <= origin, 'DNS não aponta diretamente para a VPS; use --cloudflare somente para o CNAME aprovado')
        return
    require(target and actual == target, f'DNS não corresponde ao destino CNAME aprovado: {CNAME_TARGET}')
    require(all(any(ip in network for network in networks) for ip in actual),
            'DNS contém endereço fora das redes oficiais Cloudflare')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin-ips', required=True)
    parser.add_argument('--cloudflare', action='store_true')
    args = parser.parse_args()
    try:
        validate_addresses(resolve(DOMAIN), {ipaddress.ip_address(s) for s in args.origin_ips.split()},
                           cloudflare=args.cloudflare,
                           target=resolve(CNAME_TARGET) if args.cloudflare else None,
                           networks=cloudflare_networks() if args.cloudflare else ())
    except (Invalid, OSError, ValueError) as exc:
        print(f'ERRO: {exc}', file=sys.stderr)
        return 1
    if args.cloudflare:
        print('DNS do proxy Cloudflare validado contra o destino CNAME aprovado e as redes oficiais.')
        print('DNS do proxy não comprova a origem: a verificação HTTPS do catálogo é obrigatória após ativação.')
    else:
        print('DNS direto da VPS validado.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
