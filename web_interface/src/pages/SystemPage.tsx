import { useState } from "react";
import { Layout } from "@/components/Layout";
import { TerminalCard } from "@/components/TerminalCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { 
  Settings,
  Database, 
  Key,
  Trash2,
  Plus,
  Edit,
  Shield,
  HardDrive,
  RefreshCw,
  Download,
  Upload,
  CheckCircle,
  AlertTriangle
} from "lucide-react";

const SystemPage = () => {
  const [activeTab, setActiveTab] = useState("database");
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const databaseStats = {
    size: "156.2 MB",
    tables: 8,
    records: 12453,
    lastBackup: "2024-01-15 14:30",
    status: "healthy"
  };

  const dbTables = [
    { name: "scans", records: 3456, size: "45.2 MB", lastUpdate: "2024-01-15" },
    { name: "profiles", records: 2341, size: "32.1 MB", lastUpdate: "2024-01-14" },
    { name: "domains", records: 4532, size: "28.9 MB", lastUpdate: "2024-01-15" },
    { name: "emails", records: 1892, size: "22.4 MB", lastUpdate: "2024-01-13" },
    { name: "usernames", records: 332, size: "15.8 MB", lastUpdate: "2024-01-12" }
  ];

  const apiKeys = [
    { id: 1, name: "Shodan API", service: "Shodan", status: "active", lastUsed: "2024-01-15" },
    { id: 2, name: "VirusTotal API", service: "VirusTotal", status: "active", lastUsed: "2024-01-14" },
    { id: 3, name: "Have I Been Pwned", service: "HIBP", status: "inactive", lastUsed: "2024-01-10" },
    { id: 4, name: "Hunter.io API", service: "Hunter.io", status: "expired", lastUsed: "2024-01-08" }
  ];

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Settings className="w-6 h-6 text-cyber-amber" />
          <h1 className="text-2xl font-bold text-foreground">Opzioni di Sistema</h1>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="database">Database</TabsTrigger>
            <TabsTrigger value="apikeys">API Keys</TabsTrigger>
          </TabsList>

          <TabsContent value="database" className="space-y-4">
            {/* Database Overview */}
            <TerminalCard title="Informazioni Generali Database" variant="success">
              <div className="grid md:grid-cols-4 gap-4">
                <div className="bg-secondary/20 p-4 rounded-lg border border-border text-center">
                  <HardDrive className="w-6 h-6 text-cyber-blue mx-auto mb-2" />
                  <div className="text-2xl font-bold text-cyber-blue">{databaseStats.size}</div>
                  <div className="text-sm text-muted-foreground">Dimensione DB</div>
                </div>
                
                <div className="bg-secondary/20 p-4 rounded-lg border border-border text-center">
                  <Database className="w-6 h-6 text-cyber-green mx-auto mb-2" />
                  <div className="text-2xl font-bold text-cyber-green">{databaseStats.tables}</div>
                  <div className="text-sm text-muted-foreground">Tabelle</div>
                </div>
                
                <div className="bg-secondary/20 p-4 rounded-lg border border-border text-center">
                  <Shield className="w-6 h-6 text-cyber-amber mx-auto mb-2" />
                  <div className="text-2xl font-bold text-cyber-amber">{databaseStats.records.toLocaleString()}</div>
                  <div className="text-sm text-muted-foreground">Records Totali</div>
                </div>
                
                <div className="bg-secondary/20 p-4 rounded-lg border border-border text-center">
                  <CheckCircle className="w-6 h-6 text-cyber-green mx-auto mb-2" />
                  <Badge variant="default" className="mb-1">Healthy</Badge>
                  <div className="text-sm text-muted-foreground">Status DB</div>
                </div>
              </div>
            </TerminalCard>

            {/* Database Management */}
            <TerminalCard title="Gestione Database" variant="default">
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" className="gap-2">
                    <Download className="w-4 h-4" />
                    Backup Completo
                  </Button>
                  <Button variant="outline" className="gap-2">
                    <Upload className="w-4 h-4" />
                    Ripristina Backup
                  </Button>
                  <Button variant="outline" className="gap-2">
                    <RefreshCw className="w-4 h-4" />
                    Svuota Cache
                  </Button>
                  <Button variant="destructive" className="gap-2">
                    <Trash2 className="w-4 h-4" />
                    Pulisci Database
                  </Button>
                </div>
                
                <div className="bg-secondary/20 p-3 rounded border border-border">
                  <div className="text-sm text-muted-foreground">
                    <strong>Ultimo Backup:</strong> {databaseStats.lastBackup}
                  </div>
                </div>
              </div>
            </TerminalCard>

            {/* Database Tables */}
            <TerminalCard title="Gestione Tabelle Database" variant="default">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nome Tabella</TableHead>
                    <TableHead>Records</TableHead>
                    <TableHead>Dimensione</TableHead>
                    <TableHead>Ultimo Aggiornamento</TableHead>
                    <TableHead>Azioni</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dbTables.map((table, i) => (
                    <TableRow key={i}>
                      <TableCell className="font-mono font-medium">{table.name}</TableCell>
                      <TableCell className="text-cyber-blue">{table.records.toLocaleString()}</TableCell>
                      <TableCell>{table.size}</TableCell>
                      <TableCell className="text-muted-foreground">{table.lastUpdate}</TableCell>
                      <TableCell className="space-x-2">
                        <Button variant="ghost" size="sm">
                          <RefreshCw className="w-3 h-3 mr-1" />
                          Ottimizza
                        </Button>
                        <Button variant="ghost" size="sm" className="text-destructive">
                          <Trash2 className="w-3 h-3 mr-1" />
                          Svuota
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TerminalCard>
          </TabsContent>

          <TabsContent value="apikeys" className="space-y-4">
            {/* API Keys Overview */}
            <TerminalCard title="API Keys Configurate" variant="default">
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <div className="text-sm text-muted-foreground">
                    Gestisci le API keys per i servizi esterni
                  </div>
                  <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                    <DialogTrigger asChild>
                      <Button className="gap-2">
                        <Plus className="w-4 h-4" />
                        Aggiungi API Key
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-md">
                      <DialogHeader>
                        <DialogTitle>Aggiungi/Aggiorna API Key</DialogTitle>
                      </DialogHeader>
                      <div className="space-y-4 py-4">
                        <div className="space-y-2">
                          <Label htmlFor="service">Servizio</Label>
                          <Input id="service" placeholder="es. Shodan API" />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="apikey">API Key</Label>
                          <Input id="apikey" type="password" placeholder="Inserisci la tua API key..." />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="description">Descrizione (opzionale)</Label>
                          <Input id="description" placeholder="Descrizione del servizio..." />
                        </div>
                        <div className="flex justify-end gap-2">
                          <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                            Annulla
                          </Button>
                          <Button onClick={() => setIsDialogOpen(false)}>
                            Salva
                          </Button>
                        </div>
                      </div>
                    </DialogContent>
                  </Dialog>
                </div>

                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nome</TableHead>
                      <TableHead>Servizio</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Ultimo Uso</TableHead>
                      <TableHead>Azioni</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {apiKeys.map((api) => (
                      <TableRow key={api.id}>
                        <TableCell className="font-medium">{api.name}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{api.service}</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge 
                            variant={
                              api.status === 'active' ? 'default' : 
                              api.status === 'inactive' ? 'secondary' : 
                              'destructive'
                            }
                            className="gap-1"
                          >
                            {api.status === 'active' && <CheckCircle className="w-3 h-3" />}
                            {api.status === 'expired' && <AlertTriangle className="w-3 h-3" />}
                            {api.status === 'active' ? 'Attiva' : 
                             api.status === 'inactive' ? 'Inattiva' : 'Scaduta'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">{api.lastUsed}</TableCell>
                        <TableCell className="space-x-2">
                          <Button variant="ghost" size="sm">
                            <Edit className="w-3 h-3 mr-1" />
                            Modifica
                          </Button>
                          <Button variant="ghost" size="sm" className="text-destructive">
                            <Trash2 className="w-3 h-3 mr-1" />
                            Rimuovi
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TerminalCard>

            {/* API Usage Stats */}
            <TerminalCard title="Statistiche Utilizzo API" variant="default">
              <div className="grid md:grid-cols-3 gap-4">
                <div className="bg-secondary/20 p-4 rounded-lg border border-border text-center">
                  <Key className="w-6 h-6 text-cyber-green mx-auto mb-2" />
                  <div className="text-2xl font-bold text-cyber-green">4</div>
                  <div className="text-sm text-muted-foreground">API Keys Totali</div>
                </div>
                
                <div className="bg-secondary/20 p-4 rounded-lg border border-border text-center">
                  <CheckCircle className="w-6 h-6 text-cyber-blue mx-auto mb-2" />
                  <div className="text-2xl font-bold text-cyber-blue">2</div>
                  <div className="text-sm text-muted-foreground">Keys Attive</div>
                </div>
                
                <div className="bg-secondary/20 p-4 rounded-lg border border-border text-center">
                  <AlertTriangle className="w-6 h-6 text-cyber-red mx-auto mb-2" />
                  <div className="text-2xl font-bold text-cyber-red">1</div>
                  <div className="text-sm text-muted-foreground">Keys Scadute</div>
                </div>
              </div>
            </TerminalCard>
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
};

export default SystemPage; 