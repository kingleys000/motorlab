"""Evaluación reproducible del corpus distribuido; no consulta IA."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from motorlab.calibration import calibrate, compare
from motorlab.diagnostics import Limits, detect_episodes
from motorlab.evaluation import evaluate_episodes
from motorlab.experiments import read_experiment


def main():
    root = ROOT / 'examples'
    training = read_experiment(root / 'ajuste_saludable_sintetico.csv')
    validation = read_experiment(root / 'validacion_saludable_sintetica.csv')
    calibration = calibrate(training, validation, steady_state=True)
    limits = Limits(current_max=3, temperature_max=40, voltage_residual_max=.5,
                    persistence_s=1, clear_s=.5)
    cases = {'saludable': ('evaluacion_saludable_sintetica', 'evaluacion_saludable'),
             'sobrecorriente': ('sobrecorriente', 'sobrecorriente'),
             'temperatura': ('temperatura', 'temperatura'),
             'residual': ('residual_estacionario', 'residual_estacionario'),
             'combinada': ('combinada', 'combinada'), 'pico_breve': ('pico_breve', 'pico_breve')}
    results = {}
    for name, (data_name, labels_name) in cases.items():
        rows = read_experiment(root / (data_name + '.csv'))
        prediction = [item['predicted_voltage'] for item in compare(rows, calibration.parameters)]
        episodes = detect_episodes(rows, limits, predicted_voltages=prediction,
                                   steady_state=True, calibration=calibration)
        labels = json.loads((root / 'labels' / (labels_name + '.json')).read_text(encoding='utf-8'))
        results[name] = evaluate_episodes(episodes, labels)
    print(json.dumps({'limites': {'corriente_A': 3, 'temperatura_C': 40, 'residual_V': .5,
                                'persistencia_s': 1, 'limpieza_s': .5},
                      'calibracion': {'rmse_validacion_V': calibration.validation_rmse_v},
                      'resultados': results}, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
