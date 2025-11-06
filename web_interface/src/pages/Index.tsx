import { Layout } from "@/components/Layout";
import { TerminalCard } from "@/components/TerminalCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Link } from "react-router-dom";
import { 
  Download, 
  Search, 
  UserSearch, 
  Settings,
  Activity,
  Database,
  Shield,
  Zap
} from "lucide-react";

const menuItems = [
  {
    id: 1,
    title: "Web Crawl & Download",
    description: "Download pagine HTML e crawling ricorsivo di siti web",
    icon: Download,
    path: "/crawl",
    features: ["Download singola pagina", "Download multiplo", "Crawl struttura completa"]
  },
  {
    id: 2,
    title: "OSINT Web Scraping",
    description: "Estrazione dati OSINT da pagine web e crawling strutturale",
    icon: Search,
    path: "/scraping", 
    features: ["Analisi pagina web", "Crawl con estrazione OSINT"]
  },
  {
    id: 3,
    title: "Profilazione OSINT",
    description: "Investigazione completa di domini, email e profili social",
    icon: UserSearch,
    path: "/profiling",
    features: ["Analisi domini/IP", "Profila email", "Ricerca username", "Gestione profili"]
  },
  {
    id: 4,
    title: "Opzioni di Sistema",
    description: "Gestione database, backup e configurazione API keys",
    icon: Settings,
    path: "/system",
    features: ["Gestione DB", "Backup", "API Keys", "Cache"]
  }
];

const Dashboard = () => {
  return (
    <Layout>
      <div className="space-y-8">
        {/* Header */}
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 bg-cyber-green rounded-full pulse-cyber"></div>
            <h1 className="text-3xl font-bold tracking-wider">
              BROWSINT - MENU PRINCIPALE
            </h1>
          </div>
          <p className="text-muted-foreground text-lg">
            Toolkit OSINT per scraping, crawling e profilazione intelligence
          </p>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <TerminalCard title="system.status" variant="success">
            <div className="flex items-center gap-3">
              <Shield className="w-8 h-8 text-cyber-green" />
              <div>
                <p className="text-sm text-muted-foreground">Sistema</p>
                <p className="text-lg font-bold text-cyber-green">ONLINE</p>
              </div>
            </div>
          </TerminalCard>

          <TerminalCard title="database.info">
            <div className="flex items-center gap-3">
              <Database className="w-8 h-8 text-primary" />
              <div>
                <p className="text-sm text-muted-foreground">Database</p>
                <p className="text-lg font-bold">127 Records</p>
              </div>
            </div>
          </TerminalCard>

          <TerminalCard title="api.status" variant="warning">
            <div className="flex items-center gap-3">
              <Zap className="w-8 h-8 text-cyber-amber" />
              <div>
                <p className="text-sm text-muted-foreground">API Keys</p>
                <p className="text-lg font-bold text-cyber-amber">4/7 Active</p>
              </div>
            </div>
          </TerminalCard>

          <TerminalCard title="activity.log">
            <div className="flex items-center gap-3">
              <Activity className="w-8 h-8 text-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Ultime scansioni</p>
                <p className="text-lg font-bold">23 oggi</p>
              </div>
            </div>
          </TerminalCard>
        </div>

        {/* Main Menu */}
        <div className="space-y-6">
          <h2 className="text-xl font-semibold text-foreground flex items-center gap-2">
            <span className="text-primary">▓▓▓▓</span> Moduli Principali
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {menuItems.map((item) => {
              const Icon = item.icon;
              return (
                <Card key={item.id} className="group hover:border-primary/50 transition-all duration-200 bg-card/50 backdrop-blur">
                  <CardHeader>
                    <div className="flex items-center gap-4">
                      <div className="p-3 bg-primary/10 rounded-lg group-hover:bg-primary/20 transition-colors">
                        <Icon className="w-6 h-6 text-primary" />
                      </div>
                      <div>
                        <CardTitle className="text-lg">{item.title}</CardTitle>
                        <CardDescription>{item.description}</CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <ul className="space-y-2">
                        {item.features.map((feature, idx) => (
                          <li key={idx} className="flex items-center gap-2 text-sm text-muted-foreground">
                            <span className="text-cyber-green">→</span>
                            {feature}
                          </li>
                        ))}
                      </ul>
                      
                      <Link to={item.path}>
                        <Button className="w-full group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                          Avvia Modulo
                        </Button>
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <TerminalCard title="browsint.info" className="mt-8">
          <div className="text-center space-y-2">
            <p className="text-sm text-muted-foreground">
              BROWSINT v2.1.0 - Tool di scraping, crawling e profilazione OSINT
            </p>
            <p className="text-xs text-muted-foreground/70">
              Seleziona un modulo dal menu principale per iniziare l'analisi
            </p>
          </div>
        </TerminalCard>
      </div>
    </Layout>
  );
};

export default Dashboard; 