#!/usr/bin/env python3
"""
Automatic NLP Tagger
Extracts tech stack entities from memory content
Auto-tags: languages, frameworks, APIs, libraries, error types
"""

import re
import sys
import json
import urllib.request
from typing import List, Dict, Set

MEMORY_API = "http://localhost:8100"

# Tech stack dictionary
TECH_ENTITIES = {
    # Programming Languages
    'languages': {
        'python', 'javascript', 'typescript', 'java', 'go', 'rust', 'ruby', 'php',
        'c++', 'c#', 'swift', 'kotlin', 'scala', 'perl', 'bash', 'shell', 'sql'
    },

    # Frontend Frameworks
    'frontend': {
        'react', 'vue', 'angular', 'svelte', 'nextjs', 'next.js', 'nuxt',
        'gatsby', 'vite', 'webpack', 'tailwind', 'bootstrap', 'mui', 'chakra'
    },

    # Backend Frameworks
    'backend': {
        'express', 'fastify', 'nestjs', 'django', 'flask', 'fastapi', 'spring',
        'rails', 'laravel', 'gin', 'actix', 'rocket', 'fiber'
    },

    # Databases
    'databases': {
        'postgresql', 'postgres', 'mysql', 'mongodb', 'redis', 'elasticsearch',
        'dynamodb', 'cassandra', 'neo4j', 'qdrant', 'pinecone', 'supabase', 'firebase'
    },

    # Cloud & Infrastructure
    'cloud': {
        'aws', 'gcp', 'azure', 'docker', 'kubernetes', 'k8s', 'terraform',
        'ansible', 'jenkins', 'github actions', 'gitlab ci', 'circleci'
    },

    # Libraries & Tools
    'libraries': {
        'numpy', 'pandas', 'sklearn', 'tensorflow', 'pytorch', 'langchain',
        'openai', 'anthropic', 'huggingface', 'transformers', 'axios', 'lodash',
        'moment', 'dayjs', 'zod', 'joi', 'bcrypt', 'jwt', 'passport'
    },

    # Error Types
    'errors': {
        'typeerror', 'referenceerror', 'syntaxerror', 'networkerror',
        'permission', 'econnrefused', 'etimedout', 'enoent', 'eacces',
        '400', '401', '403', '404', '500', '502', '503'
    }
}

class NLPTagger:
    def __init__(self):
        self.tagged_count = 0
        self.skipped_count = 0

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

    def extract_entities(self, text: str) -> Set[str]:
        """Extract tech entities from text"""
        text_lower = text.lower()
        entities = set()

        # Extract all entity types
        for category, terms in TECH_ENTITIES.items():
            for term in terms:
                # Word boundary matching
                pattern = r'\b' + re.escape(term) + r'\b'
                if re.search(pattern, text_lower):
                    entities.add(term)

        # Extract file extensions as language indicators
        extensions = re.findall(r'\.([a-z]{1,4})\b', text_lower)
        ext_to_lang = {
            'py': 'python', 'js': 'javascript', 'ts': 'typescript',
            'java': 'java', 'go': 'go', 'rs': 'rust', 'rb': 'ruby',
            'php': 'php', 'sql': 'sql', 'sh': 'bash', 'cpp': 'c++',
            'cs': 'c#', 'swift': 'swift', 'kt': 'kotlin'
        }
        for ext in extensions:
            if ext in ext_to_lang:
                entities.add(ext_to_lang[ext])

        # Extract HTTP status codes
        http_codes = re.findall(r'\b([45]\d{2})\b', text)
        entities.update(http_codes)

        return entities

    def tag_memory(self, memory: Dict) -> bool:
        """Add NLP tags to a memory"""
        memory_id = memory['id']
        current_tags = set(memory.get('tags', []))
        content = (memory.get('content') or '') + ' ' + (memory.get('context') or '') + ' ' + (memory.get('error_message') or '')

        # Extract entities
        entities = self.extract_entities(content)

        # Remove entities already in tags
        new_tags = entities - current_tags

        if not new_tags:
            return False

        # Update memory with new tags
        updated_tags = list(current_tags | new_tags)

        result = self.api_request(f"/memories/{memory_id}", 'PATCH', {
            'tags': updated_tags
        })

        return result is not None

    def tag_all(self, limit: int = 1000):
        """Tag all memories that don't have NLP tags"""
        self.log(f"\n🏷️  Automatic NLP Tagging")
        self.log(f"Processing up to {limit} memories\n")

        # Fetch memories
        self.log("📊 Fetching memories...")
        response = self.api_request("/memories/search", 'POST', {
            "query": "",
            "limit": limit
        })

        if not response:
            self.log("❌ Failed to fetch memories")
            return

        memories = response if isinstance(response, list) else []
        total = len(memories)
        self.log(f"Found: {total} memories\n")

        # Process each memory
        for i, item in enumerate(memories, 1):
            memory = item.get('memory', item)

            try:
                if self.tag_memory(memory):
                    self.tagged_count += 1
                    print(f"[{i}/{total}] ✓ Tagged: {memory.get('content', '')[:50]}...", end='\r')
                else:
                    self.skipped_count += 1
            except Exception as e:
                self.log(f"\n❌ Error tagging {memory['id']}: {e}")

        print()  # Newline
        self.log(f"\n✓ Tagged: {self.tagged_count} memories")
        self.log(f"⊘ Skipped: {self.skipped_count} memories (already tagged)")

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Auto-tag memories with NLP entities')
    parser.add_argument('--limit', type=int, default=1000,
                       help='Maximum memories to process (default: 1000)')

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

    # Run tagger
    tagger = NLPTagger()
    tagger.tag_all(limit=args.limit)

if __name__ == '__main__':
    main()
