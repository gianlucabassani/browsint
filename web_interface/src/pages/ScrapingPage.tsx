import { Layout } from "@/components/Layout";
import { TerminalCard } from "@/components/TerminalCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { 
  Search, 
  Target, 
  Database, 
  FileText,
  Mail,
  Phone,
  ExternalLink,
  Download
} from "lucide-react";
import { useState } from "react";

const ScrapingPage = () => {
  const [targetUrl, setTargetUrl] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [extractedData] = useState({
    emails: ["contact@example.com", "support@example.com"],
    phones: ["+39 123 456 7890", "+39 098 765 4321"],
    links: ["https://facebook.com/example", "https://linkedin.com/company/example"],
    metadata: {
      title: "Example Company - Homepage",
      description: "Leading company in technology solutions",
      keywords: "technology, solutions, services"
    }
  });

  const handleAnalyze = () => {
    setIsAnalyzing(true);
    setTimeout(() => setIsAnalyzing(false), 2500);
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <Search className="w-8 h-8 text-primary" />
            <div>
              <h1 className="text-3xl font-bold tracking-wider">OSINT SCRAPING</h1>
              <p className="text-muted-foreground">Estrazione dati OSINT da pagine web</p>
            </div>
          </div>
        </div>

        <Tabs defaultValue="single" className="space-y-6">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="single">Analisi Singola Pagina</TabsTrigger>
            <TabsTrigger value="crawl">Crawl con Estrazione</TabsTrigger>
          </TabsList>

          {/* Single Page Analysis */}
          <TabsContent value="single">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Configuration Panel */}
              <TerminalCard title="target.config">
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="target-url">URL Target</Label>
                    <Input
                      id="target-url"
                      placeholder="https://example.com"
                      value={targetUrl}
                      onChange={(e) => setTargetUrl(e.target.value)}
                      className="font-mono"
                    />
                  </div>

                  <div className="space-y-3">
                    <Label>Dati da Estrarre</Label>
                    <div className="space-y-2">
                      <div className="flex items-center space-x-2">
                        <Checkbox id="emails" defaultChecked />
                        <label htmlFor="emails" className="text-sm">Indirizzi Email</label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Checkbox id="phones" defaultChecked />
                        <label htmlFor="phones" className="text-sm">Numeri Telefono</label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Checkbox id="social" defaultChecked />
                        <label htmlFor="social" className="text-sm">Link Social Media</label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Checkbox id="metadata" defaultChecked />
                        <label htmlFor="metadata" className="text-sm">Metadata Pagina</label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Checkbox id="forms" />
                        <label htmlFor="forms" className="text-sm">Form e Input</label>
                      </div>
                    </div>
                  </div>

                  <Button 
                    onClick={handleAnalyze}
                    disabled={!targetUrl || isAnalyzing}
                    className="w-full"
                  >
                    <Target className="w-4 h-4 mr-2" />
                    {isAnalyzing ? "Analisi in corso..." : "Avvia Analisi"}
                  </Button>
                </div>
              </TerminalCard>

              {/* Analysis Log */}
              <TerminalCard title="analysis.log" variant={isAnalyzing ? "warning" : "default"}>
                <div className="space-y-2 font-mono text-sm">
                  <div className="text-cyber-green">→ OSINT Parser inizializzato</div>
                  <div className="text-muted-foreground">→ Regex patterns caricati</div>
                  <div className="text-muted-foreground">→ Social media extractors attivi</div>
                  {isAnalyzing && (
                    <>
                      <div className="text-cyber-amber">→ Connessione: {targetUrl}</div>
                      <div className="text-cyber-amber pulse-cyber">→ Scanning HTML content...</div>
                      <div className="text-cyber-amber">→ Extracting contact data...</div>
                    </>
                  )}
                  {!isAnalyzing && targetUrl && (
                    <div className="text-cyber-green">→ Pronto per nuova analisi</div>
                  )}
                </div>
              </TerminalCard>

              {/* Results Panel */}
              <TerminalCard title="extraction.results" variant="success">
                <div className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Mail className="w-4 h-4 text-primary" />
                      <span className="font-semibold text-sm">Email ({extractedData.emails.length})</span>
                    </div>
                    {extractedData.emails.map((email, idx) => (
                      <div key={idx} className="bg-secondary/30 p-2 rounded font-mono text-xs">
                        {email}
                      </div>
                    ))}
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Phone className="w-4 h-4 text-primary" />
                      <span className="font-semibold text-sm">Telefoni ({extractedData.phones.length})</span>
                    </div>
                    {extractedData.phones.map((phone, idx) => (
                      <div key={idx} className="bg-secondary/30 p-2 rounded font-mono text-xs">
                        {phone}
                      </div>
                    ))}
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <ExternalLink className="w-4 h-4 text-primary" />
                      <span className="font-semibold text-sm">Social Links ({extractedData.links.length})</span>
                    </div>
                    {extractedData.links.map((link, idx) => (
                      <div key={idx} className="bg-secondary/30 p-2 rounded font-mono text-xs break-all">
                        {link}
                      </div>
                    ))}
                  </div>
                </div>
              </TerminalCard>
            </div>

            {/* Metadata Results */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
              <TerminalCard title="metadata.analysis">
                <div className="space-y-4">
                  <h3 className="font-semibold flex items-center gap-2">
                    <FileText className="w-5 h-5 text-primary" />
                    Metadata Pagina
                  </h3>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="text-muted-foreground">Titolo:</span>
                      <div className="font-mono bg-secondary/30 p-2 rounded mt-1">
                        {extractedData.metadata.title}
                      </div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Descrizione:</span>
                      <div className="font-mono bg-secondary/30 p-2 rounded mt-1">
                        {extractedData.metadata.description}
                      </div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Keywords:</span>
                      <div className="font-mono bg-secondary/30 p-2 rounded mt-1">
                        {extractedData.metadata.keywords}
                      </div>
                    </div>
                  </div>
                </div>
              </TerminalCard>

              <TerminalCard title="export.options">
                <div className="space-y-4">
                  <h3 className="font-semibold flex items-center gap-2">
                    <Download className="w-5 h-5 text-primary" />
                    Esporta Risultati
                  </h3>
                  <div className="grid grid-cols-3 gap-2">
                    <Button variant="outline" size="sm">JSON</Button>
                    <Button variant="outline" size="sm">HTML</Button>
                    <Button variant="outline" size="sm">PDF</Button>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Checkbox id="include-metadata" defaultChecked />
                      <label htmlFor="include-metadata" className="text-sm">Include Metadata</label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox id="timestamp" defaultChecked />
                      <label htmlFor="timestamp" className="text-sm">Timestamp Analisi</label>
                    </div>
                  </div>
                  <Button className="w-full">
                    <Download className="w-4 h-4 mr-2" />
                    Esporta Report
                  </Button>
                </div>
              </TerminalCard>
            </div>
          </TabsContent>

          {/* Crawl with Extraction */}
          <TabsContent value="crawl">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <TerminalCard title="crawl_extraction.config">
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="crawl-url">URL Base</Label>
                    <Input
                      id="crawl-url"
                      placeholder="https://example.com"
                      className="font-mono"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Profondità Max</Label>
                      <Input type="number" defaultValue="3" min="1" max="10" />
                    </div>
                    <div>
                      <Label>Delay (ms)</Label>
                      <Input type="number" defaultValue="2000" />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Modalità Estrazione</Label>
                    <div className="flex gap-2 flex-wrap">
                      <Badge variant="secondary">Contact Info</Badge>
                      <Badge variant="secondary">Social Links</Badge>
                      <Badge variant="outline">Form Data</Badge>
                      <Badge variant="outline">Technical Info</Badge>
                    </div>
                  </div>

                  <Button className="w-full">
                    <Database className="w-4 h-4 mr-2" />
                    Avvia Crawl + Estrazione
                  </Button>
                </div>
              </TerminalCard>

              <TerminalCard title="crawl.progress">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Pagine Processate</span>
                    <span className="text-sm text-muted-foreground">0 / 0</span>
                  </div>
                  <div className="w-full bg-secondary rounded-full h-2">
                    <div className="bg-primary h-2 rounded-full transition-all duration-300"></div>
                  </div>
                  <div className="space-y-2 font-mono text-sm">
                    <div className="text-muted-foreground">Crawler inattivo</div>
                    <div className="text-muted-foreground">Email trovate: 0</div>
                    <div className="text-muted-foreground">Telefoni trovati: 0</div>
                    <div className="text-muted-foreground">Link social: 0</div>
                  </div>
                </div>
              </TerminalCard>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
};

export default ScrapingPage; 