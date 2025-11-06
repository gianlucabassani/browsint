import { Layout } from "@/components/Layout";
import { TerminalCard } from "@/components/TerminalCard";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { Home, AlertTriangle } from "lucide-react";

const NotFound = () => {
  return (
    <Layout>
      <div className="flex items-center justify-center min-h-[60vh]">
        <TerminalCard title="error.404" variant="danger" className="max-w-md">
          <div className="text-center space-y-6">
            <div className="flex justify-center">
              <AlertTriangle className="w-16 h-16 text-cyber-red" />
            </div>
            
            <div className="space-y-2">
              <h1 className="text-2xl font-bold text-foreground">Pagina Non Trovata</h1>
              <p className="text-muted-foreground">
                La pagina che stai cercando non esiste o è stata spostata.
              </p>
            </div>
            
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground font-mono">
                Error: 404 - Route not found
              </p>
              
              <Link to="/">
                <Button className="w-full">
                  <Home className="w-4 h-4 mr-2" />
                  Torna alla Dashboard
                </Button>
              </Link>
            </div>
          </div>
        </TerminalCard>
      </div>
    </Layout>
  );
};

export default NotFound; 