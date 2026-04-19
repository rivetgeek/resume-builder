"""Interactive CLI for resume-builder (extracted from resume_builder.py)."""

import argparse
import os
import re
import sys

import yaml

from discovery import discover_data_files, discover_templates
from resume_builder import render_resume


def main() -> None:
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)

    template_files, template_paths = discover_templates(root)
    if not template_files:
        print("No templates found in templates/html directories.")
        sys.exit(1)

    print("Select a template:")
    for idx, fname in enumerate(template_files, 1):
        template_name = fname.replace(".html.j2", "").replace("-", " ").title()
        dir_name = "personal" if "personal" in template_paths[fname].replace("\\", "/") else "public"
        print(f"  {idx}. {template_name} ({dir_name})")

    while True:
        try:
            template_choice = int(input("Enter the number of your choice: "))
            if 1 <= template_choice <= len(template_files):
                selected_template = template_files[template_choice - 1]
                break
            print(f"Please enter a number between 1 and {len(template_files)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    selected_template_path = template_paths[selected_template]

    yml_files, yml_paths = discover_data_files(root)
    if not yml_files:
        print("No YAML files found in the data directories.")
        sys.exit(1)

    print("\nSelect a YAML resume data file:")
    for idx, fname in enumerate(yml_files, 1):
        dir_name = "personal" if "personal" in yml_paths[fname].replace("\\", "/") else "data"
        print(f"  {idx}. {fname} ({dir_name})")

    while True:
        try:
            choice = int(input("Enter the number of your choice: "))
            if 1 <= choice <= len(yml_files):
                selected_yml = yml_files[choice - 1]
                break
            print(f"Please enter a number between 1 and {len(yml_files)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    selected_data_path = yml_paths[selected_yml]

    with open(selected_data_path, "r") as f:
        resume_data = yaml.safe_load(f)
    name = resume_data.get("name", "Resume")
    parts = name.split()
    first, last = parts[0], parts[-1] if len(parts) > 1 else name

    base_name = os.path.splitext(selected_yml)[0]
    if base_name.startswith("resume-"):
        suffix = base_name.replace("resume-", "")
    else:
        suffix = base_name

    if not re.match(r"^[a-zA-Z0-9_-]+$", suffix):
        raise ValueError(
            "Invalid characters in filename suffix. Only alphanumeric characters, dashes, "
            "and underscores are allowed."
        )

    output_subfolder = os.path.join("outputs", suffix)
    os.makedirs(output_subfolder, exist_ok=True)

    parser = argparse.ArgumentParser(description="Render resume HTML and optionally PDF.")
    parser.add_argument("--pdf", action="store_true", help="Generate a PDF using WeasyPrint")
    parser.add_argument("--no-ats-check", action="store_true", help="Skip ATS compliance validation")
    parser.add_argument(
        "--pdf-variant",
        choices=["pdf/a-1b", "pdf/a-2b", "pdf/a-3b", "pdf/a-4b"],
        default="pdf/a-2b",
        help="PDF variant to generate (default: pdf/a-2b)",
    )
    args = parser.parse_args()

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
        pdf_variant=args.pdf_variant if pdf else None,
    )


if __name__ == "__main__":
    main()
