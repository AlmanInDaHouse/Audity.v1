from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from app.config import get_settings

SUPPORTED_FRAMEWORKS = ('ISO27001', 'ENS', 'RGPD')


@dataclass
class ControlDefinition:
    id: str
    framework: str
    title: str
    description: str
    severity: str
    mapped_controls: list[str]
    evidence_requirements: list[str]
    evaluator_key: str
    tags: list[str]
    level: str


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        content = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        # why this: Windows editors may save YAML in latin-1/cp1252 during local setup.
        content = path.read_text(encoding='latin-1')
    return yaml.safe_load(content)


def catalog_files() -> dict[str, Path]:
    base = Path(get_settings().catalog_dir)
    return {
        'iso': base / 'iso27001_annex_a.v1.yml',
        'ens': base / 'ens_measures.v1.yml',
        'rgpd': base / 'rgpd_checklist.v1.yml',
        'mapping': base / 'control_mapping.v1.yml',
    }


def compute_catalog_checksum() -> str:
    digest = hashlib.sha256()
    for _, file_path in sorted(catalog_files().items()):
        digest.update(file_path.read_bytes())
    return digest.hexdigest()


def compute_bundle_checksum(bundle: dict[str, Any]) -> str:
    payload = {key: value for key, value in bundle.items() if key != 'checksum'}
    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(serialized).hexdigest()


def default_framework_scope() -> list[str]:
    return list(SUPPORTED_FRAMEWORKS)


def normalize_framework_scope(frameworks: list[str] | None) -> list[str]:
    if not frameworks:
        return default_framework_scope()

    normalized: list[str] = []
    seen: set[str] = set()
    for raw in frameworks:
        value = str(raw).strip()
        if value not in SUPPORTED_FRAMEWORKS:
            raise ValueError(f'Unsupported framework: {value}')
        if value in seen:
            continue
        seen.add(value)
        normalized.append(value)

    if not normalized:
        raise ValueError('At least one framework is required')
    return normalized


def load_controls() -> list[ControlDefinition]:
    files = catalog_files()

    iso = _read_yaml(files['iso'])
    ens = _read_yaml(files['ens'])
    rgpd = _read_yaml(files['rgpd'])

    controls: list[ControlDefinition] = []
    for item in iso.get('controls', []):
        controls.append(
            ControlDefinition(
                id=item['id'],
                framework='ISO27001',
                title=item['title'],
                description=item['description'],
                severity=item.get('severity', 'medium'),
                mapped_controls=item.get('mapped_controls', []),
                evidence_requirements=item.get('evidence_requirements', []),
                evaluator_key=item.get('evaluator_key', 'fallback'),
                tags=item.get('tags', []),
                level=item.get('level', 'base'),
            )
        )

    for item in ens.get('measures', []):
        controls.append(
            ControlDefinition(
                id=item['id'],
                framework='ENS',
                title=item['title'],
                description=item['description'],
                severity=item.get('severity', 'medium'),
                mapped_controls=item.get('mapped_controls', []),
                evidence_requirements=item.get('evidence_requirements', []),
                evaluator_key=item.get('evaluator_key', 'fallback'),
                tags=item.get('tags', []),
                level=item.get('level', 'base'),
            )
        )

    for item in rgpd.get('checklist', []):
        control_id = f"RGPD-{item['article_or_principle']}"
        controls.append(
            ControlDefinition(
                id=control_id,
                framework='RGPD',
                title=item['question'],
                description=item.get('expected_evidence', ''),
                severity=item.get('severity', 'medium'),
                mapped_controls=item.get('mapped_controls', []),
                evidence_requirements=item.get('evidence_requirements', []),
                evaluator_key=item.get('evaluator_key', 'fallback'),
                tags=item.get('tags', []),
                level='base',
            )
        )

    return controls


def load_mapping() -> dict[str, list[str]]:
    mapping = _read_yaml(catalog_files()['mapping'])
    out: dict[str, list[str]] = {}
    for item in mapping.get('mappings', []):
        out[item['control_id']] = item.get('requirement_refs', [])
    return out


def control_to_dict(control: ControlDefinition) -> dict[str, Any]:
    return asdict(control)


