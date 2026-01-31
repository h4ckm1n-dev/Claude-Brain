import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Database,
  FileText,
  Search,
  Network,
  BarChart3,
  Brain,
  Lightbulb,
  Settings
} from 'lucide-react';
import { cn } from '../../lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Memories', href: '/memories', icon: Database },
  { name: 'Documents', href: '/documents', icon: FileText },
  { name: 'Search', href: '/search', icon: Search },
  { name: 'Graph', href: '/graph', icon: Network },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Brain Intelligence', href: '/brain', icon: Brain },
  { name: 'Suggestions', href: '/suggestions', icon: Lightbulb },
  { name: 'Settings', href: '/settings', icon: Settings },
];

interface SidebarProps {
  onNavigate?: () => void;
}

export function Sidebar({ onNavigate }: SidebarProps) {
  const location = useLocation();

  return (
    <div className="flex h-screen w-64 flex-col fixed left-0 top-0 bg-card border-r">
      <div className="flex h-16 items-center gap-3 px-6 border-b">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" className="h-10 w-10 flex-shrink-0">
          <defs>
            <linearGradient id="brainGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style={{stopColor: '#8B5CF6', stopOpacity: 1}} />
              <stop offset="100%" style={{stopColor: '#EC4899', stopOpacity: 1}} />
            </linearGradient>
          </defs>
          <path d="M32 8C24 8 18 14 18 22C18 24 18.5 26 19.5 27.5C17 28 15 30.5 15 33.5C15 36 16.5 38 18.5 39C18 40 18 41 18 42C18 46 21 49 25 50C25 53 27.5 56 32 56C36.5 56 39 53 39 50C43 49 46 46 46 42C46 41 46 40 45.5 39C47.5 38 49 36 49 33.5C49 30.5 47 28 44.5 27.5C45.5 26 46 24 46 22C46 14 40 8 32 8Z"
                fill="url(#brainGradient)"
                stroke="url(#brainGradient)"
                strokeWidth="2"/>
          <path d="M28 18C26 20 25 23 25 26" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" fill="none" opacity="0.6"/>
          <path d="M36 18C38 20 39 23 39 26" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" fill="none" opacity="0.6"/>
          <path d="M22 32C24 34 27 35 30 35" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" fill="none" opacity="0.6"/>
          <path d="M42 32C40 34 37 35 34 35" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" fill="none" opacity="0.6"/>
          <circle cx="24" cy="24" r="1.5" fill="#FFFFFF" opacity="0.8"/>
          <circle cx="40" cy="24" r="1.5" fill="#FFFFFF" opacity="0.8"/>
          <circle cx="32" cy="30" r="1.5" fill="#FFFFFF" opacity="0.8"/>
        </svg>
        <h1 className="text-xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
          Claude Brain
        </h1>
      </div>
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href;
          return (
            <Link
              key={item.name}
              to={item.href}
              onClick={onNavigate}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200",
                isActive
                  ? "bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg shadow-blue-500/20"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground hover:scale-105"
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.name}
            </Link>
          );
        })}
      </nav>
      <div className="border-t p-4">
        <div className="text-xs text-muted-foreground">
          <div className="font-semibold mb-1">Claude Memory</div>
          <div>Version 1.0.0</div>
          <div className="mt-2 text-[10px] text-gray-400">
            Enhanced with Advanced Analytics
          </div>
        </div>
      </div>
    </div>
  );
}
