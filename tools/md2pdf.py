#!/usr/bin/env python3
"""
Markdown to PDF Converter
Converts markdown files to PDF while preserving formatting and layout.
"""

import sys
import argparse
from pathlib import Path

def check_dependencies():
    """Check if required packages are installed."""
    missing = []
    try:
        import markdown
    except ImportError:
        missing.append('markdown')

    try:
        import weasyprint
    except ImportError:
        missing.append('weasyprint')

    if missing:
        print(f"Missing required packages: {', '.join(missing)}")
        print("\nInstall with:")
        print(f"  pip3 install {' '.join(missing)}")
        sys.exit(1)

def get_default_css():
    """Return default CSS styling for PDF."""
    return """
    @page {
        size: A4;
        margin: 2cm;
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
        font-size: 11pt;
        line-height: 1.6;
        color: #333;
        max-width: 100%;
    }

    h1, h2, h3, h4, h5, h6 {
        font-weight: 600;
        line-height: 1.25;
        margin-top: 24px;
        margin-bottom: 16px;
        color: #1a1a1a;
    }

    h1 {
        font-size: 2em;
        border-bottom: 1px solid #eaecef;
        padding-bottom: 0.3em;
    }

    h2 {
        font-size: 1.5em;
        border-bottom: 1px solid #eaecef;
        padding-bottom: 0.3em;
    }

    h3 { font-size: 1.25em; }
    h4 { font-size: 1em; }
    h5 { font-size: 0.875em; }
    h6 { font-size: 0.85em; color: #6a737d; }

    p {
        margin-top: 0;
        margin-bottom: 16px;
    }

    code {
        font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
        font-size: 85%;
        background-color: #f6f8fa;
        padding: 0.2em 0.4em;
        border-radius: 3px;
    }

    pre {
        font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
        font-size: 85%;
        line-height: 1.45;
        background-color: #f6f8fa;
        border-radius: 6px;
        padding: 16px;
        overflow: auto;
        margin-bottom: 16px;
    }

    pre code {
        background-color: transparent;
        padding: 0;
        border-radius: 0;
    }

    blockquote {
        padding: 0 1em;
        color: #6a737d;
        border-left: 0.25em solid #dfe2e5;
        margin: 0 0 16px 0;
    }

    table {
        border-collapse: collapse;
        margin-bottom: 16px;
        width: 100%;
    }

    table th, table td {
        padding: 6px 13px;
        border: 1px solid #dfe2e5;
    }

    table th {
        font-weight: 600;
        background-color: #f6f8fa;
    }

    table tr:nth-child(even) {
        background-color: #f6f8fa;
    }

    ul, ol {
        margin-bottom: 16px;
        padding-left: 2em;
    }

    li {
        margin-bottom: 0.25em;
    }

    hr {
        height: 0.25em;
        padding: 0;
        margin: 24px 0;
        background-color: #e1e4e8;
        border: 0;
    }

    a {
        color: #0366d6;
        text-decoration: none;
    }

    a:hover {
        text-decoration: underline;
    }

    img {
        max-width: 100%;
        height: auto;
    }

    /* Prevent page breaks inside these elements */
    h1, h2, h3, h4, h5, h6, pre, blockquote, table {
        page-break-inside: avoid;
    }

    /* Keep headings with following content */
    h1, h2, h3, h4, h5, h6 {
        page-break-after: avoid;
    }
    """

def convert_md_to_pdf(input_file, output_file=None, css_file=None):
    """Convert markdown file to PDF."""
    check_dependencies()

    import markdown
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration

    # Read markdown file
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    markdown_text = input_path.read_text(encoding='utf-8')

    # Convert markdown to HTML with extensions
    md = markdown.Markdown(extensions=[
        'extra',          # Tables, fenced code blocks, etc.
        'codehilite',     # Syntax highlighting
        'toc',            # Table of contents
        'sane_lists',     # Better list handling
        'nl2br',          # Newline to <br>
    ])
    html_body = md.convert(markdown_text)

    # Create complete HTML document
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{input_path.stem}</title>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """

    # Determine output file
    if output_file is None:
        output_file = input_path.with_suffix('.pdf')

    # Get CSS
    if css_file:
        css_path = Path(css_file)
        if css_path.exists():
            custom_css = css_path.read_text(encoding='utf-8')
        else:
            print(f"Warning: CSS file not found: {css_file}, using default CSS")
            custom_css = get_default_css()
    else:
        custom_css = get_default_css()

    # Create PDF
    font_config = FontConfiguration()
    html = HTML(string=html_content)
    css = CSS(string=custom_css, font_config=font_config)

    html.write_pdf(output_file, stylesheets=[css], font_config=font_config)

    print(f"✓ PDF created: {output_file}")
    return output_file

def main():
    parser = argparse.ArgumentParser(
        description='Convert Markdown files to PDF with preserved formatting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s document.md                    # Creates document.pdf
  %(prog)s document.md -o output.pdf      # Specify output file
  %(prog)s document.md -c style.css       # Use custom CSS
  %(prog)s document.md --install          # Show installation instructions
        """
    )

    parser.add_argument('input_file', help='Input markdown file')
    parser.add_argument('-o', '--output', help='Output PDF file (default: same name as input)')
    parser.add_argument('-c', '--css', help='Custom CSS file for styling')
    parser.add_argument('--install', action='store_true', help='Show installation instructions')

    args = parser.parse_args()

    if args.install:
        print("Installation instructions:")
        print("\n1. Install required Python packages:")
        print("   pip3 install markdown weasyprint")
        print("\n2. Make the script executable:")
        print("   chmod +x md2pdf.py")
        print("\n3. Use it:")
        print("   ./md2pdf.py your-file.md")
        sys.exit(0)

    convert_md_to_pdf(args.input_file, args.output, args.css)

if __name__ == '__main__':
    main()
