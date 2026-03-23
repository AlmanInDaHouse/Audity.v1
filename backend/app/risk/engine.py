from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from typing import Any

ENGINE_VERSION = 'deterministic-v1'

_SCALE_ALIASES: dict[str, tuple[str, int]] = {
    'very_low': ('very_low', 1),
    'muy_bajo': ('very_low', 1),
    'low': ('low', 2),
    'bajo': ('low', 2),
    'medium': ('medium', 3),
    'medio': ('medium', 3),
    'moderate': ('medium', 3),
    'high': ('high', 4),
    'alto': ('high', 4),
    'very_high': ('very_high', 5),
    'muy_alto': ('very_high', 5),
}
_SCORE_TO_LABEL = {score: label for label, score in _SCALE_ALIASES.values()}

_ZERO_RISK = {'likelihood': 'none', 'impact': 'none', 'score': 0.0, 'level': 'none'}


@dataclass(frozen=True)
class TreatmentInput:
    id: str
    title: str
    decision: str
    status: str
    applies_to: str
    effectiveness_pct: int
    safeguard_id: str | None


def _normalize_scale(value: str | None, *, field_name: str) -> tuple[str, int]:
    if value is None:
        raise ValueError(f'{field_name} is required for deterministic evaluation')
    key = value.strip().lower()
    if not key:
        raise ValueError(f'{field_name} is required for deterministic evaluation')
    normalized = _SCALE_ALIASES.get(key)
    if normalized is None:
        raise ValueError(f'Unsupported {field_name} value: {value}')
    return normalized


def normalize_scale_value(value: str | None, *, field_name: str, required: bool = False) -> str | None:
    if value is None and not required:
        return None
    label, _ = _normalize_scale(value, field_name=field_name)
    return label


def _score_to_level(score: float) -> str:
    if score <= 0:
        return 'none'
    if score <= 4:
        return 'low'
    if score <= 9:
        return 'medium'
    if score <= 16:
        return 'high'
    return 'critical'


def _combine_effectiveness(values: list[float]) -> float:
    if not values:
        return 0.0
    remaining = reduce(lambda current, item: current * (1 - item), values, 1.0)
    return max(0.0, min(1.0, 1 - remaining))


def _scale_from_effect(base_score: int, effectiveness: float) -> tuple[str, int]:
    if effectiveness >= 1.0:
        return 'none', 0
    adjusted = round(base_score * (1 - effectiveness))
    if adjusted <= 0:
        return 'none', 0
    clamped = min(5, max(1, adjusted))
    return _SCORE_TO_LABEL[clamped], clamped


def evaluate_scenario(
    *,
    scenario_id: str,
    likelihood: str | None,
    impact: str | None,
    dimension_values: dict[str, str],
    asset: dict[str, Any] | None,
    threat: dict[str, Any] | None,
    safeguard: dict[str, Any] | None,
    treatments: list[TreatmentInput],
    notes: str = '',
) -> dict[str, Any]:
    inherent_likelihood_label, inherent_likelihood_score = _normalize_scale(
        likelihood,
        field_name='likelihood',
    )

    normalized_dimensions: dict[str, dict[str, Any]] = {}
    dimension_scores: list[int] = []
    for code, raw_value in sorted((dimension_values or {}).items()):
        label, score = _normalize_scale(raw_value, field_name=f'dimension {code}')
        normalized_dimensions[code] = {'label': label, 'score': score}
        dimension_scores.append(score)

    if dimension_scores:
        inherent_impact_score = max(dimension_scores)
        inherent_impact_label = _SCORE_TO_LABEL[inherent_impact_score]
    else:
        inherent_impact_label, inherent_impact_score = _normalize_scale(
            impact,
            field_name='impact',
        )

    inherent_score = float(inherent_likelihood_score * inherent_impact_score)
    inherent_level = _score_to_level(inherent_score)

    applicable = []
    likelihood_effects: list[float] = []
    impact_effects: list[float] = []
    avoid_completed = False
    accepted_ids: list[str] = []
    for item in treatments:
        treatment_row = {
            'id': item.id,
            'title': item.title,
            'decision': item.decision,
            'status': item.status,
            'applies_to': item.applies_to,
            'effectiveness_pct': item.effectiveness_pct,
            'safeguard_id': item.safeguard_id,
        }
        applicable.append(treatment_row)
        if item.decision == 'accept' and item.status == 'accepted':
            accepted_ids.append(item.id)
        if item.decision == 'avoid' and item.status == 'implemented':
            avoid_completed = True
            continue
        if item.status != 'implemented':
            continue
        effectiveness = max(0.0, min(1.0, item.effectiveness_pct / 100))
        if item.decision not in {'mitigate', 'transfer'} or effectiveness <= 0:
            continue
        if item.applies_to in {'likelihood', 'both'}:
            likelihood_effects.append(effectiveness)
        if item.applies_to in {'impact', 'both'}:
            impact_effects.append(effectiveness)

    if avoid_completed:
        residual = dict(_ZERO_RISK)
    else:
        likelihood_effectiveness = _combine_effectiveness(likelihood_effects)
        impact_effectiveness = _combine_effectiveness(impact_effects)
        residual_likelihood_label, residual_likelihood_score = _scale_from_effect(
            inherent_likelihood_score,
            likelihood_effectiveness,
        )
        residual_impact_label, residual_impact_score = _scale_from_effect(
            inherent_impact_score,
            impact_effectiveness,
        )
        residual_score = float(residual_likelihood_score * residual_impact_score)
        residual = {
            'likelihood': residual_likelihood_label,
            'impact': residual_impact_label,
            'score': residual_score,
            'level': _score_to_level(residual_score),
        }

    return {
        'engine_version': ENGINE_VERSION,
        'inherent_likelihood': inherent_likelihood_label,
        'inherent_impact': inherent_impact_label,
        'inherent_score': inherent_score,
        'inherent_level': inherent_level,
        'residual_likelihood': residual['likelihood'],
        'residual_impact': residual['impact'],
        'residual_score': residual['score'],
        'residual_level': residual['level'],
        'input_snapshot_json': {
            'scenario_id': scenario_id,
            'likelihood': likelihood,
            'impact': impact,
            'dimension_values_json': dimension_values or {},
            'asset': asset,
            'threat': threat,
            'safeguard': safeguard,
            'notes': notes,
        },
        'trace_json': {
            'engine_version': ENGINE_VERSION,
            'normalized_dimensions': normalized_dimensions,
            'inherent': {
                'likelihood': {'label': inherent_likelihood_label, 'score': inherent_likelihood_score},
                'impact': {'label': inherent_impact_label, 'score': inherent_impact_score},
                'score': inherent_score,
                'level': inherent_level,
            },
            'residual': residual,
            'treatments': {
                'selected': applicable,
                'accepted_ids': accepted_ids,
                'avoid_completed': avoid_completed,
                'likelihood_effectiveness': _combine_effectiveness(likelihood_effects),
                'impact_effectiveness': _combine_effectiveness(impact_effects),
            },
        },
    }
