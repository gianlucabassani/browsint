import { cn } from "@/lib/utils";

interface BrowsintLogoProps {
  className?: string;
  showText?: boolean;
}

export const BrowsintLogo = ({ className, showText = true }: BrowsintLogoProps) => {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="relative">
        <div className="w-10 h-10 bg-gradient-to-br from-primary via-cyber-green to-primary rounded-lg flex items-center justify-center terminal-glow">
          <span className="text-primary-foreground font-bold text-xl">B</span>
        </div>
        <div className="absolute -top-1 -right-1 w-3 h-3 bg-cyber-green rounded-full pulse-cyber"></div>
      </div>
      {showText && (
        <div className="flex flex-col">
          <h1 className="text-2xl font-bold text-foreground tracking-wider">
            BROWSINT
          </h1>
          <p className="text-xs text-muted-foreground uppercase tracking-widest">
            OSINT Toolkit
          </p>
        </div>
      )}
    </div>
  );
}; 