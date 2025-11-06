import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface TerminalCardProps {
  title: string;
  children: ReactNode;
  className?: string;
  variant?: "default" | "success" | "warning" | "danger";
}

export const TerminalCard = ({ 
  title, 
  children, 
  className, 
  variant = "default" 
}: TerminalCardProps) => {
  const variantStyles = {
    default: "border-border",
    success: "border-cyber-green/30 bg-cyber-green/5",
    warning: "border-cyber-amber/30 bg-cyber-amber/5", 
    danger: "border-cyber-red/30 bg-cyber-red/5"
  };
  
  const headerVariants = {
    default: "bg-secondary",
    success: "bg-cyber-green/10",
    warning: "bg-cyber-amber/10",
    danger: "bg-cyber-red/10"
  };

  return (
    <div className={cn(
      "bg-card border rounded-lg overflow-hidden shadow-lg",
      variantStyles[variant],
      className
    )}>
      {/* Terminal Header */}
      <div className={cn(
        "px-4 py-3 border-b border-border flex items-center gap-3",
        headerVariants[variant]
      )}>
        <div className="flex gap-2">
          <div className="w-3 h-3 bg-cyber-red rounded-full"></div>
          <div className="w-3 h-3 bg-cyber-amber rounded-full"></div>
          <div className="w-3 h-3 bg-cyber-green rounded-full"></div>
        </div>
        <span className="text-sm font-mono text-muted-foreground">
          {title}
        </span>
      </div>
      
      {/* Content */}
      <div className="p-6">
        {children}
      </div>
    </div>
  );
}; 