def control_from_dict(payload: dict[str, Any]) -> ControlDefinition:
    return ControlDefinition(
        id=str(payload['id']),
        framework=str(payload['framework']),
        title=str(payload['title']),
        description=str(payload['description']),
        severity=str(payload.get('severity', 'medium')),
        mapped_controls=[str(item) for item in payload.get('mapped_controls', [])],
        evidence_requirements=[str(item) for item in payload.get('evidence_requirements', [])],
        evaluator_key=str(payload.get('evaluator_key', 'fallback')),
        tags=[str(item) for item in payload.get('tags', [])],
        level=str(payload.get('level', 'base')),
    )


def build_catalog_snapshot(frameworks: list[str] | None, *, version: str = 'v1') -> dict[str, Any]:
    scope = normalize_framework_scope(frameworks)
    controls = [item for item in load_controls() if item.framework in scope]
    mapping = load_mapping()
    included_control_ids = {item.id for item in controls}
    filtered_mapping = {
        control_id: requirement_refs
        for control_id, requirement_refs in mapping.items()
        if control_id in included_control_ids
    }
    return {
        'version': version,
        'checksum': compute_catalog_checksum(),
        'frameworks': scope,
        'controls': [control_to_dict(item) for item in controls],
        'control_mapping': filtered_mapping,
    }


def build_catalog_bundle(frameworks: list[str] | None, *, version: str = 'v1') -> dict[str, Any]:
    bundle = build_catalog_snapshot(frameworks, version=version)
    bundle['checksum'] = compute_bundle_checksum(bundle)
    return bundle


def validate_catalog_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(bundle, dict):
        raise ValueError('Catalog bundle must be a JSON object')

    version = str(bundle.get('version') or 'v1').strip() or 'v1'
    frameworks = normalize_framework_scope(bundle.get('frameworks'))
    controls = load_controls_from_snapshot(bundle)
    control_mapping = bundle.get('control_mapping', {})
    if not isinstance(control_mapping, dict):
        raise ValueError('Catalog bundle control_mapping must be an object')

    from app.rules import EVALUATORS

    normalized_controls: list[dict[str, Any]] = []
    for control in controls:
        if control.framework not in SUPPORTED_FRAMEWORKS:
            raise ValueError(f'Unsupported control framework: {control.framework}')
        if control.framework not in frameworks:
            raise ValueError(f'Control {control.id} framework {control.framework} is outside bundle scope')
        if control.evaluator_key not in EVALUATORS:
            raise ValueError(f'Unknown evaluator_key: {control.evaluator_key}')
        normalized_controls.append(control_to_dict(control))

    normalized_mapping: dict[str, list[str]] = {}
    for control_id, requirement_refs in control_mapping.items():
        if not isinstance(requirement_refs, list):
            raise ValueError(f'Catalog bundle control_mapping for {control_id} must be a list')
        normalized_mapping[str(control_id)] = [str(item) for item in requirement_refs]

    normalized_bundle = {
        'version': version,
        'frameworks': frameworks,
        'controls': normalized_controls,
        'control_mapping': normalized_mapping,
    }
    normalized_bundle['checksum'] = compute_bundle_checksum(normalized_bundle)
    return normalized_bundle


def build_catalog_snapshot_from_bundle(bundle: dict[str, Any], frameworks: list[str] | None) -> dict[str, Any]:
    validated_bundle = validate_catalog_bundle(bundle)
    scope = normalize_framework_scope(frameworks)
    controls = [item for item in validated_bundle['controls'] if item['framework'] in scope]
    included_control_ids = {item['id'] for item in controls}
    filtered_mapping = {
        control_id: requirement_refs
        for control_id, requirement_refs in validated_bundle['control_mapping'].items()
        if control_id in included_control_ids
    }
    return {
        'version': validated_bundle['version'],
        'checksum': validated_bundle['checksum'],
        'frameworks': scope,
        'controls': controls,
        'control_mapping': filtered_mapping,
    }


def load_controls_from_snapshot(snapshot: dict[str, Any] | None) -> list[ControlDefinition]:
    if not snapshot:
        return load_controls()
    if not isinstance(snapshot, dict):
        raise ValueError('Catalog snapshot must be a JSON object')
    controls = snapshot.get('controls', [])
    if not isinstance(controls, list):
        raise ValueError('Catalog snapshot controls must be a list')

    parsed_controls: list[ControlDefinition] = []
    for item in controls:
        if not isinstance(item, dict):
            raise ValueError('Catalog snapshot controls must contain objects')
        parsed_controls.append(control_from_dict(item))
    return parsed_controls
