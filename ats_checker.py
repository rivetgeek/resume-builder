import re
import os
import yaml
from typing import Dict, List, Optional

class ATSComplianceChecker:
    """Check resume for ATS compliance"""
    
    def __init__(self):
        self.ats_keywords = {
            'technical': ['python', 'java', 'javascript', 'aws', 'kubernetes', 'docker', 'terraform', 'ansible'],
            'security': ['ciso', 'security', 'compliance', 'pci', 'soc2', 'sox', 'hipaa', 'gdpr', 'incident response'],
            'leadership': ['lead', 'manage', 'direct', 'vice president', 'director', 'head of', 'executive'],
            'metrics': ['reduced', 'increased', 'improved', 'achieved', 'delivered', 'implemented']
        }
        
        self.unfriendly_elements = [
            'tables', 'columns', 'images', 'graphics', 'charts', 'headers', 'footers',
            'text boxes', 'shapes', 'watermarks', 'background colors'
        ]
        
        self.ats_friendly_fonts = [
            'arial', 'calibri', 'times new roman', 'georgia', 'verdana', 'tahoma', 'roboto', 'georgia'
        ]

    def check_resume_data(self, data: Dict) -> Dict[str, List[str]]:
        """Check YAML resume data for ATS compliance"""
        issues = {
            'warnings': [],
            'errors': [],
            'suggestions': []
        }
        
        required_sections = ['name', 'title', 'contact', 'experience']
        for section in required_sections:
            if section not in data:
                issues['errors'].append(f"Missing required section: {section}")
        
        if 'contact' in data:
            contact = data['contact']
            required_contact = ['email', 'location']
            for field in required_contact:
                if field not in contact:
                    issues['warnings'].append(f"Missing contact field: {field}")
        
        if 'experience' in data:
            for i, job in enumerate(data['experience']):
                required_job_fields = ['title', 'company', 'dates', 'bullets']
                for field in required_job_fields:
                    if field not in job:
                        issues['errors'].append(f"Job {i+1} missing required field: {field}")
                
                if 'bullets' in job:
                    for j, bullet in enumerate(job['bullets']):
                        if not self._has_action_verb(bullet):
                            issues['suggestions'].append(f"Job {i+1}, bullet {j+1}: Consider starting with an action verb")
                        
                        if not self._has_metrics(bullet):
                            issues['suggestions'].append(f"Job {i+1}, bullet {j+1}: Consider adding quantifiable metrics")
        
        all_text = self._extract_all_text(data)
        keyword_coverage = self._check_keyword_coverage(all_text)
        if keyword_coverage < 0.3:
            issues['suggestions'].append(f"Low keyword coverage ({keyword_coverage:.1%}). Consider adding more relevant keywords.")
        
        return issues

    def check_html_compliance(self, html_content: Optional[str]) -> Dict[str, List[str]]:
        issues = {
            'warnings': [],
            'errors': [],
            'suggestions': []
        }
        
        if not html_content:
            return issues
        
        for element in self.unfriendly_elements:
            if element in html_content.lower():
                issues['warnings'].append(f"Contains potentially ATS-unfriendly element: {element}")
        
        if '<table' in html_content.lower():
            issues['errors'].append("Contains tables - ATS systems may not parse these correctly")
        
        if '<img' in html_content.lower():
            issues['errors'].append("Contains images - ATS systems cannot read image content")
        
        if 'position: absolute' in html_content or 'position: fixed' in html_content:
            issues['warnings'].append("Uses absolute positioning - may cause parsing issues")
        
        font_pattern = r'font-family:\s*([^;]+)'
        fonts = re.findall(font_pattern, html_content, re.IGNORECASE)
        for font in fonts:
            font_clean = font.strip().lower().replace('"', '').replace("'", '')
            if font_clean not in self.ats_friendly_fonts:
                issues['suggestions'].append(f"Consider using ATS-friendly font instead of: {font}")
        
        return issues

    def _extract_all_text(self, data: Dict) -> str:
        text_parts = []
        
        if 'summary' in data and data['summary']:
            text_parts.append(data['summary'])
        
        if 'highlights' in data and data['highlights']:
            text_parts.extend(data['highlights'])
        
        if 'experience' in data and data['experience']:
            for job in data['experience']:
                if 'title' in job and job['title']:
                    text_parts.append(job['title'])
                if 'bullets' in job and job['bullets']:
                    text_parts.extend(job['bullets'])
        
        if 'technologies' in data and data['technologies']:
            text_parts.extend(data['technologies'])
        
        if 'languages' in data and data['languages']:
            text_parts.extend(data['languages'])
        
        if 'disciplines' in data and data['disciplines']:
            text_parts.extend(data['disciplines'])
        
        return ' '.join(text_parts).lower()

    def _check_keyword_coverage(self, text: str) -> float:
        """Calculate keyword coverage percentage"""
        all_keywords = []
        for category in self.ats_keywords.values():
            all_keywords.extend(category)
        
        found_keywords = []
        for keyword in all_keywords:
            if keyword.lower() in text:
                found_keywords.append(keyword)
        
        return len(found_keywords) / len(all_keywords) if all_keywords else 0

    def _has_action_verb(self, text: str) -> bool:
        """Check if text starts with an action verb"""
        action_verbs = [
            'led', 'managed', 'directed', 'built', 'created', 'developed', 'implemented',
            'designed', 'architected', 'reduced', 'increased', 'improved', 'achieved',
            'delivered', 'established', 'founded', 'co-led', 'conducted', 'performed',
            'secured', 'trained', 'participated', 'collaborated', 'reported'
        ]
        
        first_word = text.split()[0].lower() if text.split() else ''
        return first_word in action_verbs

    def _has_metrics(self, text: str) -> bool:
        """Check if text contains quantifiable metrics"""
        metric_patterns = [
            r'\d+%', r'\$\d+', r'\d+\s*(million|billion|thousand)', 
            r'\d+\s*(people|employees|users|customers)', r'\d+\s*(years|months)',
            r'reduced by \d+', r'increased by \d+', r'\d+\s*M', r'\d+\s*K'
        ]
        
        for pattern in metric_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def generate_ats_report(self, data: Dict, html_content: Optional[str] = None) -> str:
        """Generate ATS compliance report"""
        report = ["=== ATS Compliance Report ===\n"]
        
        data_issues = self.check_resume_data(data)
        html_issues = self.check_html_compliance(html_content)
        
        all_errors = data_issues['errors'] + html_issues['errors']
        all_warnings = data_issues['warnings'] + html_issues['warnings']
        all_suggestions = data_issues['suggestions'] + html_issues['suggestions']
        
        if all_errors:
            report.append("❌ ERRORS (Must fix):")
            for error in all_errors:
                report.append(f"  • {error}")
            report.append("")
        
        if all_warnings:
            report.append("⚠️  WARNINGS (Should address):")
            for warning in all_warnings:
                report.append(f"  • {warning}")
            report.append("")
        
        if all_suggestions:
            report.append("💡 SUGGESTIONS (Consider implementing):")
            for suggestion in all_suggestions:
                report.append(f"  • {suggestion}")
            report.append("")
        
        if not any([all_errors, all_warnings, all_suggestions]):
            report.append("✅ Your resume appears to be ATS-compliant!")
        
        return "\n".join(report)


def check_ats_compliance(yaml_path: str, html_path: Optional[str] = None) -> str:
    """Check ATS compliance from file paths"""
    checker = ATSComplianceChecker()
    
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
    
    html_content: Optional[str] = None
    if html_path and os.path.exists(html_path):
        with open(html_path, 'r') as f:
            html_content = f.read()
    
    return checker.generate_ats_report(data, html_content)


if __name__ == "__main__":
    report = check_ats_compliance("data/resume-example.yml", "outputs/resume.html")
    print(report) 