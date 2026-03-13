from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

try:
    from weasyprint import HTML
except Exception:
    HTML = None


def render_report_html(context: dict[str, Any]) -> str:
    template_dir = Path(__file__).resolve().parent / 'templates'
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(['html', 'xml']),
    )
    template = env.get_template('report.html.j2')
    return template.render(**context)


def render_report_pdf(html: str) -> bytes:
    if HTML is None:
        raise RuntimeError('WeasyPrint runtime is unavailable. Install production PDF dependencies before generating reports.')
    return HTML(string=html).write_pdf()
