import type { Memory } from '../types/memory';

/**
 * Export memories to CSV format
 */
export function exportToCSV(memories: Memory[], filename = 'memories.csv') {
  const headers = ['ID', 'Type', 'Content', 'Tags', 'Created', 'Access Count', 'Score', 'Project'];

  const rows = memories.map(m => [
    m.id,
    m.type,
    (m.content || '').replace(/"/g, '""'), // Escape quotes
    (m.tags || []).join(';'),
    m.created_at,
    m.access_count?.toString() || '0',
    m.importance_score?.toFixed(2) || '0',
    m.project || ''
  ]);

  const csv = [
    headers.join(','),
    ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
  ].join('\n');

  downloadFile(csv, filename, 'text/csv');
}

/**
 * Export memories to JSON format
 */
export function exportToJSON(memories: Memory[], filename = 'memories.json') {
  const json = JSON.stringify(memories, null, 2);
  downloadFile(json, filename, 'application/json');
}

/**
 * Download file to user's computer
 */
function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export memories to Markdown format
 */
export function exportToMarkdown(memories: Memory[], filename = 'memories.md') {
  const markdown = [
    '# Memory Export',
    '',
    `**Exported:** ${new Date().toISOString()}`,
    `**Total Memories:** ${memories.length}`,
    '',
    '---',
    '',
    ...memories.map(m => `
## ${(m.type || '').toUpperCase()}: ${(m.content || '').slice(0, 60)}...

**ID:** ${m.id}
**Created:** ${m.created_at}
**Score:** ${m.importance_score?.toFixed(2) || 'N/A'}
**Access Count:** ${m.access_count || 0}
**Project:** ${m.project || 'N/A'}
**Tags:** ${(m.tags || []).join(', ')}

**Content:**
${m.content || ''}

${m.error_message ? `**Error:**\n${m.error_message}\n\n` : ''}
${m.solution ? `**Solution:**\n${m.solution}\n\n` : ''}

---
`)
  ].join('\n');

  downloadFile(markdown, filename, 'text/markdown');
}
