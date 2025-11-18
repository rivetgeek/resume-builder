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
        'summary': 'Test summary',
        'experience': [
            {
                'title': 'Senior Engineer',
                'company': 'Test Corp',
                'dates': '2020 - Present',
                'bullets': ['Built systems', 'Led team']
            }
        ],
        'General_Technologies': ['Python', 'JavaScript'],
        'Languages': ['Python', 'JavaScript']
    }


@pytest.fixture
def temp_yaml_file(sample_resume_data):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(sample_resume_data, f)
        temp_path = f.name
    yield temp_path
    os.unlink(temp_path)


def test_render_resume_valid_data(temp_yaml_file):
    template_path = 'templates/html/modern-minimal.html.j2'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        html_output = f.name
    
    try:
        render_resume(template_path, temp_yaml_file, html_output, validate_ats=False)
        assert os.path.exists(html_output)
        with open(html_output, 'r') as f:
            content = f.read()
            assert 'Test User' in content
            assert 'Software Engineer' in content
    finally:
        if os.path.exists(html_output):
            os.unlink(html_output)


def test_render_resume_missing_name(temp_yaml_file):
    with open(temp_yaml_file, 'r') as f:
        data = yaml.safe_load(f)
    del data['name']
    with open(temp_yaml_file, 'w') as f:
        yaml.dump(data, f)
    
    template_path = 'templates/html/modern-minimal.html.j2'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        html_output = f.name
    
    try:
        with pytest.raises(ValueError, match="Missing required field: 'name'"):
            render_resume(template_path, temp_yaml_file, html_output, validate_ats=False)
    finally:
        if os.path.exists(html_output):
            os.unlink(html_output)


def test_render_resume_missing_title(temp_yaml_file):
    with open(temp_yaml_file, 'r') as f:
        data = yaml.safe_load(f)
    del data['title']
    with open(temp_yaml_file, 'w') as f:
        yaml.dump(data, f)
    
    template_path = 'templates/html/modern-minimal.html.j2'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        html_output = f.name
    
    try:
        with pytest.raises(ValueError, match="Missing required field: 'title'"):
            render_resume(template_path, temp_yaml_file, html_output, validate_ats=False)
    finally:
        if os.path.exists(html_output):
            os.unlink(html_output)


def test_render_resume_empty_yaml():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write('')
        temp_path = f.name
    
    template_path = 'templates/html/modern-minimal.html.j2'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        html_output = f.name
    
    try:
        with pytest.raises(ValueError, match="No data found in YAML file"):
            render_resume(template_path, temp_path, html_output, validate_ats=False)
    finally:
        os.unlink(temp_path)
        if os.path.exists(html_output):
            os.unlink(html_output)


def test_render_resume_xss_protection(temp_yaml_file):
    with open(temp_yaml_file, 'r') as f:
        data = yaml.safe_load(f)
    data['name'] = '<script>alert("xss")</script>'
    with open(temp_yaml_file, 'w') as f:
        yaml.dump(data, f)
    
    template_path = 'templates/html/modern-minimal.html.j2'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        html_output = f.name
    
    try:
        render_resume(template_path, temp_yaml_file, html_output, validate_ats=False)
        with open(html_output, 'r') as f:
            content = f.read()
            body_start = content.find('<body>')
            body_content = content[body_start:] if body_start != -1 else content
            assert '<script>' not in body_content
            assert '&lt;script&gt;' in body_content or '&lt;script&gt;' in content
    finally:
        if os.path.exists(html_output):
            os.unlink(html_output)


def test_render_resume_ats_check(temp_yaml_file):
    template_path = 'templates/html/modern-minimal.html.j2'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        html_output = f.name
    
    try:
        render_resume(template_path, temp_yaml_file, html_output, validate_ats=True)
        ats_report_path = html_output.replace('.html', '_ats_report.txt')
        assert os.path.exists(ats_report_path)
        with open(ats_report_path, 'r') as f:
            report = f.read()
            assert 'ATS Compliance Report' in report
    finally:
        if os.path.exists(html_output):
            os.unlink(html_output)
        if os.path.exists(html_output.replace('.html', '_ats_report.txt')):
            os.unlink(html_output.replace('.html', '_ats_report.txt'))

