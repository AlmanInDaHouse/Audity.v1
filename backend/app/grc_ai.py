from __future__ import annotations

import io
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from app.catalog_engine import ControlDefinition, load_controls
from app.config import get_settings
from app.storage import get_object_store

try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
except Exception:
    ChatPromptTemplate = None
    ChatOpenAI = None

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


RESULT_MAP = {
    'cumple': 'pass',
    'no cumple': 'fail',
    'recomendacion': 'partial',
    'recomendación': 'partial',
    'pass': 'pass',
    'fail': 'fail',
    'partial': 'partial',
}

GROQ_BASE_URL = 'https://api.groq.com/openai/v1'
GROQ_DEFAULT_MODEL = 'llama-3.3-70b-versatile'
ASSISTANT_MESSAGE_LIMIT = 1800
ASSISTANT_HISTORY_LIMIT = 10


@dataclass
class ControlVerdict:
    control_id: str
    title: str
    verdict: str
    confidence: float
    rationale: str
    recommendations: list[str]
    evidence_ids: list[str]

    def as_control_result(self, framework: str, severity: str) -> dict[str, Any]:
        return {
            'control_id': self.control_id,
            'title': self.title,
            'framework': framework,
            'severity': severity,
            'result': RESULT_MAP.get(self.verdict.lower(), 'partial'),
            'confidence': self.confidence,
            'notes': self.rationale,
            'evidence_refs': self.evidence_ids,
        }


def _truncate_text(value: str, *, limit: int = 5000) -> str:
    compact = ' '.join(value.split())
    return compact[:limit]


def _resolve_llm_base_url() -> str:
    settings = get_settings()
    if settings.llm_base_url:
        return settings.llm_base_url.rstrip('/')
    if settings.llm_provider == 'groq':
        return GROQ_BASE_URL
    return ''


def _resolve_llm_model() -> str:
    settings = get_settings()
    if settings.llm_model:
        return settings.llm_model
    if settings.llm_provider == 'groq':
        return GROQ_DEFAULT_MODEL
    return ''


def _resolve_llm_api_key() -> str:
    settings = get_settings()
    if settings.llm_api_key:
        return settings.llm_api_key
    if settings.llm_provider == 'groq':
        return settings.groq_api_key
    return ''


def _extract_text_from_pdf(data: bytes) -> str:
    if PdfReader is None:
        return ''
    reader = PdfReader(io.BytesIO(data))
    return '\n'.join(page.extract_text() or '' for page in reader.pages[:10])


def _extract_text(name: str, content_type: str, data: bytes) -> str:
    lowered = content_type.lower()
    if lowered.startswith('text/'):
        return data.decode('utf-8', errors='ignore')
    if lowered == 'application/json':
        return data.decode('utf-8', errors='ignore')
    if lowered == 'application/pdf':
        return _extract_text_from_pdf(data)
    if name.lower().endswith('.json'):
        return data.decode('utf-8', errors='ignore')
    if name.lower().endswith('.pdf'):
        return _extract_text_from_pdf(data)
    return ''


def _select_iso_controls(limit: int = 12) -> list[ControlDefinition]:
    iso_controls = [item for item in load_controls() if item.framework == 'ISO27001']
    return iso_controls[:limit]


def _heuristic_verdicts(
    *,
    controls: list[ControlDefinition],
    documents: list[dict[str, Any]],
) -> list[ControlVerdict]:
    joined = ' '.join(doc['excerpt'].lower() for doc in documents)
    file_names = ' '.join(doc['name'].lower() for doc in documents)
    verdicts: list[ControlVerdict] = []
    for control in controls:
        matched_policy = any(token in joined or token in file_names for token in ('policy', 'proced', 'acceso', 'access'))
        if matched_policy:
            verdict = 'cumple'
            confidence = 0.63
            rationale = f'Evidencia documental encontrada para {control.id}. Revisar aprobación y vigencia.'
            recommendations = ['Validar firma/aprobación del documento', 'Confirmar periodicidad de revisión']
        else:
            verdict = 'recomendacion'
            confidence = 0.38
            rationale = f'No se pudo correlacionar evidencia suficiente para {control.id} con el motor heurístico.'
            recommendations = ['Subir políticas o procedimientos firmados', 'Adjuntar evidencia operativa asociada al control']
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


