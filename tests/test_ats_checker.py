import pytest
from ats_checker import ATSComplianceChecker


@pytest.fixture
def checker():
    return ATSComplianceChecker()


def test_check_resume_data_valid(checker):
    data = {
        'name': 'John Doe',
        'title': 'Software Engineer',
        'contact': {
            'email': 'john@example.com',
            'location': 'San Francisco, CA'
        },
        'experience': [
            {
                'title': 'Engineer',
                'company': 'Tech Corp',
                'dates': '2020 - Present',
                'bullets': ['Led development', 'Increased performance by 50%']
            }
        ]
    }
    issues = checker.check_resume_data(data)
    assert len(issues['errors']) == 0


def test_check_resume_data_missing_name(checker):
    data = {
        'title': 'Software Engineer',
        'contact': {'email': 'test@example.com'},
        'experience': []
    }
    issues = checker.check_resume_data(data)
    assert any('Missing required section: name' in error for error in issues['errors'])


def test_check_resume_data_missing_title(checker):
    data = {
        'name': 'John Doe',
        'contact': {'email': 'test@example.com'},
        'experience': []
    }
    issues = checker.check_resume_data(data)
    assert any('Missing required section: title' in error for error in issues['errors'])


def test_check_resume_data_missing_contact(checker):
    data = {
        'name': 'John Doe',
        'title': 'Software Engineer',
        'experience': []
    }
    issues = checker.check_resume_data(data)
    assert any('Missing required section: contact' in error for error in issues['errors'])


def test_check_resume_data_missing_experience(checker):
    data = {
        'name': 'John Doe',
        'title': 'Software Engineer',
        'contact': {'email': 'test@example.com'}
    }
    issues = checker.check_resume_data(data)
    assert any('Missing required section: experience' in error for error in issues['errors'])


def test_check_resume_data_missing_contact_email(checker):
    data = {
        'name': 'John Doe',
        'title': 'Software Engineer',
        'contact': {'location': 'San Francisco'},
        'experience': []
    }
    issues = checker.check_resume_data(data)
    assert any('Missing contact field: email' in warning for warning in issues['warnings'])


def test_check_resume_data_action_verb_suggestion(checker):
    data = {
        'name': 'John Doe',
        'title': 'Engineer',
        'contact': {'email': 'test@example.com', 'location': 'SF'},
        'experience': [
            {
                'title': 'Engineer',
                'company': 'Corp',
                'dates': '2020 - Present',
                'bullets': ['Responsible for development']
            }
        ]
    }
    issues = checker.check_resume_data(data)
    assert any('action verb' in suggestion.lower() for suggestion in issues['suggestions'])


def test_check_resume_data_metrics_suggestion(checker):
    data = {
        'name': 'John Doe',
        'title': 'Engineer',
        'contact': {'email': 'test@example.com', 'location': 'SF'},
        'experience': [
            {
                'title': 'Engineer',
                'company': 'Corp',
                'dates': '2020 - Present',
                'bullets': ['Built systems']
            }
        ]
    }
    issues = checker.check_resume_data(data)
    assert any('metrics' in suggestion.lower() for suggestion in issues['suggestions'])


def test_check_html_compliance_tables(checker):
    html = '<table><tr><td>Content</td></tr></table>'
    issues = checker.check_html_compliance(html)
    assert any('tables' in error.lower() for error in issues['errors'])


def test_check_html_compliance_images(checker):
    html = '<img src="photo.jpg" alt="Photo">'
    issues = checker.check_html_compliance(html)
    assert any('images' in error.lower() for error in issues['errors'])


def test_check_html_compliance_absolute_positioning(checker):
    html = '<div style="position: absolute;">Content</div>'
    issues = checker.check_html_compliance(html)
    assert any('absolute positioning' in warning.lower() for warning in issues['warnings'])


def test_check_html_compliance_custom_font(checker):
    html = '<style>body { font-family: "Comic Sans MS"; }</style>'
    issues = checker.check_html_compliance(html)
    assert any('ats-friendly font' in suggestion.lower() for suggestion in issues['suggestions'])


def test_has_action_verb(checker):
    assert checker._has_action_verb('Led development team')
    assert checker._has_action_verb('Built scalable systems')
    assert not checker._has_action_verb('Responsible for development')


def test_has_metrics(checker):
    assert checker._has_metrics('Increased performance by 50%')
    assert checker._has_metrics('Reduced costs by $1M')
    assert checker._has_metrics('Managed team of 10 people')
    assert not checker._has_metrics('Built systems')


def test_keyword_coverage(checker):
    text = 'python java aws kubernetes docker'
    coverage = checker._check_keyword_coverage(text)
    assert coverage > 0


def test_generate_ats_report_no_issues(checker):
    data = {
        'name': 'John Doe',
        'title': 'Software Engineer',
        'contact': {
            'email': 'john@example.com',
            'location': 'San Francisco, CA'
        },
        'experience': [
            {
                'title': 'Engineer',
                'company': 'Tech Corp',
                'dates': '2020 - Present',
                'bullets': ['Led development of Python systems', 'Increased performance by 50%']
            }
        ],
        'summary': 'Python developer with AWS experience'
    }
    html = '<html><body>Content</body></html>'
    report = checker.generate_ats_report(data, html)
    assert 'ATS Compliance Report' in report

