import unittest

from kp import util


class TestFindMissing(unittest.TestCase):

    def test_find_missing_number_1(self):
        self.assertEqual(util.find_missing_number(0, 5, set()), 0)

    def test_find_missing_number_2(self):
        self.assertEqual(util.find_missing_number(0, 5, set([0, 1, 2])), 3)

    def test_find_missing_number_3(self):
        self.assertEqual(util.find_missing_number(0, 5, set([0, 1, 2, 3, 4])),
                         5)

    def test_find_missing_number_4(self):
        self.assertEqual(util.find_missing_number(0, 5, set([0, 1, 3, 4, 5])),
                         2)

    def test_find_missing_number_5(self):
        self.assertIsNone(
            util.find_missing_number(0, 6, set([0, 1, 2, 3, 4, 5, 6])))

    def test_find_missing_1(self):
        self.assertEqual(util.find_missing([0, 1, 2, 3, 4, 5, 6], set([])), 0)

    def test_find_missing_2(self):
        self.assertEqual(util.find_missing([0, 1, 2, 3, 4, 5, 6], set([0, 1])),
                         2)

    def test_find_missing_3(self):
        self.assertEqual(
            util.find_missing([0, 1, 2, 3, 4, 5, 6], set([0, 1, 2, 4, 5, 6])),
            3)

    def test_find_missing_4(self):
        self.assertEqual(
            util.find_missing([0, 1, 2, 3, 4, 5], set([0, 1, 2, 3, 4])), 5)

    def test_find_missing_5(self):
        self.assertIsNone(
            util.find_missing([0, 1, 2, 3, 4, 5], set([0, 1, 2, 3, 4, 5])))


class TestProxmoxUtil(unittest.TestCase):

    def test_extract_ip(self):
        self.assertEqual(util.Proxmox.extract_ip("ip=192.168.56.123/24,gw=192.168.56.1"), "192.168.56.123")

class TestKubevip(unittest.TestCase):

    def test_render_pod_manifest(self):
        manifest = util.Kubevip.render_pod_manifest(inf="eth0", vip="192.168.56.21")
        self.assertNotEqual(manifest.find("value: eth0"), -1)
        self.assertNotEqual(manifest.find("value: 192.168.56.21"), -1)
