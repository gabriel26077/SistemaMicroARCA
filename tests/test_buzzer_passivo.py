import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'packages/buzzer-passivo/1.0.0'


class Pin:
    OUT = 1
    def __init__(self, number, mode, value=0):
        self.number, self.mode, self.level = number, mode, value
    def init(self, mode, value=0):
        self.mode, self.level = mode, value


class PWM:
    created = []
    def __init__(self, pin, freq, duty_u16):
        self.pin, self.frequency, self.duty, self.closed = pin, freq, duty_u16, False
        self.created.append(self)
    def duty_u16(self, value):
        self.duty = value
    def freq(self, value):
        self.frequency = value
    def deinit(self):
        self.closed = True


class BuzzerTests(unittest.TestCase):
    def setUp(self):
        PWM.created = []
        self.machine = patch.dict(sys.modules, {'machine': types.SimpleNamespace(Pin=Pin, PWM=PWM)})
        self.machine.start()
        spec = importlib.util.spec_from_file_location('test_buzzer_library', PACKAGE / 'lib_buzzer_passivo.py')
        self.lib = importlib.util.module_from_spec(spec)
        exec(compile((PACKAGE / 'lib_buzzer_passivo.py').read_text(), 'lib_buzzer_passivo.py', 'exec'), self.lib.__dict__)
        self.sleep = patch.object(self.lib.time, 'sleep_ms', create=True)
        self.wait = self.sleep.start()

    def tearDown(self):
        self.lib.parar_todos()
        self.sleep.stop()
        self.machine.stop()

    def test_notes_and_octaves(self):
        for note in ('A', 'La', 'Lá'):
            self.assertEqual(self.lib.frequencia_nota(note, 4), 440)
        self.assertEqual(self.lib.frequencia_nota('Dó', 4), 262)
        self.assertEqual(self.lib.frequencia_nota('C#', 4), 277)
        self.assertEqual(self.lib.frequencia_nota('A', 5), 880)

    def test_timed_tone_waits_and_releases_pwm(self):
        buzzer = self.lib.criar_buzzer(25)
        buzzer.tocar_nota('A', 4, 300)
        self.wait.assert_called_once_with(300)
        pwm = PWM.created[-1]
        self.assertEqual(pwm.frequency, 440)
        self.assertTrue(pwm.closed)
        self.assertEqual(pwm.duty, 0)
        self.assertEqual(buzzer._pin.level, 0)

    def test_continuous_tone_does_not_wait_and_reuses_channel(self):
        buzzer = self.lib.criar_buzzer(25)
        buzzer.iniciar(440)
        buzzer.iniciar(880)
        self.wait.assert_not_called()
        self.assertEqual(len(PWM.created), 1)
        self.assertEqual(PWM.created[0].frequency, 880)
        self.assertEqual(PWM.created[0].duty, 32768)
        buzzer.parar()
        buzzer.parar()
        buzzer.iniciar(220)
        self.assertEqual(len(PWM.created), 2)

    def test_interrupt_during_note_silences_and_propagates(self):
        buzzer = self.lib.criar_buzzer()
        self.wait.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            buzzer.tocar(440, 500)
        self.assertTrue(PWM.created[-1].closed)
        self.assertEqual(PWM.created[-1].duty, 0)

    def test_context_cleanup_and_same_pin_replacement(self):
        first = self.lib.criar_buzzer(25)
        first.iniciar()
        with self.lib.criar_buzzer(25) as second:
            self.assertTrue(first._fechado)
            self.assertTrue(PWM.created[0].closed)
            second.iniciar()
        self.assertTrue(PWM.created[-1].closed)
        self.assertFalse(self.lib._buzzers)

    def test_cleanup_hook_releases_all_buzzers(self):
        self.lib.criar_buzzer(25).iniciar()
        self.lib.criar_buzzer(26).iniciar()
        self.lib.__arca_cleanup__()
        self.lib.__arca_cleanup__()
        self.assertTrue(all(pwm.closed for pwm in PWM.created))
        self.assertFalse(self.lib._buzzers)

    def test_invalid_values_fail_before_allocating_pwm(self):
        for pin in (6, 34, -1, 2.5, True):
            with self.assertRaises(ValueError):
                self.lib.criar_buzzer(pin)
        buzzer = self.lib.criar_buzzer()
        for frequency in (0, -1, 20001, 440.5, float('nan'), True):
            with self.assertRaises(ValueError):
                buzzer.iniciar(frequency)
        for duration in (-1, 60001, 1.5):
            with self.assertRaises(ValueError):
                buzzer.tocar(440, duration)
        for note, octave in (('H', 4), ('A', -1), ('A', 9)):
            with self.assertRaises(ValueError):
                buzzer.tocar_nota(note, octave, 100)
        self.assertFalse(PWM.created)

    def test_real_manifest_templates_execute_with_the_library(self):
        manifest = json.loads((PACKAGE / 'blocks.json').read_text())
        for block in manifest['blocks']:
            scope = {'criar_buzzer': self.lib.criar_buzzer}
            if not block['type'].endswith('_criar'):
                scope['buzzer'] = self.lib.criar_buzzer()
            fields = {f['name']: f['default'] if f['type'] == 'identifier' else repr(f['default'])
                      for f in block['fields']}
            exec(block['python']['template'].format(**fields), scope)
            self.lib.parar_todos()
