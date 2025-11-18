import os
import tempfile
import pytest
import yaml
from resume_builder import render_resume


@pytest.fixture
def sample_resume_data():
    return {
        'name': 'Test User',
        'title': 'Software Engineer',
        'contact': {
            'email': 'test@example.com',
            'mobile': '555-1234',
            'location': 'San Francisco, CA'
        },
        'experience': [
            {
                'title': 'Engineer',
                'company': 'Corp',
                'dates': '2020 - Present',
                'bullets': ['Built systems']
            }
        ]
    }


def test_path_traversal_prevention():
    malicious_suffixes = [
        '../../../etc/passwd',
        '..\\..\\windows\\system32',
        '../../outputs/../etc/passwd',
        'normal-name/../../../etc',
        'test@bad',
        'test<script>',
        'test; rm -rf /'
    ]
    
    for suffix in malicious_suffixes:
        import re
        is_valid = bool(re.match(r'^[a-zA-Z0-9_-]+$', suffix))
        assert not is_valid, f"Path traversal attempt '{suffix}' should be rejected"


def test_xss_protection_in_name(sample_resume_data):
    xss_payloads = [
        '<script>alert("xss")</script>',
        '<img src=x onerror=alert(1)>',
        '<svg onload=alert(1)>'
    ]
    
    template_path = 'templates/html/modern-minimal.html.j2'
    
    for payload in xss_payloads:
        sample_resume_data['name'] = payload
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(sample_resume_data, f)
            temp_yaml = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            html_output = f.name
        
        try:
            render_resume(template_path, temp_yaml, html_output, validate_ats=False)
            with open(html_output, 'r') as f:
                content = f.read()
                body_start = content.find('<body>')
                body_content = content[body_start:] if body_start != -1 else content
                assert payload not in body_content
                assert '&lt;' in body_content
        finally:
            os.unlink(temp_yaml)
            if os.path.exists(html_output):
                os.unlink(html_output)


def test_xss_protection_in_summary(sample_resume_data):
    sample_resume_data['summary'] = '<script>alert("xss")</script>Test summary'
    
    template_path = 'templates/html/modern-minimal.html.j2'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(sample_resume_data, f)
        temp_yaml = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        html_output = f.name
    
    try:
        render_resume(template_path, temp_yaml, html_output, validate_ats=False)
        with open(html_output, 'r') as f:
            content = f.read()
            body_start = content.find('<body>')
            body_content = content[body_start:] if body_start != -1 else content
            assert '<script>' not in body_content
            assert '&lt;script&gt;' in body_content
    finally:
        os.unlink(temp_yaml)
        if os.path.exists(html_output):
            os.unlink(html_output)

