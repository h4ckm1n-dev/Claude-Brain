# Markdown to PDF Converter

A powerful tool to convert Markdown files to professionally formatted PDFs while preserving layout and formatting.

## Features

- ✓ **Beautiful formatting** - Professional styling with proper typography
- ✓ **Syntax highlighting** - Code blocks with syntax highlighting
- ✓ **Tables & images** - Full support for tables, images, and diagrams
- ✓ **Custom styling** - Use custom CSS for personalized layouts
- ✓ **Page management** - Intelligent page breaks and pagination
- ✓ **Markdown extensions** - Tables, code blocks, TOC, and more

## Installation

### 1. Install Python dependencies

```bash
pip3 install markdown weasyprint
```

**Note**: On macOS, you may need to install system dependencies first:

```bash
brew install python3 cairo pango gdk-pixbuf libffi
pip3 install markdown weasyprint
```

### 2. Make scripts executable (already done)

```bash
chmod +x ~/.claude/tools/md2pdf
chmod +x ~/.claude/tools/md2pdf.py
```

### 3. Optional: Add to PATH

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
export PATH="$HOME/.claude/tools:$PATH"
```

Then reload: `source ~/.zshrc`

## Usage

### Basic usage

```bash
# Convert markdown to PDF (same filename)
md2pdf document.md

# Specify output file
md2pdf document.md -o output.pdf

# Use custom CSS styling
md2pdf document.md -c custom-style.css

# Or use the Python script directly
python3 ~/.claude/tools/md2pdf.py document.md
```

### Examples

```bash
# Convert README
md2pdf README.md

# Create presentation with custom styling
md2pdf slides.md -c sample-style.css -o presentation.pdf

# Convert documentation
md2pdf docs/api-guide.md -o documentation.pdf
```

## Customization

### Using Custom CSS

1. Copy the sample CSS file:
   ```bash
   cp ~/.claude/tools/sample-style.css my-style.css
   ```

2. Edit `my-style.css` to customize:
   - Page size and margins
   - Fonts and colors
   - Heading styles
   - Code block styling
   - Table appearance
   - Page numbers and headers

3. Use your custom CSS:
   ```bash
   md2pdf document.md -c my-style.css
   ```

### CSS Customization Options

The CSS file supports standard CSS properties plus print-specific features:

```css
/* Page setup */
@page {
    size: A4;           /* or Letter, Legal, etc. */
    margin: 2cm;        /* page margins */

    /* Add page numbers */
    @bottom-right {
        content: counter(page);
    }
}

/* Prevent page breaks */
h1, h2, h3 {
    page-break-after: avoid;
    page-break-inside: avoid;
}

/* Keep content together */
table, pre, blockquote {
    page-break-inside: avoid;
}
```

## Supported Markdown Features

- **Headings** - H1 through H6
- **Emphasis** - *italic*, **bold**, ***bold italic***
- **Lists** - Ordered and unordered lists
- **Links** - [text](url)
- **Images** - ![alt](image.png)
- **Code** - Inline `code` and fenced code blocks
- **Tables** - Full table support
- **Blockquotes** - > quote text
- **Horizontal rules** - ---
- **HTML** - Inline HTML elements

## Advanced Features

### Code Syntax Highlighting

Fenced code blocks with language specification:

\`\`\`python
def hello():
    print("Hello, World!")
\`\`\`

### Tables

```markdown
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
```

### Table of Contents

Add `[TOC]` to generate an automatic table of contents.

## Troubleshooting

### "Module not found" errors

Install missing dependencies:
```bash
pip3 install markdown weasyprint
```

### WeasyPrint installation issues on macOS

Install system dependencies:
```bash
brew install cairo pango gdk-pixbuf libffi
```

### Images not showing

- Use absolute paths or relative paths from the markdown file location
- Ensure image files exist and are accessible

### Custom fonts not working

WeasyPrint supports web fonts. Add to your CSS:
```css
@font-face {
    font-family: 'CustomFont';
    src: url('path/to/font.ttf');
}
body {
    font-family: 'CustomFont', sans-serif;
}
```

## Tips for Best Results

1. **Use proper markdown structure** - Start with H1, don't skip heading levels
2. **Optimize images** - Compress large images before embedding
3. **Test page breaks** - Review PDF and adjust CSS if needed
4. **Use semantic markup** - Proper use of headings, lists, and emphasis
5. **Keep tables simple** - Complex tables may not fit on page width
6. **Preview CSS changes** - Iterate on styling until satisfied

## File Locations

- Main script: `~/.claude/tools/md2pdf`
- Python script: `~/.claude/tools/md2pdf.py`
- Sample CSS: `~/.claude/tools/sample-style.css`
- This README: `~/.claude/tools/README-md2pdf.md`

## Getting Help

```bash
# Show usage help
md2pdf --help

# Show installation instructions
md2pdf --install
```

## License

Free to use and modify for personal and commercial projects.

---

**Created**: 2025-11-06
**Version**: 1.0
**Tool Location**: `~/.claude/tools/`
