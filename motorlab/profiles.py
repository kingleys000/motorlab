"""Identidad y procedencia de perfiles, sin atribuir datos al motor del usuario."""
from dataclasses import dataclass, fields
import json
import math
from types import MappingProxyType
from .model import Parameters

@dataclass(frozen=True)
class Profile:
    identifier: str
    version: str
    identity: str
    status: str
    source: str
    parameters: Parameters

    def __post_init__(self):
        if self.status not in ('didactico', 'catalogo', 'calibrado', 'validado'):
            raise ValueError('Estado de perfil desconocido')
        if not all((self.identifier, self.version, self.identity, self.source)):
            raise ValueError('Identidad, versión y fuente son obligatorias')

LEGACY = Profile('legacy-dc', '1', 'Motor DC didáctico sin fabricante', 'didactico',
                 'Parámetros didácticos heredados de MotorLab; no son datos de catálogo', Parameters())
PROFILES = MappingProxyType({LEGACY.identifier: LEGACY})


def load_profile(path):
    """Carga un perfil JSON explícito; cargar catálogo no implica calibración."""
    with open(path, encoding='utf-8') as stream:
        obj = json.load(stream)
    if not isinstance(obj, dict) or not isinstance(obj.get('parameters'), dict):
        raise ValueError('El perfil debe ser un objeto JSON con parámetros.')
    names = {field.name for field in fields(Parameters)}
    raw = obj.get('parameters', {})
    if set(raw) != names:
        raise ValueError('El perfil debe contener todos los parámetros SI explícitos.')
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for v in raw.values()):
        raise ValueError('Parámetros deben ser números finitos.')
    for key in ('resistance', 'inductance', 'torque_constant', 'inertia', 'thermal_capacity'):
        if raw[key] <= 0:
            raise ValueError(f'{key} debe ser positivo.')
    if raw['friction'] < 0 or raw['copper_alpha'] < 0:
        raise ValueError('Fricción y coeficiente térmico no pueden ser negativos.')
    try:
        return Profile(obj['identifier'], obj['version'], obj['identity'], obj['status'], obj['source'], Parameters(**raw))
    except (KeyError, TypeError) as exc:
        raise ValueError('Perfil incompleto.') from exc
