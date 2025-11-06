import { BrowsintLogo } from "./BrowsintLogo";
import { Navigation } from "./Navigation";

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout = ({ children }: LayoutProps) => {
  return (
    <div className="min-h-screen bg-background text-foreground flex">
      {/* Sidebar */}
      <div className="flex flex-col">
        {/* Header Logo */}
        <div className="p-6 border-b border-border bg-card">
          <BrowsintLogo />
        </div>
        
        {/* Navigation */}
        <Navigation />
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Top Bar */}
        <header className="h-16 bg-card border-b border-border flex items-center justify-between px-6">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-cyber-green rounded-full pulse-cyber"></div>
            <span className="text-sm text-muted-foreground">Sistema Operativo</span>
          </div>
          
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span>v2.1.0</span>
            <span>•</span>
            <span>{new Date().toLocaleDateString()}</span>
          </div>
        </header>
        
        {/* Page Content */}
        <main className="flex-1 p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}; 