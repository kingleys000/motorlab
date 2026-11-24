import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from motorlab.ai import AIConfig, structured_agent, run_agents


class StructuredAITests(unittest.TestCase):
    def setUp(self):
        self.config = AIConfig('https://example.invalid/v1', 'model', 'super-secret-key', 1, 'test')
        self.evidence = [{'id': 'ev-1', 'signal': 'current'}]
        self.proposal = {'hipotesis': [{'explicacion': 'Sobrecarga posible', 'alternativas': 'Medición errónea',
            'comprobaciones': 'Medir corriente', 'evidencias': ['ev-1'], 'componentes': ['motor']}]}
        self.review = {'hallazgos': [{'conclusion': 'La ubicación es insuficiente', 'estado': 'insuficiente',
                                     'evidencias': ['ev-1'], 'componentes': ['motor']}]}

    def reply(self, obj):
        return io.BytesIO(json.dumps({'choices': [{'message': {'content': json.dumps(obj)}}]}).encode())

    def test_sequence_and_disagreement(self):
        calls = []
        def opener(request, timeout):
            payload = json.loads(request.data)
            self.assertNotIn('super-secret-key', request.data.decode())
            calls.append(payload)
            return self.reply(self.proposal if len(calls) == 1 else self.review)
        result = run_agents(self.config, self.evidence, {'origin': 'synthetic'}, opener)
        self.assertEqual(result['revision'], self.review)
        self.assertEqual(len(calls), 2)
        self.assertIn('propuesta', calls[1]['messages'][1]['content'])

    def test_invalid_json_and_invented_references(self):
        with self.assertRaises(RuntimeError):
            structured_agent(self.config, 'diagnostico', self.evidence, {}, opener=lambda *a, **k: io.BytesIO(b'bad'))
        invalid_content = {'choices': [{'message': {'content': '{mal formado'}}]}
        with self.assertRaises(RuntimeError):
            structured_agent(self.config, 'diagnostico', self.evidence, {},
                             opener=lambda *a, **k: io.BytesIO(json.dumps(invalid_content).encode()))
        for key, value in [('evidencias', ['no-existe']), ('componentes', ['pieza-inventada'])]:
            proposal = json.loads(json.dumps(self.proposal))
            proposal['hipotesis'][0][key] = value
            with self.assertRaises(RuntimeError):
                structured_agent(self.config, 'diagnostico', self.evidence, {}, opener=lambda *a, **k: self.reply(proposal))

    def test_timeout_keeps_proposal_without_review(self):
        count = 0
        def opener(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 1:
                return self.reply(self.proposal)
            raise TimeoutError('super-secret-key')
        result = run_agents(self.config, self.evidence, {}, opener)
        self.assertEqual(result['propuesta'], self.proposal)
        self.assertIsNone(result['revision'])
        self.assertNotIn('super-secret-key', str(result))
        with self.assertRaises(RuntimeError) as error:
            run_agents(self.config, self.evidence, {}, lambda *a, **k: (_ for _ in ()).throw(TimeoutError('super-secret-key')))
        self.assertNotIn('super-secret-key', str(error.exception))

    def test_reject_credential_echo_and_query_credentials(self):
        proposal = json.loads(json.dumps(self.proposal))
        proposal['hipotesis'][0]['explicacion'] = 'super-secret-key'
        with self.assertRaises(RuntimeError):
            structured_agent(self.config, 'diagnostico', self.evidence, {}, opener=lambda *a, **k: self.reply(proposal))
        with self.assertRaises(ValueError):
            AIConfig('https://example.invalid/v1?key=secret', 'model', 'x', 1, 'test').validate()

    def test_http_errors_are_actionable_and_do_not_echo_credentials(self):
        cases = [
            (400, [{'error': {'message': 'Please pass a valid API key'}}], 'clave API'),
            (401, {'error': {'message': 'super-secret-key'}}, 'autenticación'),
            (403, {}, 'permisos'),
            (404, {}, 'modelo'),
            (429, {}, 'cuota'),
            (503, {}, 'temporalmente'),
        ]
        for code, payload, expected in cases:
            with self.subTest(code=code):
                def fail(request, timeout):
                    raise HTTPError(request.full_url, code, 'super-secret-key', {},
                                    io.BytesIO(json.dumps(payload).encode()))
                with self.assertRaises(RuntimeError) as result:
                    structured_agent(self.config, 'diagnostico', self.evidence, {}, opener=fail)
                self.assertIn(expected, str(result.exception))
                self.assertNotIn('super-secret-key', str(result.exception))

    def test_network_error_and_url_base_validation(self):
        def fail(*args, **kwargs):
            raise URLError('super-secret-key')
        with self.assertRaisesRegex(RuntimeError, 'conectar') as result:
            structured_agent(self.config, 'diagnostico', self.evidence, {}, opener=fail)
        self.assertNotIn('super-secret-key', str(result.exception))
        with self.assertRaisesRegex(ValueError, 'URL base'):
            AIConfig('https://example.invalid/v1/chat/completions', 'model', 'key', 60, 'test').validate()
