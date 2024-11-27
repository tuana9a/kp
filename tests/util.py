import unittest

from kp.util.proxmox import parse_ifconfig
from kp.util.num import find_missing, find_missing_number
from kp.util import kubevip


class TestFindMissing(unittest.TestCase):

    def test_find_missing_number_1(self):
        self.assertEqual(find_missing_number(0, 5, set()), 0)

    def test_find_missing_number_2(self):
        self.assertEqual(find_missing_number(0, 5, set([0, 1, 2])), 3)

    def test_find_missing_number_3(self):
        self.assertEqual(find_missing_number(0, 5, set([0, 1, 2, 3, 4])), 5)

    def test_find_missing_number_4(self):
        self.assertEqual(find_missing_number(0, 5, set([0, 1, 3, 4, 5])), 2)

    def test_find_missing_number_5(self):
        self.assertIsNone(find_missing_number(0, 6, set([0, 1, 2, 3, 4, 5, 6])))

    def test_find_missing_1(self):
        self.assertEqual(find_missing([0, 1, 2, 3, 4, 5, 6], set([])), 0)

    def test_find_missing_2(self):
        self.assertEqual(find_missing([0, 1, 2, 3, 4, 5, 6], set([0, 1])), 2)

    def test_find_missing_3(self):
        self.assertEqual(find_missing([0, 1, 2, 3, 4, 5, 6], set([0, 1, 2, 4, 5, 6])), 3)

    def test_find_missing_4(self):
        self.assertEqual(find_missing([0, 1, 2, 3, 4, 5], set([0, 1, 2, 3, 4])), 5)

    def test_find_missing_5(self):
        self.assertIsNone(find_missing([0, 1, 2, 3, 4, 5], set([0, 1, 2, 3, 4, 5])))


class TestProxmoxUtil(unittest.TestCase):

    def test_parse_ifconfig(self):
        self.assertEqual(parse_ifconfig("ip=192.168.56.123/24,gw=192.168.56.1"), {"ip": "192.168.56.123", "netmask": "24", "gw_ip": "192.168.56.1"})


class TestKubevip(unittest.TestCase):

    def test_render_pod_manifest(self):
        inf = "eth0"
        vip = "192.168.56.21"
        manifest = kubevip.render_pod_manifest(inf=inf, vip=vip)
        self.assertNotEqual(manifest.find(f"value: \"{inf}\""), -1)
        self.assertNotEqual(manifest.find(f"value: \"{vip}\""), -1)