async def _invoke_openai_compatible(prompt: str) -> str:
    settings = get_settings()
    base_url = _resolve_llm_base_url()
    model = _resolve_llm_model()
    api_key = _resolve_llm_api_key()
    if not base_url or not model:
        raise RuntimeError('LLM endpoint not configured')

    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    payload = {
        'model': model,
        'temperature': 0.1,
        'response_format': {'type': 'json_object'},
        'messages': [
            {
                'role': 'system',
                'content': (
                    'You are a senior GRC auditor. Respond only with JSON matching '
                    '{"assessments":[{"control_id":"","verdict":"","confidence":0.0,'
                    '"rationale":"","recommendations":[""],"evidence_ids":[""]}]}.'
                ),
            },
            {'role': 'user', 'content': prompt},
        ],
    }
    async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
        response = await client.post(f'{base_url}/chat/completions', headers=headers, json=payload)
        response.raise_for_status()
    body = response.json()
    return str(body['choices'][0]['message']['content'])


async def _invoke_openai_compatible_messages(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
) -> dict[str, str]:
    settings = get_settings()
    base_url = _resolve_llm_base_url()
    model = _resolve_llm_model()
    api_key = _resolve_llm_api_key()
    if not base_url or not model or not api_key:
        raise RuntimeError('Assistant LLM endpoint not configured')

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    }
    payload = {
        'model': model,
        'temperature': temperature,
        'messages': messages,
    }
    async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
        response = await client.post(f'{base_url}/chat/completions', headers=headers, json=payload)
        response.raise_for_status()
    body = response.json()
    return {
        'reply': str(body['choices'][0]['message']['content']).strip(),
        'model': str(body.get('model') or model),
    }


async def _invoke_langchain(prompt: str) -> str:
    settings = get_settings()
    if ChatPromptTemplate is None or ChatOpenAI is None:
        raise RuntimeError('LangChain runtime unavailable')
    model = _resolve_llm_model()
    base_url = _resolve_llm_base_url()
    api_key = _resolve_llm_api_key()
    if not model or not base_url:
        raise RuntimeError('LLM endpoint not configured')

    prompt_template = ChatPromptTemplate.from_messages(
        [
            ('system', 'Eres un auditor GRC senior. Devuelve exclusivamente JSON válido.'),
            ('human', '{prompt}'),
        ]
    )
    llm = ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key or 'not-needed',
        temperature=0.1,
        timeout=settings.llm_timeout_seconds,
    )
    chain = prompt_template | llm
    response = await chain.ainvoke({'prompt': prompt})
    return str(response.content)


def _build_prompt(controls: list[ControlDefinition], documents: list[dict[str, Any]]) -> str:
    controls_payload = [
        {
            'control_id': control.id,
            'title': control.title,
            'description': control.description,
            'severity': control.severity,
            'evidence_requirements': control.evidence_requirements,
        }
        for control in controls
    ]
    return json.dumps(
        {
            'framework': 'ISO27001',
            'task': (
                'Cruza la evidencia contra los controles y responde por control con verdict '
                'Cumple, No Cumple o Recomendacion.'
            ),
            'controls': controls_payload,
            'documents': documents,
        },
        ensure_ascii=False,
    )


def _build_dashboard_snapshot(organization_name: str, dashboard: dict[str, Any]) -> str:
    readiness_items = [
        f"- {item['label']}: {'ready' if item['ready'] else 'needs work'} ({item['detail']})"
        for item in dashboard['readiness']['items']
    ]
    recent_runs = [
        f"- {item['project_name']}: status={item['status']}, risk={item['risk_level'] or 'n/a'}, score={item['risk_score']}"
        for item in dashboard['recent_runs'][:4]
    ]
    return '\n'.join(
        [
            f'Organization: {organization_name}',
            'Executive metrics:',
            f"- Readiness score: {dashboard['readiness']['score']}%",
            f"- Audit coverage: {dashboard['summary']['audit_coverage_pct']}%",
            f"- Automation coverage: {dashboard['summary']['automation_coverage_pct']}%",
            f"- Evidence hygiene: {dashboard['summary']['evidence_hygiene_pct']}%",
            f"- Open findings: {dashboard['summary']['open_findings']}",
            f"- Critical findings: {dashboard['summary']['critical_findings']}",
            f"- Overdue tasks: {dashboard['summary']['overdue_tasks']}",
            f"- Active audit runs: {dashboard['summary']['active_runs']}",
            f"- Evidence items: {dashboard['summary']['evidence_total']}",
            'Plan status:',
            f"- Plan: {dashboard['plan']['plan_code']}",
            f"- Assets used: {dashboard['plan']['assets_used']}/{dashboard['plan']['max_assets']}",
            f"- Modules enabled: {', '.join(dashboard['plan']['modules_enabled']) or 'none'}",
            'Readiness checklist:',
            *readiness_items,
            'Recent audit runs:',
            *(recent_runs or ['- No recent runs']),
        ]
    )


