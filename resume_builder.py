import argparse
from math import ceil
from jinja2 import Environment, FileSystemLoader
import yaml
import os
import re
from ats_checker import ATSComplianceChecker
import sys

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
    template_dirs = ["templates/html", "templates/html/personal"]
    template_files = []
    template_paths = {}
    
    for template_dir in template_dirs:
        if os.path.exists(template_dir):
            for f in os.listdir(template_dir):
                if f.endswith(".html.j2") and not f.startswith("."):
                    full_path = os.path.join(template_dir, f)
                    if os.path.isfile(full_path):
                        if f not in template_files:
                            template_files.append(f)
                            template_paths[f] = full_path
    
    if not template_files:
        print("No templates found in templates/html directories.")
        sys.exit(1)
    
    print("Select a template:")
    for idx, fname in enumerate(template_files, 1):
        template_name = fname.replace(".html.j2", "").replace("-", " ").title()
        dir_name = "personal" if "personal" in template_paths[fname] else "public"
        print(f"  {idx}. {template_name} ({dir_name})")
    
    while True:
        try:
            template_choice = int(input("Enter the number of your choice: "))
            if 1 <= template_choice <= len(template_files):
                selected_template = template_files[template_choice - 1]
                break
            else:
                print(f"Please enter a number between 1 and {len(template_files)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    
    selected_template_path = template_paths[selected_template]
    
    data_dirs = ["data", "data/personal"]
    yml_files = []
    yml_paths = {}
    
    for data_dir in data_dirs:
        if os.path.exists(data_dir):
            for f in os.listdir(data_dir):
                if f.endswith(".yml") or f.endswith(".yaml"):
                    if f not in yml_files:
                        yml_files.append(f)
                        yml_paths[f] = os.path.join(data_dir, f)
    
    if not yml_files:
        print("No YAML files found in the data directories.")
        sys.exit(1)
    
    print("\nSelect a YAML resume data file:")
    for idx, fname in enumerate(yml_files, 1):
        dir_name = "personal" if "personal" in yml_paths[fname] else "data"
        print(f"  {idx}. {fname} ({dir_name})")
    
    while True:
        try:
            choice = int(input("Enter the number of your choice: "))
            if 1 <= choice <= len(yml_files):
                selected_yml = yml_files[choice - 1]
                break
            else:
                print(f"Please enter a number between 1 and {len(yml_files)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    selected_data_path = yml_paths[selected_yml]

    with open(selected_data_path, 'r') as f:
        resume_data = yaml.safe_load(f)
    name = resume_data.get('name', 'Resume')
    first, last = name.split()[0], name.split()[-1] if len(name.split()) > 1 else name

    base_name = os.path.splitext(selected_yml)[0]
    if base_name.startswith("resume-"):
        suffix = base_name.replace("resume-", "")
    else:
        suffix = base_name

    # Sanitize suffix to prevent path traversal
    if not re.match(r'^[a-zA-Z0-9_-]+$', suffix):
        raise ValueError(f"Invalid characters in filename suffix. Only alphanumeric characters, dashes, and underscores are allowed.")

    output_subfolder = os.path.join("outputs", suffix)
    os.makedirs(output_subfolder, exist_ok=True)

    parser = argparse.ArgumentParser(description="Render resume HTML and optionally PDF.")
    parser.add_argument("--pdf", action="store_true", help="Generate a PDF using WeasyPrint")
    parser.add_argument("--no-ats-check", action="store_true", help="Skip ATS compliance validation")
    parser.add_argument("--pdf-variant", choices=['pdf/a-1b', 'pdf/a-2b', 'pdf/a-3b', 'pdf/a-4b'], 
                       default='pdf/a-2b', help="PDF variant to generate (default: pdf/a-2b)")
    args = parser.parse_args()

    # Default behavior: PDF enabled, ATS check disabled
    if len(sys.argv) == 1:
        pdf = True
        no_ats_check = True
    else:
        pdf = args.pdf
        no_ats_check = args.no_ats_check

    html_filename = f"{first}_{last}_Resume.html"
    html_output_path = os.path.join(output_subfolder, html_filename)
    pdf_filename = f"{first}_{last}_Resume.pdf"
    pdf_output_path = os.path.join(output_subfolder, pdf_filename) if pdf else None

    render_resume(
        template_path=selected_template_path,
        data_path=selected_data_path,
        html_output_path=html_output_path,
        pdf_output_path=pdf_output_path,
        validate_ats=not no_ats_check,
        pdf_variant=args.pdf_variant if pdf else None
    )