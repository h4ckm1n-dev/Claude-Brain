import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Zap, Search, Plus, Settings, FileText, Database } from 'lucide-react';
import { Button } from '../ui/button';
import { Link } from 'react-router-dom';

export function QuickActions() {
  return (
    <Card className="shadow-lg border-l-4 border-l-blue-500">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Zap className="h-5 w-5 text-blue-600" />
          <CardTitle>Quick Actions</CardTitle>
        </div>
        <CardDescription>Common operations and shortcuts</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {/* Search Memories */}
          <Link to="/search" className="group">
            <Button
              variant="outline"
              className="w-full h-24 flex flex-col items-center justify-center gap-2 hover:bg-blue-50 dark:hover:bg-blue-950 hover:border-blue-500 transition-all"
            >
              <Search className="h-6 w-6 text-blue-600 group-hover:scale-110 transition-transform" />
              <span className="text-xs font-medium">Search</span>
            </Button>
          </Link>

          {/* Create Memory */}
          <Link to="/memories" className="group">
            <Button
              variant="outline"
              className="w-full h-24 flex flex-col items-center justify-center gap-2 hover:bg-green-50 dark:hover:bg-green-950 hover:border-green-500 transition-all"
            >
              <Plus className="h-6 w-6 text-green-600 group-hover:scale-110 transition-transform" />
              <span className="text-xs font-medium">New Memory</span>
            </Button>
          </Link>

          {/* View Documents */}
          <Link to="/documents" className="group">
            <Button
              variant="outline"
              className="w-full h-24 flex flex-col items-center justify-center gap-2 hover:bg-purple-50 dark:hover:bg-purple-950 hover:border-purple-500 transition-all"
            >
              <FileText className="h-6 w-6 text-purple-600 group-hover:scale-110 transition-transform" />
              <span className="text-xs font-medium">Documents</span>
            </Button>
          </Link>

          {/* Analytics */}
          <Link to="/analytics" className="group">
            <Button
              variant="outline"
              className="w-full h-24 flex flex-col items-center justify-center gap-2 hover:bg-indigo-50 dark:hover:bg-indigo-950 hover:border-indigo-500 transition-all"
            >
              <Database className="h-6 w-6 text-indigo-600 group-hover:scale-110 transition-transform" />
              <span className="text-xs font-medium">Analytics</span>
            </Button>
          </Link>

          {/* Knowledge Graph */}
          <Link to="/graph" className="group">
            <Button
              variant="outline"
              className="w-full h-24 flex flex-col items-center justify-center gap-2 hover:bg-pink-50 dark:hover:bg-pink-950 hover:border-pink-500 transition-all"
            >
              <svg className="h-6 w-6 text-pink-600 group-hover:scale-110 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
              <span className="text-xs font-medium">Graph</span>
            </Button>
          </Link>

          {/* Suggestions */}
          <Link to="/suggestions" className="group">
            <Button
              variant="outline"
              className="w-full h-24 flex flex-col items-center justify-center gap-2 hover:bg-teal-50 dark:hover:bg-teal-950 hover:border-teal-500 transition-all"
            >
              <svg className="h-6 w-6 text-teal-600 group-hover:scale-110 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              <span className="text-xs font-medium">Suggestions</span>
            </Button>
          </Link>

          {/* Settings */}
          <Link to="/settings" className="group">
            <Button
              variant="outline"
              className="w-full h-24 flex flex-col items-center justify-center gap-2 hover:bg-gray-50 dark:hover:bg-gray-800 hover:border-gray-500 transition-all"
            >
              <Settings className="h-6 w-6 text-gray-600 group-hover:scale-110 transition-transform" />
              <span className="text-xs font-medium">Settings</span>
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
