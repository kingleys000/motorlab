import io
import json
import unittest
from motorlab.ai import AIConfig, advise, advise_async

class Response(io.BytesIO):
    pass

class AITests(unittest.TestCase):
    def setUp(self):
        self.config = AIConfig('https://example.invalid/v1', 'test', 'secret', 1, 'test')
        self.evidence = [{'id': 'ev-1', 'value': 2}]

    def test_success(self):
        def opener(request, timeout):
            self.assertEqual(timeout, 1)
            self.assertNotIn(b'secret', request.data)
            return Response(json.dumps({'choices': [{'message': {'content': 'Revisar ev-1'}}]}).encode())
        self.assertEqual(advise(self.config, self.evidence, opener), 'Revisar ev-1')

    def test_timeout_and_missing_reference(self):
        def timeout(*args, **kwargs):
            raise TimeoutError('secret')
        with self.assertRaisesRegex(RuntimeError, 'no disponible'):
            advise(self.config, self.evidence, timeout)
        with self.assertRaises(RuntimeError):
            advise(self.config, self.evidence, lambda *a, **k: Response(b'{"choices":[{"message":{"content":"sin evidencia"}}]}'))

    def test_default_disabled_async(self):
        with self.assertRaises(ValueError):
            advise_async(AIConfig(), self.evidence).result(timeout=2)
