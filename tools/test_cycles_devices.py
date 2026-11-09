"""Exercise strict device selection without requiring Blender or a GPU."""

from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
import unittest

from cycles_devices import configure_cycles


def device(name, kind, identifier):
    return SimpleNamespace(name=name, type=kind, id=identifier, use=True)


class DeviceSelectionTests(unittest.TestCase):
    def setUp(self):
        self.cpu = device('Ryzen CPU', 'CPU', 'cpu')
        self.gpu = device('RTX 4090', 'CUDA', 'cuda-4090')
        self.preferences = SimpleNamespace(
            compute_device_type='NONE', devices=[self.cpu, self.gpu],
            get_devices_for_type=lambda backend: self.preferences.devices)
        self.bpy = SimpleNamespace(context=SimpleNamespace(preferences=SimpleNamespace(
            addons={'cycles': SimpleNamespace(preferences=self.preferences)})))
        self.scene = SimpleNamespace(render=SimpleNamespace(engine=''),
                                     cycles=SimpleNamespace(device='CPU'))

    def configure(self, **kwargs):
        with redirect_stdout(StringIO()):
            return configure_cycles(self.scene, bpy_module=self.bpy, **kwargs)

    def test_cuda_selects_gpu_and_disables_cpu(self):
        result = self.configure(backend='CUDA', device='RTX 4090')
        self.assertEqual(result['backend'], 'CUDA')
        self.assertEqual(self.scene.cycles.device, 'GPU')
        self.assertTrue(self.gpu.use)
        self.assertFalse(self.cpu.use)

    def test_exact_id_disambiguates_multiple_gpus(self):
        other = device('RTX 4090', 'CUDA', 'cuda-other')
        self.preferences.devices.append(other)
        self.configure(backend='CUDA', device='cuda-4090')
        self.assertTrue(self.gpu.use)
        self.assertFalse(other.use)

    def test_single_gpu_is_selected_without_name(self):
        self.configure(backend='CUDA')
        self.assertTrue(self.gpu.use)
        self.assertFalse(self.cpu.use)

    def test_missing_gpu_rejects_instead_of_falling_back(self):
        self.preferences.devices = [self.cpu]
        with self.assertRaisesRegex(RuntimeError, 'No render was started'):
            self.configure(backend='CUDA')

    def test_nonmatching_name_rejects(self):
        with self.assertRaises(RuntimeError):
            self.configure(backend='CUDA', device='another GPU')

    def test_ambiguous_gpu_requires_explicit_selection(self):
        self.preferences.devices.append(device('second GPU', 'CUDA', 'cuda-other'))
        with self.assertRaisesRegex(RuntimeError, 'found 2'):
            self.configure(backend='CUDA')

    def test_other_backend_device_cannot_masquerade_as_cuda(self):
        self.gpu.type = 'OPTIX'
        with self.assertRaises(RuntimeError):
            self.configure(backend='CUDA')

    def test_cpu_is_explicit_and_does_not_query_gpu(self):
        def fail(_backend):
            raise AssertionError('CPU fallback must not initialize a GPU')
        self.preferences.get_devices_for_type = fail
        result = self.configure(backend='CPU')
        self.assertEqual(result['backend'], 'CPU')
        self.assertEqual(self.scene.cycles.device, 'CPU')

    def test_cpu_rejects_gpu_selector(self):
        with self.assertRaises(ValueError):
            self.configure(backend='CPU', device='RTX 4090')

    def test_initialization_failure_is_reported(self):
        def fail(_backend):
            raise RuntimeError('driver initialization failed')
        self.preferences.get_devices_for_type = fail
        with self.assertRaisesRegex(RuntimeError, 'no automatic fallback'):
            self.configure(backend='OPTIX')


if __name__ == '__main__':
    unittest.main()
