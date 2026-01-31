#!/usr/bin/env python3
"""
Session Timeline Generator
Shows complete workflow chains: prompt → edit → error → solution
Visualizes your work sessions
"""

import sys
import json
import urllib.request
from datetime import datetime, timedelta
from typing import List, Dict
from collections import defaultdict

MEMORY_API = "http://localhost:8100"

class SessionTimeline:
    def __init__(self):
        self.sessions = defaultdict(list)

    def log(self, message: str):
        print(message)

    def api_request(self, endpoint: str, method='GET', data=None):
        """Make API request"""
        url = f"{MEMORY_API}{endpoint}"
        headers = {'Content-Type': 'application/json'}

        try:
            if data:
                req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'),
                                            headers=headers, method=method)
            else:
                req = urllib.request.Request(url, headers=headers, method=method)

            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            self.log(f"API Error: {e}")
            return None

    def get_session_id(self, memory: Dict) -> str:
        """Extract session ID from tags"""
        tags = memory.get('tags', [])
        for tag in tags:
            if tag.startswith('session-'):
                return tag
        return None

    def format_memory(self, memory: Dict) -> str:
        """Format memory for display"""
        mem_type = memory['type']
        content = memory.get('content', '')[:80]
        created = memory.get('created_at', '')[:19]

        icons = {
            'context': '💬',
            'pattern': '📝',
            'error': '❌',
            'docs': '📄',
            'decision': '🎯',
            'learning': '💡'
        }

        icon = icons.get(mem_type, '•')

        # Special formatting
        if mem_type == 'context' and content.startswith('User:'):
            return f"  {created} {icon} 👤 {content[6:]}"
        elif mem_type == 'pattern' and 'File Write:' in content or 'File Edit:' in content:
            return f"  {created} {icon} ✏️  {content}"
        elif mem_type == 'error':
            return f"  {created} {icon} 🐛 {content}"
        elif 'Solution:' in content:
            return f"  {created} {icon} ✅ {content}"
        else:
            return f"  {created} {icon} {content}"

    def build_timeline(self, hours: int = 24):
        """Build session timeline"""
        cutoff = datetime.now() - timedelta(hours=hours)

        self.log(f"\n📊 Session Timeline (last {hours} hours)")
        self.log("="*70 + "\n")

        # Fetch memories
        response = self.api_request("/memories?limit=1000", 'GET')

        if not response:
            self.log("❌ Failed to fetch memories")
            return

        memories = response if isinstance(response, list) else []

        # Group by session
        for item in memories:
            memory = item.get('memory', item)

            # Parse date
            try:
                created_at = datetime.fromisoformat(memory['created_at'].replace('Z', '+00:00'))
                if created_at < cutoff:
                    continue
            except:
                continue

            session_id = self.get_session_id(memory)
            if session_id:
                self.sessions[session_id].append(memory)

        if not self.sessions:
            self.log("No sessions found in the last {hours} hours")
            return

        # Display sessions
        for session_id in sorted(self.sessions.keys(), reverse=True):
            memories_in_session = sorted(self.sessions[session_id],
                                        key=lambda m: m.get('created_at', ''))

            # Session header
            session_time = session_id.replace('session-', '')
            session_date = f"{session_time[:4]}-{session_time[4:6]}-{session_time[6:8]} {session_time[8:10]}:00"

            # Count types
            types = defaultdict(int)
            for m in memories_in_session:
                types[m['type']] += 1

            type_summary = ", ".join([f"{count} {t}" for t, count in types.items()])

            self.log(f"┌─ Session: {session_date}")
            self.log(f"│  ({len(memories_in_session)} memories: {type_summary})")
            self.log(f"└─")

            # Display memories
            for memory in memories_in_session:
                self.log(self.format_memory(memory))

            self.log("")  # Blank line between sessions

    def export_json(self, hours: int = 24, output_file: str = None):
        """Export timeline as JSON"""
        cutoff = datetime.now() - timedelta(hours=hours)

        # Fetch memories
        response = self.api_request("/memories?limit=1000", 'GET')

        if not response:
            return

        memories = response if isinstance(response, list) else []

        # Group by session
        sessions_data = {}
        for item in memories:
            memory = item.get('memory', item)

            try:
                created_at = datetime.fromisoformat(memory['created_at'].replace('Z', '+00:00'))
                if created_at < cutoff:
                    continue
            except:
                continue

            session_id = self.get_session_id(memory)
            if session_id:
                if session_id not in sessions_data:
                    sessions_data[session_id] = []
                sessions_data[session_id].append(memory)

        # Export
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(sessions_data, f, indent=2)
            self.log(f"✓ Exported to: {output_file}")
        else:
            print(json.dumps(sessions_data, indent=2))

def main():
    import argparse

    parser = argparse.ArgumentParser(description='View session timeline')
    parser.add_argument('--hours', type=int, default=24,
                       help='Hours to look back (default: 24)')
    parser.add_argument('--json', type=str,
                       help='Export as JSON to file')

    args = parser.parse_args()

    # Check memory service
    try:
        req = urllib.request.Request(f"{MEMORY_API}/health")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status != 200:
                print("❌ Memory service not available")
                sys.exit(1)
    except:
        print("❌ Cannot connect to memory service")
        sys.exit(1)

    # Build timeline
    timeline = SessionTimeline()

    if args.json:
        timeline.export_json(hours=args.hours, output_file=args.json)
    else:
        timeline.build_timeline(hours=args.hours)

if __name__ == '__main__':
    main()
