import { useState } from "react";
import { Layout } from "@/components/Layout";
import { TerminalCard } from "@/components/TerminalCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { 
  Globe, 
  Mail, 
  UserSearch, 
  Database,
  Download,
  Shield,
  ExternalLink,
  CheckCircle,
  AlertCircle,
  Clock
} from "lucide-react";

const ProfilingPage = () => {
  const [activeTab, setActiveTab] = useState("domain");
  const [target, setTarget] = useState("");
  const [isScanning, setIsScanning] = useState(false);
  const [results, setResults] = useState<any>(null);

  const mockScan = async () => {
    setIsScanning(true);
    // Simulate API call
    setTimeout(() => {
      setResults({
        domain: {
          whois: { registrar: "GoDaddy", created: "2015-03-15", expires: "2025-03-15" },
          dns: [
            { type: "A", value: "192.168.1.1" },
            { type: "MX", value: "mail.example.com" },
            { type: "NS", value: "ns1.example.com" }
          ],
          subdomains: ["www", "mail", "api", "admin"],
          technologies: ["React", "Cloudflare", "Google Analytics"]
        },
        email: {
          validity: "valid",
          breaches: ["LinkedIn 2021", "Adobe 2013"],
          social: ["LinkedIn", "Twitter"],
          reputation: "clean"
        },
        username: {
          platforms: [
            { name: "GitHub", found: true, url: "github.com/user" },
            { name: "Twitter", found: true, url: "twitter.com/user" },
            { name: "LinkedIn", found: false, url: null },
            { name: "Instagram", found: true, url: "instagram.com/user" }
          ]
        }
      });
      setIsScanning(false);
    }, 3000);
  };

  const savedProfiles = [
    { id: 1, target: "example.com", type: "domain", date: "2024-01-15", status: "completed" },
    { id: 2, target: "user@example.com", type: "email", date: "2024-01-14", status: "completed" },
    { id: 3, target: "johndoe", type: "username", date: "2024-01-13", status: "in-progress" }
  ];

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <UserSearch className="w-6 h-6 text-cyber-green" />
          <h1 className="text-2xl font-bold text-foreground">Investigazione OSINT</h1>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="domain">Dominio/IP</TabsTrigger>
            <TabsTrigger value="email">Email</TabsTrigger>
            <TabsTrigger value="username">Username</TabsTrigger>
            <TabsTrigger value="profiles">Profili Salvati</TabsTrigger>
          </TabsList>

          <TabsContent value="domain" className="space-y-4">
            <TerminalCard title="Analisi OSINT Dominio/IP" variant="default">
              <div className="space-y-4">
                <div className="flex gap-2">
                  <Input 
                    placeholder="Inserisci dominio o IP..." 
                    value={target}
                    onChange={(e) => setTarget(e.target.value)}
                    className="font-mono"
                  />
                  <Button 
                    onClick={mockScan} 
                    disabled={isScanning || !target}
                    className="min-w-24"
                  >
                    {isScanning ? <Clock className="w-4 h-4 animate-spin" /> : <Globe className="w-4 h-4" />}
                    {isScanning ? "Scansione..." : "Analizza"}
                  </Button>
                </div>

                {results?.domain && (
                  <div className="grid md:grid-cols-2 gap-4 mt-6">
                    <div className="bg-secondary/20 p-4 rounded-lg border border-border">
                      <h4 className="font-semibold text-cyber-green mb-3 flex items-center gap-2">
                        <Shield className="w-4 h-4" />
                        WHOIS Info
                      </h4>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Registrar:</span>
                          <span>{results.domain.whois.registrar}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Creato:</span>
                          <span>{results.domain.whois.created}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Scade:</span>
                          <span>{results.domain.whois.expires}</span>
                        </div>
                      </div>
                    </div>

                    <div className="bg-secondary/20 p-4 rounded-lg border border-border">
                      <h4 className="font-semibold text-cyber-amber mb-3">DNS Records</h4>
                      <div className="space-y-1 text-sm">
                        {results.domain.dns.map((record: any, i: number) => (
                          <div key={i} className="flex justify-between font-mono">
                            <Badge variant="outline" className="mr-2">{record.type}</Badge>
                            <span className="text-muted-foreground">{record.value}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="bg-secondary/20 p-4 rounded-lg border border-border">
                      <h4 className="font-semibold text-cyber-blue mb-3">Subdomains</h4>
                      <div className="flex flex-wrap gap-2">
                        {results.domain.subdomains.map((sub: string, i: number) => (
                          <Badge key={i} variant="secondary" className="font-mono">
                            {sub}.{target}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    <div className="bg-secondary/20 p-4 rounded-lg border border-border">
                      <h4 className="font-semibold text-cyber-green mb-3">Technologies</h4>
                      <div className="flex flex-wrap gap-2">
                        {results.domain.technologies.map((tech: string, i: number) => (
                          <Badge key={i} variant="outline">
                            {tech}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </TerminalCard>
          </TabsContent>

          <TabsContent value="email" className="space-y-4">
            <TerminalCard title="Profila indirizzo email" variant="default">
              <div className="space-y-4">
                <div className="flex gap-2">
                  <Input 
                    placeholder="Inserisci email..." 
                    type="email"
                    value={target}
                    onChange={(e) => setTarget(e.target.value)}
                    className="font-mono"
                  />
                  <Button 
                    onClick={mockScan} 
                    disabled={isScanning || !target}
                    className="min-w-24"
                  >
                    {isScanning ? <Clock className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4" />}
                    {isScanning ? "Verifica..." : "Verifica"}
                  </Button>
                </div>

                {results?.email && (
                  <div className="grid md:grid-cols-2 gap-4 mt-6">
                    <div className="bg-secondary/20 p-4 rounded-lg border border-border">
                      <h4 className="font-semibold text-cyber-green mb-3 flex items-center gap-2">
                        <CheckCircle className="w-4 h-4" />
                        Validità Email
                      </h4>
                      <Badge variant={results.email.validity === 'valid' ? 'default' : 'destructive'}>
                        {results.email.validity === 'valid' ? 'Valida' : 'Non valida'}
                      </Badge>
                    </div>

                    <div className="bg-secondary/20 p-4 rounded-lg border border-border">
                      <h4 className="font-semibold text-cyber-red mb-3 flex items-center gap-2">
                        <AlertCircle className="w-4 h-4" />
                        Data Breaches
                      </h4>
                      <div className="space-y-1">
                        {results.email.breaches.map((breach: string, i: number) => (
                          <Badge key={i} variant="destructive" className="mr-1">
                            {breach}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    <div className="bg-secondary/20 p-4 rounded-lg border border-border">
                      <h4 className="font-semibold text-cyber-blue mb-3">Social Media</h4>
                      <div className="flex flex-wrap gap-2">
                        {results.email.social.map((platform: string, i: number) => (
                          <Badge key={i} variant="outline">
                            {platform}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    <div className="bg-secondary/20 p-4 rounded-lg border border-border">
                      <h4 className="font-semibold text-cyber-green mb-3">Reputation</h4>
                      <Badge variant="default">{results.email.reputation}</Badge>
                    </div>
                  </div>
                )}
              </div>
            </TerminalCard>
          </TabsContent>

          <TabsContent value="username" className="space-y-4">
            <TerminalCard title="Ricerca username sui social media" variant="default">
              <div className="space-y-4">
                <div className="flex gap-2">
                  <Input 
                    placeholder="Inserisci username..." 
                    value={target}
                    onChange={(e) => setTarget(e.target.value)}
                    className="font-mono"
                  />
                  <Button 
                    onClick={mockScan} 
                    disabled={isScanning || !target}
                    className="min-w-24"
                  >
                    {isScanning ? <Clock className="w-4 h-4 animate-spin" /> : <UserSearch className="w-4 h-4" />}
                    {isScanning ? "Cerca..." : "Cerca"}
                  </Button>
                </div>

                {results?.username && (
                  <div className="mt-6">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Piattaforma</TableHead>
                          <TableHead>Stato</TableHead>
                          <TableHead>Profilo</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {results.username.platforms.map((platform: any, i: number) => (
                          <TableRow key={i}>
                            <TableCell className="font-medium">{platform.name}</TableCell>
                            <TableCell>
                              <Badge variant={platform.found ? "default" : "secondary"}>
                                {platform.found ? "Trovato" : "Non trovato"}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              {platform.found && platform.url ? (
                                <Button variant="ghost" size="sm" asChild>
                                  <a href={`https://${platform.url}`} target="_blank" rel="noopener noreferrer">
                                    <ExternalLink className="w-3 h-3 mr-1" />
                                    Visita
                                  </a>
                                </Button>
                              ) : (
                                <span className="text-muted-foreground">-</span>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </div>
            </TerminalCard>
          </TabsContent>

          <TabsContent value="profiles" className="space-y-4">
            <TerminalCard title="Profili OSINT salvati" variant="default">
              <div className="space-y-4">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Target</TableHead>
                      <TableHead>Tipo</TableHead>
                      <TableHead>Data</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Azioni</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {savedProfiles.map((profile) => (
                      <TableRow key={profile.id}>
                        <TableCell className="font-mono">{profile.target}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{profile.type}</Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">{profile.date}</TableCell>
                        <TableCell>
                          <Badge variant={profile.status === 'completed' ? 'default' : 'secondary'}>
                            {profile.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="space-x-2">
                          <Button variant="ghost" size="sm">
                            <Database className="w-3 h-3 mr-1" />
                            Analizza
                          </Button>
                          <Button variant="ghost" size="sm">
                            <Download className="w-3 h-3 mr-1" />
                            Esporta
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TerminalCard>
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
};

export default ProfilingPage; 