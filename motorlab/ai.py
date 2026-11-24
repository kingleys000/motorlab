"""Asesor opcional: solo evidencia seleccionada, sin acceso a herramientas."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json
import os
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='motorlab-ai')

@dataclass(frozen=True)
class AIConfig:
    base_url: str = ''
    model: str = ''
    api_key: str = ''
    timeout: float = 60.0
    provider: str = ''

    @classmethod
    def from_env(cls):
        return cls(os.getenv('MOTORLAB_AI_BASE_URL', ''), os.getenv('MOTORLAB_AI_MODEL', ''),
                   os.getenv('MOTORLAB_AI_API_KEY', ''), provider=os.getenv('MOTORLAB_AI_PROVIDER', ''))

    def validate(self):
        url = urlparse(self.base_url)
        if not self.provider or not self.model or not self.api_key or url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.query or url.fragment or self.timeout <= 0:
            raise ValueError('Asesor IA deshabilitado: configura proveedor, URL, modelo y credencial.')
        if url.path.rstrip('/').endswith('/chat/completions'):
            raise ValueError('La URL base no debe terminar en /chat/completions; MotorLab añade esa ruta.')


def advise(config, evidence, opener=urlopen):
    """Devuelve texto no verificado; el cliente debe contrastarlo con las evidencias."""
    config.validate()
    if not isinstance(evidence, list) or not evidence or len(evidence) > 20:
        raise ValueError('Selecciona entre 1 y 20 evidencias.')
    ids = [item.get('id') for item in evidence if isinstance(item, dict)]
    if len(ids) != len(evidence) or any(not isinstance(x, str) or not x for x in ids):
        raise ValueError('Cada evidencia requiere un id.')
    payload = {'model': config.model, 'messages': [
        {'role': 'system', 'content': 'Actúa como asesor de diagnóstico y mantenimiento. Usa únicamente las evidencias suministradas y cita sus IDs. Indica límites e incertidumbre; no inventes porcentajes ni RUL. No tienes herramientas de control.'},
        {'role': 'user', 'content': json.dumps(evidence, ensure_ascii=False, allow_nan=False)}]}
    request = Request(config.base_url.rstrip('/') + '/chat/completions', data=json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + config.api_key}, method='POST')
    try:
        with opener(request, timeout=config.timeout) as response:
            content = json.loads(response.read())['choices'][0]['message']['content']
        if not isinstance(content, str) or not any(identifier in content for identifier in ids):
            raise ValueError('Respuesta sin referencias a evidencias')
        return content
    except Exception as exc:
        raise RuntimeError('Asesor IA no disponible o respuesta inválida.') from exc


def advise_async(config, evidence):
    return _executor.submit(advise, config, evidence)


# Componentes del modelo ilustrativo; no son afirmaciones de daño físico.
COMPONENTS = frozenset(('motor', 'bobinado', 'rotor_eje', 'carcasa', 'estator',
                        'escobillas', 'conmutador', 'rodamientos'))


def _http_error_message(error):
    """Clasifica el error sin mostrar el cuerpo ni información de la solicitud."""
    code = error.code
    if code == 400:
        try:
            payload = json.loads(error.read(65536))
            entries = payload if isinstance(payload, list) else [payload]
            errors = [entry.get('error', {}) for entry in entries if isinstance(entry, dict)]
            for item in errors:
                if not isinstance(item, dict):
                    continue
                description = item.get('message', '')
                details = item.get('details', [])
                invalid_message = isinstance(description, str) and 'please pass a valid api key' in description.lower()
                invalid_reason = isinstance(details, list) and any(
                    isinstance(detail, dict) and detail.get('reason') == 'API_KEY_INVALID' for detail in details)
                if invalid_message or invalid_reason:
                    return 'El proveedor rechazó la clave API (HTTP 400). Revisa la clave configurada.'
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        return 'El proveedor rechazó la solicitud (HTTP 400). Revisa la clave, el modelo y la URL base.'
    if code == 401:
        return 'El proveedor rechazó la autenticación (HTTP 401). Revisa la clave API.'
    if code == 403:
        return 'Acceso denegado por el proveedor (HTTP 403). Revisa permisos, proyecto y clave API.'
    if code == 404:
        return 'No se encontró el modelo o la dirección API (HTTP 404). Revisa el modelo y la URL base.'
    if code == 429:
        return 'El proveedor alcanzó un límite de cuota o solicitudes (HTTP 429). Revisa la cuota y reintenta más tarde.'
    if 500 <= code <= 599:
        return f'El servicio del proveedor falló temporalmente (HTTP {code}). Reintenta más tarde.'
    return f'El proveedor rechazó la solicitud (HTTP {code}). Revisa la configuración.'


def _validate_items(result, role, evidence_ids):
    """Valida el contrato y todas las referencias; rechaza campos adicionales."""
    key = 'hipotesis' if role == 'diagnostico' else 'hallazgos'
    if not isinstance(result, dict) or set(result) != {key} or not isinstance(result[key], list) or not result[key]:
        raise ValueError('Estructura JSON inválida.')
    required = ({'explicacion', 'alternativas', 'comprobaciones', 'evidencias', 'componentes'}
                if role == 'diagnostico' else {'conclusion', 'estado', 'evidencias', 'componentes'})
    for item in result[key]:
        if not isinstance(item, dict) or set(item) != required:
            raise ValueError('Campos JSON inválidos.')
        text_fields = ('explicacion', 'alternativas', 'comprobaciones') if role == 'diagnostico' else ('conclusion',)
        if any(not isinstance(item[f], str) or not item[f].strip() for f in text_fields):
            raise ValueError('Texto de análisis inválido.')
        for field in text_fields:
            text = item[field]
            if (re.search(r'\d\s*%', text) or
                    re.search(r'(?i)(probabilidad|vida\s+[úu]til|rul)[^.!?\n]{0,60}\d', text)):
                raise ValueError('No se permiten probabilidades ni vida útil estimadas.')
        if role == 'revision' and item['estado'] not in ('sustentada', 'insuficiente', 'contradictoria'):
            raise ValueError('Estado de revisión inválido.')
        for field, allowed in (('evidencias', evidence_ids), ('componentes', COMPONENTS)):
            refs = item[field]
            if not isinstance(refs, list) or not refs or any(not isinstance(x, str) or x not in allowed for x in refs):
                raise ValueError('Referencia inexistente en ' + field + '.')
    return result


def structured_agent(config, role, evidence, context, proposal=None, opener=urlopen):
    """Consulta un agente compatible con Chat Completions y valida su JSON."""
    config.validate()
    if role not in ('diagnostico', 'revision') or not isinstance(evidence, list) or not evidence:
        raise ValueError('Evidencias o rol inválidos.')
    ids = [e.get('id') for e in evidence if isinstance(e, dict)]
    if len(ids) != len(evidence) or any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('IDs de evidencia inválidos.')
    if role == 'revision':
        _validate_items(proposal, 'diagnostico', set(ids))
    schema = ("{\"hipotesis\":[{\"explicacion\":\"texto\",\"alternativas\":\"texto\",\"comprobaciones\":\"texto\",\"evidencias\":[\"id\"],\"componentes\":[\"motor\"]}]}"
              if role == 'diagnostico' else
              "{\"hallazgos\":[{\"conclusion\":\"texto\",\"estado\":\"sustentada|insuficiente|contradictoria\",\"evidencias\":[\"id\"],\"componentes\":[\"motor\"]}]}")
    system = ('Eres agente de ' + role + '. Devuelve exclusivamente JSON según este esquema: ' + schema +
              '. Usa solo IDs de evidencias y componentes del catálogo. Distingue observaciones de hipótesis; '
              'no declares fallas físicas confirmadas ni inventes probabilidades o vida útil. '
              'Una revisión es una evaluación de la propuesta, no confirmación física.')
    data = {'evidencias': evidence, 'contexto': context, 'catalogo_componentes': sorted(COMPONENTS)}
    if proposal is not None:
        data['propuesta'] = proposal
    payload = {'model': config.model, 'messages': [{'role': 'system', 'content': system},
              {'role': 'user', 'content': json.dumps(data, ensure_ascii=False, allow_nan=False)}],
              'response_format': {'type': 'json_object'}}
    request = Request(config.base_url.rstrip('/') + '/chat/completions', data=json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + config.api_key}, method='POST')
    try:
        with opener(request, timeout=config.timeout) as response:
            content = json.loads(response.read())['choices'][0]['message']['content']
        if config.api_key in content:
            raise ValueError('Respuesta contiene credencial.')
        return _validate_items(json.loads(content), role, set(ids))
    except HTTPError as exc:
        try:
            message = _http_error_message(exc)
        finally:
            exc.close()
        raise RuntimeError(message) from None
    except URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            raise RuntimeError('Tiempo de espera agotado al consultar el proveedor.') from None
        raise RuntimeError('No se pudo conectar con el proveedor. Revisa la conexión y la URL base.') from None
    except TimeoutError:
        raise RuntimeError('Tiempo de espera agotado al consultar el proveedor.') from None
    except (ValueError, KeyError, IndexError, TypeError):
        raise RuntimeError('Respuesta JSON inválida o con referencias no permitidas.') from None
    except Exception:
        # Los errores del proveedor pueden contener credenciales o contenido privado.
        raise RuntimeError('Proveedor no disponible.') from None


def run_agents(config, evidence, context, opener=urlopen):
    """Ejecuta secuencialmente; conserva propuesta si la revisión falla."""
    proposal = structured_agent(config, 'diagnostico', evidence, context, opener=opener)
    try:
        review = structured_agent(config, 'revision', evidence, context, proposal, opener=opener)
        return {'propuesta': proposal, 'revision': review, 'error_revision': None}
    except RuntimeError as exc:
        return {'propuesta': proposal, 'revision': None, 'error_revision': str(exc) + ' Propuesta sin revisión.'}


def run_agents_async(config, evidence, context):
    return _executor.submit(run_agents, config, evidence, context)
