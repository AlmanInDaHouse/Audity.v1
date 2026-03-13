from __future__ import annotations

import io
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from app.catalog_engine import ControlDefinition, load_controls
from app.storage import get_object_store

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


@dataclass
class ControlVerdict:
    control_id: str
    title: str
    verdict: str
    confidence: float
    rationale: str
    recommendations: list[str]
    evidence_ids: list[str]


class KnowledgeEngine(Protocol):
    async def evaluate_manual_evidence(self, manual_items: list[dict[str, Any]]) -> dict[str, Any]:
        ...


def _extract_text_from_pdf(data: bytes) -> str:
    if PdfReader is None:
        return ''
    reader = PdfReader(io.BytesIO(data))
    return '\n'.join(page.extract_text() or '' for page in reader.pages[:10])


def _extract_text(name: str, content_type: str, data: bytes) -> str:
    lowered = content_type.lower()
    if lowered.startswith('text/'):
        return data.decode('utf-8', errors='ignore')
    if lowered == 'application/json' or name.lower().endswith('.json'):
        return data.decode('utf-8', errors='ignore')
    if lowered == 'application/pdf' or name.lower().endswith('.pdf'):
        return _extract_text_from_pdf(data)
    return ''


def _truncate_text(value: str, *, limit: int = 5000) -> str:
    compact = ' '.join(value.split())
    return compact[:limit]


def _select_iso_controls(limit: int = 12) -> list[ControlDefinition]:
    return [item for item in load_controls() if item.framework == 'ISO27001'][:limit]


def _heuristic_verdicts(*, controls: list[ControlDefinition], documents: list[dict[str, Any]]) -> list[ControlVerdict]:
    joined = ' '.join(doc['excerpt'].lower() for doc in documents)
    file_names = ' '.join(doc['name'].lower() for doc in documents)
    verdicts: list[ControlVerdict] = []
    for control in controls:
        matched_policy = any(token in joined or token in file_names for token in ('policy', 'proced', 'access', 'acceso', 'backup', 'incident'))
        if matched_policy:
            verdict = 'cumple'
            confidence = 0.63
            rationale = f'Se identifico evidencia documental relevante para {control.id}. Falta validacion humana de vigencia.'
            recommendations = ['Validar aprobacion formal del documento', 'Confirmar revision periodica y responsable']
        else:
            verdict = 'recomendacion'
            confidence = 0.38
            rationale = f'No se encontro evidencia suficiente para {control.id} con el motor heuristico local.'
            recommendations = ['Adjuntar politica o procedimiento firmado', 'Anadir evidencia operativa asociada al control']
        verdicts.append(
            ControlVerdict(
                control_id=control.id,
                title=control.title,
                verdict=verdict,
                confidence=confidence,
                rationale=rationale,
                recommendations=recommendations,
                evidence_ids=[doc['id'] for doc in documents],
            )
        )
    return verdicts


class LocalHeuristicKnowledgeEngine:
    async def evaluate_manual_evidence(self, manual_items: list[dict[str, Any]]) -> dict[str, Any]:
        if not manual_items:
            return {'framework': 'ISO27001', 'generated_at': datetime.now(UTC).isoformat(), 'engine': 'empty', 'assessments': []}

        store = get_object_store()
        documents: list[dict[str, Any]] = []
        for item in manual_items[:4]:
            content_type = str(item.get('content_type') or item.get('metadata', {}).get('content_type') or 'application/octet-stream')
            try:
                raw = await store.get_bytes(item['object_key'])
            except Exception:
                continue
            excerpt = _truncate_text(_extract_text(item['name'], content_type, raw))
            if not excerpt:
                continue
            documents.append(
                {
                    'id': item['id'],
                    'name': item['name'],
                    'content_type': content_type,
                    'excerpt': excerpt,
                }
            )

        if not documents:
            return {'framework': 'ISO27001', 'generated_at': datetime.now(UTC).isoformat(), 'engine': 'empty', 'assessments': []}

        verdicts = _heuristic_verdicts(controls=_select_iso_controls(), documents=documents)
        return {
            'framework': 'ISO27001',
            'generated_at': datetime.now(UTC).isoformat(),
            'engine': 'local_heuristic',
            'documents': documents,
            'assessments': [asdict(item) for item in verdicts],
        }


_knowledge_engine: KnowledgeEngine | None = None


def get_knowledge_engine() -> KnowledgeEngine:
    global _knowledge_engine
    if _knowledge_engine is None:
        _knowledge_engine = LocalHeuristicKnowledgeEngine()
    return _knowledge_engine


async def evaluate_manual_evidence(manual_items: list[dict[str, Any]]) -> dict[str, Any]:
    return await get_knowledge_engine().evaluate_manual_evidence(manual_items)
