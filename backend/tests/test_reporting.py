import io

import pytest

from app.reporting import HTML, render_report_html, render_report_pdf

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


def test_pdf_generation_has_pdf_header():
    if HTML is None:
        pytest.skip('WeasyPrint runtime unavailable in local interpreter')
    html = render_report_html(
        {
            'audit_run_id': 'run-1',
            'project_name': 'Project',
            'org_name': 'Org',
            'risk_score': 42,
            'risk_level': 'medium',
            'total_controls': 3,
            'findings': [],
            'remediation_tasks': [],
        }
    )
    pdf = render_report_pdf(html)
    assert html.startswith('<!doctype html>') or '<html' in html.lower()
    assert pdf.startswith(b'%PDF')
    assert len(pdf) > 1024
    if PdfReader is not None:
        reader = PdfReader(io.BytesIO(pdf))
        assert len(reader.pages) >= 1
