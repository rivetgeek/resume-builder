from math import ceil
from jinja2 import Environment, FileSystemLoader
import yaml
import os
from ats_checker import ATSComplianceChecker

def render_resume(template_path, data_path, html_output_path, pdf_output_path=None, validate_ats=True, pdf_variant=None):
    with open(data_path, 'r') as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError("No data found in YAML file")
    
    if 'name' not in data:
        raise ValueError("Missing required field: 'name'")
    if 'title' not in data:
        raise ValueError("Missing required field: 'title'")
    
    optional_sections = [
        'summary', 'objective', 'contact', 'highlights', 'experience', 
        'General_Technologies', 'Security_Tools', 'Security_Disciplines', 'Languages'
    ]
    
    for section in optional_sections:
        if section not in data:
            data[section] = None
            print(f"⚠️  Section '{section}' not found in data file - skipping")
    
    if data.get('contact'):
        required_contact_fields = ['email', 'mobile', 'location']
        for field in required_contact_fields:
            if field not in data['contact']:
                data['contact'][field] = None
                print(f"⚠️  Contact field '{field}' not found - skipping")

    # Enable autoescape to prevent XSS attacks
    def should_autoescape(template_name):
        return template_name.endswith('.html') or template_name.endswith('.html.j2')
    
    env = Environment(
        loader=FileSystemLoader(os.path.dirname(template_path)),
        autoescape=should_autoescape
    )
    env.globals['ceil'] = ceil
    template = env.get_template(os.path.basename(template_path))
    rendered = template.render(data)

    with open(html_output_path, 'w') as f:
        f.write(rendered)
    print(f"Rendered HTML to: {html_output_path}")

    if validate_ats:
        print("\n" + "="*50)
        print("ATS COMPLIANCE CHECK")
        print("="*50)
        
        checker = ATSComplianceChecker()
        ats_report = checker.generate_ats_report(data, rendered)
        print(ats_report)
        
        ats_report_path = html_output_path.replace('.html', '_ats_report.txt')
        with open(ats_report_path, 'w') as f:
            f.write(ats_report)
        print(f"\nATS report saved to: {ats_report_path}")

    if pdf_output_path:
        print("Attempting PDF generation...")
        
        try:
            from weasyprint import HTML
            
            pdf_options = {}
            if pdf_variant:
                pdf_options['pdf_variant'] = pdf_variant
                print(f"Using PDF variant: {pdf_variant}")
            
            HTML(string=rendered, base_url=os.path.abspath(os.path.dirname(template_path))).write_pdf(
                pdf_output_path, **pdf_options
            )
            print(f"✅ Rendered PDF to: {pdf_output_path}")
        except ImportError:
            print("❌ WeasyPrint not installed. Install it via: pip install weasyprint")
        except OSError as e:
            print(f"❌ WeasyPrint system dependencies missing: {e}")
        except Exception as e:
            print(f"❌ PDF generation failed: {e}")

if __name__ == "__main__":
    from cli import main

    main()