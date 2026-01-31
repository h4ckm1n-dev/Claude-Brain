#!/usr/bin/env python3
"""
Tool Name: file-converter.py
Purpose: Convert between JSON, YAML, and TOML formats
Security: Input validation, safe file handling, format detection
Usage:
    # Convert JSON to YAML
    ./file-converter.py input.json --output-format yaml

    # Convert via stdin
    echo '{"key": "value"}' | ./file-converter.py --input-format json --output-format yaml

    # Auto-detect input format
    ./file-converter.py config.yaml --output-format json
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import yaml
except ImportError:
    yaml = None

try:
    import tomli
    import tomli_w
except ImportError:
    tomli = None
    tomli_w = None


def detect_format(file_path: Optional[str] = None, content: Optional[str] = None) -> str:
    """Detect file format from extension or content"""
    if file_path:
        suffix = Path(file_path).suffix.lower()
        if suffix == ".json":
            return "json"
        elif suffix in [".yaml", ".yml"]:
            return "yaml"
        elif suffix == ".toml":
            return "toml"

    # Try to detect from content
    if content:
        content = content.strip()
        if content.startswith("{") or content.startswith("["):
            return "json"
        elif "=" in content and "[" in content:
            return "toml"
        else:
            return "yaml"

    return "unknown"


def validate_format(fmt: str) -> bool:
    """Validate format is supported"""
    supported = ["json", "yaml", "yml", "toml"]
    return fmt.lower() in supported


def parse_content(content: str, input_format: str) -> Dict[str, Any]:
    """Parse content from specified format"""
    if input_format == "json":
        return json.loads(content)

    elif input_format in ["yaml", "yml"]:
        if yaml is None:
            raise RuntimeError("PyYAML not installed. Install with: pip install PyYAML")
        return yaml.safe_load(content)

    elif input_format == "toml":
        if tomli is None:
            raise RuntimeError("tomli not installed. Install with: pip install tomli tomli-w")
        return tomli.loads(content)

    else:
        raise ValueError(f"Unsupported input format: {input_format}")


def format_content(data: Dict[str, Any], output_format: str) -> str:
    """Format data to specified format"""
    if output_format == "json":
        return json.dumps(data, indent=2)

    elif output_format in ["yaml", "yml"]:
        if yaml is None:
            raise RuntimeError("PyYAML not installed. Install with: pip install PyYAML")
        return yaml.safe_dump(data, default_flow_style=False, sort_keys=False)

    elif output_format == "toml":
        if tomli_w is None:
            raise RuntimeError("tomli-w not installed. Install with: pip install tomli tomli-w")
        return tomli_w.dumps(data)

    else:
        raise ValueError(f"Unsupported output format: {output_format}")


def convert_file(
    input_path: Optional[str],
    input_format: Optional[str],
    output_format: str
) -> Dict[str, Any]:
    """Convert file between formats"""
    # Read input
    if input_path:
        if not Path(input_path).exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Prevent directory traversal
        resolved = Path(input_path).resolve()
        if not resolved.is_file():
            raise ValueError(f"Path is not a file: {input_path}")

        with open(resolved, 'r', encoding='utf-8') as f:
            content = f.read()

        # Auto-detect format if not specified
        if not input_format:
            input_format = detect_format(file_path=input_path)
            if input_format == "unknown":
                input_format = detect_format(content=content)
    else:
        # Read from stdin
        content = sys.stdin.read()
        if not input_format:
            input_format = detect_format(content=content)

    if input_format == "unknown":
        raise ValueError("Could not detect input format. Please specify --input-format")

    # Normalize format names
    if input_format == "yml":
        input_format = "yaml"
    if output_format == "yml":
        output_format = "yaml"

    # Parse and convert
    data = parse_content(content, input_format)
    output = format_content(data, output_format)

    return {
        "input_format": input_format,
        "output_format": output_format,
        "converted_content": output,
        "data_keys": list(data.keys()) if isinstance(data, dict) else None
    }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Convert between JSON, YAML, and TOML formats"
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        help="Input file path (or read from stdin if not provided)"
    )
    parser.add_argument(
        "--input-format",
        "-i",
        choices=["json", "yaml", "yml", "toml"],
        help="Input format (auto-detected if not specified)"
    )
    parser.add_argument(
        "--output-format",
        "-o",
        choices=["json", "yaml", "yml", "toml"],
        required=True,
        help="Output format"
    )
    parser.add_argument(
        "--output-file",
        "-f",
        help="Write output to file instead of stdout"
    )

    args = parser.parse_args()

    try:
        # Validate output format
        if not validate_format(args.output_format):
            raise ValueError(f"Invalid output format: {args.output_format}")

        # Convert
        result = convert_file(
            args.input_file,
            args.input_format,
            args.output_format
        )

        # Write output
        if args.output_file:
            output_path = Path(args.output_file).resolve()
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result["converted_content"])

            output = {
                "success": True,
                "data": {
                    "input_format": result["input_format"],
                    "output_format": result["output_format"],
                    "output_file": str(output_path),
                    "data_keys": result["data_keys"]
                },
                "errors": [],
                "metadata": {
                    "tool": "file-converter",
                    "version": "1.0.0"
                }
            }
        else:
            # Output converted content directly (not JSON wrapped)
            print(result["converted_content"])
            sys.exit(0)

        print(json.dumps(output, indent=2))
        sys.exit(0)

    except Exception as e:
        output = {
            "success": False,
            "data": None,
            "errors": [{"type": type(e).__name__, "message": str(e)}],
            "metadata": {
                "tool": "file-converter",
                "version": "1.0.0"
            }
        }
        print(json.dumps(output, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
