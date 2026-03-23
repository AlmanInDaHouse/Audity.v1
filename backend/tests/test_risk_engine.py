from __future__ import annotations

from app.risk.engine import TreatmentInput, evaluate_scenario


def _evaluate(*, treatments: list[TreatmentInput]) -> dict:
    return evaluate_scenario(
        scenario_id='scenario-1',
        likelihood='high',
        impact='very_high',
        dimension_values={},
        asset=None,
        threat=None,
        safeguard=None,
        treatments=treatments,
    )


def test_risk_engine_100_percent_mitigation_can_reduce_to_zero():
    payload = _evaluate(
        treatments=[
            TreatmentInput(
                id='t1',
                title='Full mitigation',
                decision='mitigate',
                status='implemented',
                applies_to='both',
                effectiveness_pct=100,
                safeguard_id=None,
            )
        ]
    )

    assert payload['residual_likelihood'] == 'none'
    assert payload['residual_impact'] == 'none'
    assert payload['residual_score'] == 0.0
    assert payload['residual_level'] == 'none'


def test_risk_engine_100_percent_transfer_can_reduce_impact_to_zero():
    payload = _evaluate(
        treatments=[
            TreatmentInput(
                id='t1',
                title='Full transfer',
                decision='transfer',
                status='implemented',
                applies_to='impact',
                effectiveness_pct=100,
                safeguard_id=None,
            )
        ]
    )

    assert payload['residual_likelihood'] == 'high'
    assert payload['residual_impact'] == 'none'
    assert payload['residual_score'] == 0.0
    assert payload['residual_level'] == 'none'


def test_risk_engine_avoid_sets_zero_risk():
    payload = _evaluate(
        treatments=[
            TreatmentInput(
                id='t1',
                title='Avoid scenario',
                decision='avoid',
                status='implemented',
                applies_to='none',
                effectiveness_pct=0,
                safeguard_id=None,
            )
        ]
    )

    assert payload['residual_likelihood'] == 'none'
    assert payload['residual_impact'] == 'none'
    assert payload['residual_score'] == 0.0
    assert payload['residual_level'] == 'none'


def test_risk_engine_combines_treatments_multiplicatively():
    payload = _evaluate(
        treatments=[
            TreatmentInput(
                id='t1',
                title='Reduce likelihood',
                decision='mitigate',
                status='implemented',
                applies_to='likelihood',
                effectiveness_pct=50,
                safeguard_id=None,
            ),
            TreatmentInput(
                id='t2',
                title='Reduce impact',
                decision='transfer',
                status='implemented',
                applies_to='impact',
                effectiveness_pct=50,
                safeguard_id=None,
            ),
        ]
    )

    assert payload['inherent_score'] == 20.0
    assert payload['residual_likelihood'] == 'low'
    assert payload['residual_impact'] == 'low'
    assert payload['residual_score'] == 4.0
    assert payload['residual_level'] == 'low'
