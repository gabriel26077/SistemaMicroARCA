import ipaddress
import unittest

from scripts.check_dns import validate_addresses
from scripts.registry import Invalid


def ips(*values):
    return {ipaddress.ip_address(value) for value in values}


class DNSTests(unittest.TestCase):
    def setUp(self):
        self.origin = ips('192.0.2.10')
        self.edge = ips('104.21.74.162', '2606:4700:3031::6815:4aa2')
        self.networks = [ipaddress.ip_network('104.16.0.0/13'), ipaddress.ip_network('2606:4700::/32')]

    def test_direct_vps_allowed(self):
        validate_addresses(self.origin, self.origin)

    def test_absent_dns_rejected(self):
        with self.assertRaises(Invalid):
            validate_addresses(set(), self.origin)

    def test_other_origin_rejected(self):
        with self.assertRaises(Invalid):
            validate_addresses(ips('192.0.2.20'), self.origin)

    def test_proxy_needs_explicit_selection(self):
        with self.assertRaises(Invalid):
            validate_addresses(self.edge, self.origin)

    def test_cloudflare_cname_allowed(self):
        validate_addresses(self.edge, self.origin, cloudflare=True, target=self.edge, networks=self.networks)

    def test_cloudflare_different_target_rejected(self):
        with self.assertRaises(Invalid):
            validate_addresses(self.edge, self.origin, cloudflare=True,
                               target=ips('104.21.74.163'), networks=self.networks)

    def test_cloudflare_mixed_non_cloudflare_ip_rejected(self):
        addresses = self.edge | ips('192.0.2.20')
        with self.assertRaises(Invalid):
            validate_addresses(addresses, self.origin, cloudflare=True, target=addresses, networks=self.networks)

    def test_cloudflare_missing_networks_rejected(self):
        with self.assertRaises(Invalid):
            validate_addresses(self.edge, self.origin, cloudflare=True, target=self.edge)
