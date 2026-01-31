#!/usr/bin/env python3
"""
Tool Name: mock-server.py
Purpose: Simple HTTP mock server for testing
Security: Port validation, safe request handling, configurable responses
Usage:
    # Start server on default port 8000
    ./mock-server.py

    # Start on custom port
    ./mock-server.py --port 9999

    # With config file
    ./mock-server.py --config mock-config.json

    # Config format (mock-config.json):
    {
      "routes": {
        "/api/users": {"status": 200, "body": {"users": []}},
        "/api/health": {"status": 200, "body": {"status": "ok"}}
      }
    }
"""

import json
import sys
import argparse
import signal
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional
from urllib.parse import urlparse


class MockHandler(BaseHTTPRequestHandler):
    """HTTP request handler with configurable responses"""

    routes: Dict[str, Dict[str, Any]] = {}

    def log_message(self, format: str, *args) -> None:
        """Override to suppress default logging"""
        pass

    def do_GET(self) -> None:
        """Handle GET requests"""
        self.handle_request()

    def do_POST(self) -> None:
        """Handle POST requests"""
        self.handle_request()

    def do_PUT(self) -> None:
        """Handle PUT requests"""
        self.handle_request()

    def do_DELETE(self) -> None:
        """Handle DELETE requests"""
        self.handle_request()

    def handle_request(self) -> None:
        """Handle any HTTP request"""
        parsed = urlparse(self.path)
        path = parsed.path

        # Check if route is configured
        if path in self.routes:
            route_config = self.routes[path]
            status = route_config.get("status", 200)
            body = route_config.get("body", {})
            headers = route_config.get("headers", {"Content-Type": "application/json"})

            self.send_response(status)
            for header, value in headers.items():
                self.send_header(header, value)
            self.end_headers()

            if isinstance(body, dict) or isinstance(body, list):
                response = json.dumps(body)
            else:
                response = str(body)

            self.wfile.write(response.encode('utf-8'))

        else:
            # Default 404 response
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = json.dumps({
                "error": "Not Found",
                "path": path,
                "available_routes": list(self.routes.keys())
            })
            self.wfile.write(response.encode('utf-8'))


def validate_port(port: int) -> bool:
    """Validate port number"""
    return 1024 <= port <= 65535


def load_config(config_path: str) -> Dict[str, Dict[str, Any]]:
    """Load mock server configuration"""
    path = Path(config_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    if not path.is_file():
        raise ValueError(f"Config path is not a file: {config_path}")

    with open(path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    if "routes" not in config:
        raise ValueError("Config must contain 'routes' key")

    return config["routes"]


def start_server(port: int, routes: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
    """Start the mock HTTP server"""
    # Default routes if none provided
    if not routes:
        routes = {
            "/health": {
                "status": 200,
                "body": {"status": "ok", "message": "Mock server is running"}
            },
            "/": {
                "status": 200,
                "body": {
                    "message": "Mock HTTP Server",
                    "routes": ["/health"]
                }
            }
        }

    # Set routes on handler class
    MockHandler.routes = routes

    # Create server
    server = HTTPServer(("0.0.0.0", port), MockHandler)

    # Output startup info
    output = {
        "success": True,
        "data": {
            "status": "running",
            "host": "0.0.0.0",
            "port": port,
            "url": f"http://localhost:{port}",
            "routes": list(routes.keys())
        },
        "errors": [],
        "metadata": {
            "tool": "mock-server",
            "version": "1.0.0"
        }
    }
    print(json.dumps(output, indent=2))
    sys.stdout.flush()

    # Setup signal handlers for clean shutdown
    def signal_handler(signum, frame):
        print(json.dumps({
            "success": True,
            "data": {"status": "stopped", "signal": signum},
            "errors": [],
            "metadata": {"tool": "mock-server", "version": "1.0.0"}
        }), file=sys.stderr)
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start serving
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Simple HTTP mock server for testing"
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8000,
        help="Server port (default: 8000)"
    )
    parser.add_argument(
        "--config",
        "-c",
        help="JSON config file with route definitions"
    )

    args = parser.parse_args()

    try:
        # Validate port
        if not validate_port(args.port):
            raise ValueError(f"Port must be between 1024 and 65535, got: {args.port}")

        # Load config if provided
        routes = None
        if args.config:
            routes = load_config(args.config)

        # Start server
        start_server(args.port, routes)

    except Exception as e:
        output = {
            "success": False,
            "data": None,
            "errors": [{"type": type(e).__name__, "message": str(e)}],
            "metadata": {
                "tool": "mock-server",
                "version": "1.0.0"
            }
        }
        print(json.dumps(output, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
