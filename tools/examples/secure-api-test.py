#!/usr/bin/env python3
"""
Secure API Testing Tool

Example of secure tool implementation with proper input validation
and no command injection vulnerabilities.

Usage:
    ./secure-api-test.py <url> [method] [json-data]

Example:
    ./secure-api-test.py "https://api.example.com/users" GET
    ./secure-api-test.py "https://api.example.com/users" POST '{"name":"test"}'
"""

import sys
import json
import re
from urllib.parse import urlparse
from typing import Dict, Any, Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

def output_json(success: bool, data: Any = None, errors: list = None) -> None:
    """Output standardized JSON response"""
    import json
    from datetime import datetime, timezone
    result = {
        "success": success,
        "data": data or {},
        "errors": errors or [],
        "metadata": {
            "tool": "secure-api-test",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }
    print(json.dumps(result, indent=2))

# Handle missing requests library gracefully
if not REQUESTS_AVAILABLE:
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print(__doc__)
        sys.exit(0)
    output_json(
        success=False,
        errors=[{
            "type": "DependencyMissing",
            "message": "requests library required. Install: pip install requests"
        }]
    )
    sys.exit(1)

def validate_url(url: str) -> bool:
    """Validate URL to prevent SSRF attacks"""
    try:
        parsed = urlparse(url)

        # Must have scheme
        if parsed.scheme not in ['http', 'https']:
            return False

        # Must have valid hostname
        if not parsed.netloc:
            return False

        # Block local/private IPs (basic check)
        hostname = parsed.hostname
        if hostname in ['localhost', '127.0.0.1', '::1']:
            print("Warning: Localhost access blocked for security")
            return False

        return True
    except Exception:
        return False

def validate_method(method: str) -> str:
    """Validate HTTP method"""
    allowed_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
    method = method.upper()

    if method not in allowed_methods:
        raise ValueError(f"Invalid HTTP method. Allowed: {', '.join(allowed_methods)}")

    return method

def test_api_endpoint(
    url: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Test API endpoint safely

    Returns structured result with status, headers, body, timing
    """
    # Validate inputs
    if not validate_url(url):
        return {
            "success": False,
            "error": "Invalid or unsafe URL",
            "url": url
        }

    try:
        method = validate_method(method)
    except ValueError as e:
        return {
            "success": False,
            "error": str(e)
        }

    # Set safe defaults
    if headers is None:
        headers = {}

    # Add user agent
    headers.setdefault('User-Agent', 'Claude-Agent-API-Tester/1.0')

    try:
        response = requests.request(
            method=method,
            url=url,
            json=data,
            headers=headers,
            timeout=10,
            allow_redirects=True,
            verify=True  # Verify SSL certificates
        )

        # Determine content type
        content_type = response.headers.get('content-type', '')

        # Parse body based on content type
        if 'application/json' in content_type:
            try:
                body = response.json()
            except json.JSONDecodeError:
                body = response.text
        else:
            body = response.text[:1000]  # Limit text response size

        return {
            "success": True,
            "status_code": response.status_code,
            "status_text": response.reason,
            "headers": dict(response.headers),
            "body": body,
            "elapsed_ms": round(response.elapsed.total_seconds() * 1000, 2),
            "url": response.url  # Final URL after redirects
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timeout (10s)",
            "error_type": "Timeout"
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Connection failed",
            "error_type": "ConnectionError"
        }
    except requests.exceptions.SSLError as e:
        return {
            "success": False,
            "error": f"SSL verification failed: {str(e)}",
            "error_type": "SSLError"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help']:
        print(__doc__)
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    # Parse arguments
    url = sys.argv[1]
    method = sys.argv[2] if len(sys.argv) > 2 else "GET"

    # Parse JSON data if provided
    data = None
    if len(sys.argv) > 3:
        try:
            data = json.loads(sys.argv[3])
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON data: {e}")
            sys.exit(1)

    # Execute test
    result = test_api_endpoint(url, method, data)

    # Output as JSON
    print(json.dumps(result, indent=2))

    # Exit with error code if failed
    sys.exit(0 if result['success'] else 1)

if __name__ == "__main__":
    main()