def _sanitize_assistant_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    sanitized: list[dict[str, str]] = []
    for item in messages[-ASSISTANT_HISTORY_LIMIT:]:
        role = str(item.get('role') or '').strip().lower()
        if role not in {'user', 'assistant'}:
            continue
        content = _truncate_text(str(item.get('content') or ''), limit=ASSISTANT_MESSAGE_LIMIT)
        if not content:
            continue
        sanitized.append({'role': role, 'content': content})
    return sanitized


async def chat_with_dashboard_assistant(
    *,
    organization_name: str,
    dashboard: dict[str, Any],
    messages: list[dict[str, str]],
) -> dict[str, str]:
    sanitized = _sanitize_assistant_messages(messages)
    if not sanitized:
        raise RuntimeError('No user message provided')

    settings = get_settings()
    snapshot = _build_dashboard_snapshot(organization_name, dashboard)
    response = await _invoke_openai_compatible_messages(
        [
            {
                'role': 'system',
                'content': (
                    'You are Audity Copilot, an executive compliance assistant for an audit dashboard. '
                    'Answer in Spanish unless the user writes in another language. '
                    'Be concise, practical, and specific. Base your answer on the dashboard snapshot below. '
                    'If the snapshot is insufficient, say so clearly and give the next best action. '
                    'Do not invent metrics, projects, or security states.\n\n'
                    f'{snapshot}'
                ),
            },
            *sanitized,
        ],
        temperature=0.25,
    )
    return {
        'reply': response['reply'],
        'provider': settings.llm_provider or 'openai_compatible',
        'model': response['model'],
        'generated_at': datetime.now(UTC).isoformat(),
    }


async def evaluate_manual_evidence(manual_items: list[dict[str, Any]]) -> dict[str, Any]:
    settings = get_settings()
    if not settings.ai_evaluator_enabled or not manual_items:
        return {'engine': 'disabled', 'assessments': []}

    store = get_object_store()
    documents: list[dict[str, Any]] = []
    for item in manual_items[: settings.llm_max_manual_evidence]:
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
        return {'engine': 'empty', 'assessments': []}

    controls = _select_iso_controls()
    prompt = _build_prompt(controls, documents)
    engine = 'heuristic'
    verdicts: list[ControlVerdict]
    try:
        if ChatPromptTemplate is not None and ChatOpenAI is not None:
            raw = await _invoke_langchain(prompt)
            engine = 'langchain'
        else:
            raw = await _invoke_openai_compatible(prompt)
            engine = 'openai_compatible'
        parsed = json.loads(raw)
        index = {control.id: control for control in controls}
        verdicts = []
        for item in parsed.get('assessments', []):
            control = index.get(item.get('control_id', ''))
            if control is None:
                continue
            verdicts.append(
                ControlVerdict(
                    control_id=control.id,
                    title=control.title,
                    verdict=str(item.get('verdict', 'Recomendacion')),
                    confidence=max(0.0, min(float(item.get('confidence', 0.5)), 1.0)),
                    rationale=str(item.get('rationale', '')),
                    recommendations=[str(value) for value in item.get('recommendations', [])[:5]],
                    evidence_ids=[str(value) for value in item.get('evidence_ids', [])[:10]] or [doc['id'] for doc in documents],
                )
            )
        if not verdicts:
            raise ValueError('No assessments returned by LLM')
    except Exception:
        verdicts = _heuristic_verdicts(controls=controls, documents=documents)

    return {
        'framework': 'ISO27001',
        'generated_at': datetime.now(UTC).isoformat(),
        'engine': engine,
        'documents': documents,
        'assessments': [asdict(item) for item in verdicts],
    }
