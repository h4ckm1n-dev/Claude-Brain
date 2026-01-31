import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Database, FileText, HardDrive } from 'lucide-react';
import { StatsResponse } from '../../types/memory';
import { DocumentStats } from '../../api/documents';

interface StorageOverviewProps {
  memoryStats?: StatsResponse;
  documentStats?: DocumentStats;
}

export function StorageOverview({ memoryStats, documentStats }: StorageOverviewProps) {
  const totalMemories = memoryStats?.total_memories || 0;
  const totalDocuments = documentStats?.total_chunks || 0;
  const totalItems = totalMemories + totalDocuments;

  const memoryPercentage = totalItems > 0 ? (totalMemories / totalItems) * 100 : 0;
  const documentPercentage = totalItems > 0 ? (totalDocuments / totalItems) * 100 : 0;

  return (
    <Card className="shadow-lg border-l-4 border-l-indigo-500">
      <CardHeader>
        <div className="flex items-center gap-2">
          <HardDrive className="h-5 w-5 text-indigo-600" />
          <CardTitle>Storage Overview</CardTitle>
        </div>
        <CardDescription>Vector database storage distribution</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Total Items */}
        <div className="text-center p-4 bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-indigo-950 dark:to-purple-950 rounded-lg">
          <div className="text-4xl font-bold text-indigo-700 dark:text-indigo-300">
            {totalItems.toLocaleString()}
          </div>
          <div className="text-sm text-indigo-600 dark:text-indigo-400 mt-1">
            Total Vector Entries
          </div>
        </div>

        {/* Storage Breakdown */}
        <div className="space-y-4">
          {/* Memories */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-blue-600" />
                <span className="font-medium">Memories</span>
              </div>
              <span className="text-muted-foreground">
                {totalMemories.toLocaleString()} ({memoryPercentage.toFixed(1)}%)
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
              <div
                className="bg-gradient-to-r from-blue-500 to-blue-600 h-full rounded-full transition-all duration-500"
                style={{ width: `${memoryPercentage}%` }}
              />
            </div>
            <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground pl-6">
              <div>Active: {memoryStats?.active_memories || 0}</div>
              <div>Archived: {memoryStats?.archived_memories || 0}</div>
              <div>Errors: {memoryStats?.unresolved_errors || 0}</div>
            </div>
          </div>

          {/* Documents */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-green-600" />
                <span className="font-medium">Document Chunks</span>
              </div>
              <span className="text-muted-foreground">
                {totalDocuments.toLocaleString()} ({documentPercentage.toFixed(1)}%)
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
              <div
                className="bg-gradient-to-r from-green-500 to-green-600 h-full rounded-full transition-all duration-500"
                style={{ width: `${documentPercentage}%` }}
              />
            </div>
            <div className="text-xs text-muted-foreground pl-6">
              Status: {documentStats?.status || 'Unknown'}
            </div>
          </div>
        </div>

        {/* Embedding Info */}
        <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Embedding Dimensions</span>
            <span className="font-mono font-bold text-indigo-600">
              {memoryStats?.embedding_dim || 0}D
            </span>
          </div>
          <div className="flex items-center justify-between text-sm mt-2">
            <span className="text-muted-foreground">Estimated Storage</span>
            <span className="font-mono font-bold text-indigo-600">
              {((totalItems * (memoryStats?.embedding_dim || 0) * 4) / (1024 * 1024)).toFixed(2)} MB
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
