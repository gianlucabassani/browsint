import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { 
  Download, 
  Search, 
  UserSearch, 
  Settings,
  Home,
  Shield
} from "lucide-react";

const menuItems = [
  {
    id: "home",
    title: "Dashboard",
    icon: Home,
    path: "/",
    description: "Menu principale"
  },
  {
    id: "crawl",
    title: "Web Crawl & Download",
    icon: Download,
    path: "/crawl",
    description: "Download pagine e crawling siti"
  },
  {
    id: "scraping",
    title: "OSINT Web Scraping", 
    icon: Search,
    path: "/scraping",
    description: "Estrazione dati OSINT"
  },
  {
    id: "profiling",
    title: "Profilazione OSINT",
    icon: UserSearch,
    path: "/profiling", 
    description: "Investigazione domini, email, username"
  },
  {
    id: "system",
    title: "Opzioni di Sistema",
    icon: Settings,
    path: "/system",
    description: "Database e API keys"
  }
];

export const Navigation = () => {
  const location = useLocation();
  
  return (
    <nav className="w-80 bg-card border-r border-border p-6 overflow-y-auto">
      <div className="space-y-2">
        {menuItems.map((item) => {
          const isActive = location.pathname === item.path;
          const Icon = item.icon;
          
          return (
            <Link
              key={item.id}
              to={item.path}
              className={cn(
                "flex items-center gap-4 p-4 rounded-lg transition-all duration-200 group",
                "border border-transparent hover:border-primary/30",
                isActive 
                  ? "bg-gradient-cyber border-primary/50 shadow-lg" 
                  : "hover:bg-secondary/50"
              )}
            >
              <div className={cn(
                "p-2 rounded-lg transition-colors",
                isActive 
                  ? "bg-primary text-primary-foreground" 
                  : "bg-secondary text-muted-foreground group-hover:text-foreground"
              )}>
                <Icon className="w-5 h-5" />
              </div>
              
              <div className="flex-1">
                <h3 className={cn(
                  "font-medium text-sm transition-colors",
                  isActive ? "text-foreground" : "text-muted-foreground group-hover:text-foreground"
                )}>
                  {item.title}
                </h3>
                <p className="text-xs text-muted-foreground/70 mt-1">
                  {item.description}
                </p>
              </div>
              
              {isActive && (
                <div className="w-2 h-2 bg-cyber-green rounded-full pulse-cyber"></div>
              )}
            </Link>
          );
        })}
      </div>
      
      {/* Status Panel */}
      <div className="mt-8 p-4 bg-secondary/30 rounded-lg border border-border">
        <div className="flex items-center gap-2 mb-3">
          <Shield className="w-4 h-4 text-cyber-green" />
          <span className="text-sm font-medium">System Status</span>
        </div>
        
        <div className="space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Database</span>
            <span className="text-cyber-green">●</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">API Keys</span>
            <span className="text-cyber-amber">●</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Scanner</span>
            <span className="text-cyber-green">●</span>
          </div>
        </div>
      </div>
    </nav>
  );
}; 