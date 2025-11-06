import { Layout } from "@/components/Layout";
import { TerminalCard } from "@/components/TerminalCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { 
  Download, 
  FileText, 
  FolderTree,
  Play,
  Upload
} from "lucide-react";
import { useState } from "react";

const CrawlPage = () => {
  const [url, setUrl] = useState("");
  const [depth, setDepth] = useState("2");
  const [isRunning, setIsRunning] = useState(false);

  const handleSingleDownload = () => {
    setIsRunning(true);
    // Simulate download process
    setTimeout(() => setIsRunning(false), 3000);
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <Download className="w-8 h-8 text-primary" />
            <div>
              <h1 className="text-3xl font-bold tracking-wider">CRAWL & DOWNLOAD</h1>
              <p className="text-muted-foreground">Download pagine HTML e crawling ricorsivo</p>
            </div>
          </div>
        </div>

        <Tabs defaultValue="single" className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="single">Download Singolo</TabsTrigger>
            <TabsTrigger value="multiple">Download Multiplo</TabsTrigger>
            <TabsTrigger value="crawl">Crawl Struttura</TabsTrigger>
          </TabsList>

          {/* Single Page Download */}
          <TabsContent value="single">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <TerminalCard title="single_download.config">
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="url">URL Target</Label>
                    <Input
                      id="url"
                      placeholder="https://example.com"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      className="font-mono"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Include Assets</Label>
                      <div className="flex gap-2 mt-2">
                        <Badge variant="secondary">CSS</Badge>
                        <Badge variant="secondary">JS</Badge>
                        <Badge variant="secondary">Images</Badge>
                      </div>
                    </div>
                    <div>
                      <Label>Formato Output</Label>
                      <div className="flex gap-2 mt-2">
                        <Badge variant="outline">HTML</Badge>
                        <Badge variant="outline">PDF</Badge>
                      </div>
                    </div>
                  </div>

                  <Button 
                    onClick={handleSingleDownload}
                    disabled={!url || isRunning}
                    className="w-full"
                  >
                    <Play className="w-4 h-4 mr-2" />
                    {isRunning ? "Download in corso..." : "Avvia Download"}
                  </Button>
                </div>
              </TerminalCard>

              <TerminalCard title="download.log" variant={isRunning ? "warning" : "default"}>
                <div className="space-y-2 font-mono text-sm">
                  <div className="text-cyber-green">→ Sistema pronto per download</div>
                  <div className="text-muted-foreground">→ Parser HTML inizializzato</div>
                  <div className="text-muted-foreground">→ Asset extractor attivo</div>
                  {isRunning && (
                    <>
                      <div className="text-cyber-amber">→ Downloading: {url}</div>
                      <div className="text-cyber-amber pulse-cyber">→ Processing HTML structure...</div>
                    </>
                  )}
                </div>
              </TerminalCard>
            </div>
          </TabsContent>

          {/* Multiple Download */}
          <TabsContent value="multiple">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <TerminalCard title="multiple_download.config">
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="urls">Lista URL (uno per riga)</Label>
                    <Textarea
                      id="urls"
                      placeholder="https://example1.com&#10;https://example2.com&#10;https://example3.com"
                      rows={6}
                      className="font-mono"
                    />
                  </div>

                  <div className="flex items-center gap-4">
                    <Button variant="outline" className="flex-1">
                      <Upload className="w-4 h-4 mr-2" />
                      Carica File TXT
                    </Button>
                    <Button className="flex-1">
                      <Play className="w-4 h-4 mr-2" />
                      Avvia Batch Download
                    </Button>
                  </div>
                </div>
              </TerminalCard>

              <TerminalCard title="batch.progress">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Progresso Batch</span>
                    <span className="text-sm text-muted-foreground">0 / 0</span>
                  </div>
                  <div className="w-full bg-secondary rounded-full h-2">
                    <div className="bg-primary h-2 rounded-full transition-all duration-300" style={{ width: "0%" }}></div>
                  </div>
                  <div className="text-sm text-muted-foreground font-mono">
                    Nessun processo attivo
                  </div>
                </div>
              </TerminalCard>
            </div>
          </TabsContent>

          {/* Website Crawl */}
          <TabsContent value="crawl">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <TerminalCard title="crawl.config">
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
                      <Label htmlFor="depth">Profondità Max</Label>
                      <Input
                        id="depth"
                        type="number"
                        value={depth}
                        onChange={(e) => setDepth(e.target.value)}
                        min="1"
                        max="10"
                      />
                    </div>
                    <div>
                      <Label>Delay (ms)</Label>
                      <Input
                        type="number"
                        placeholder="1000"
                        defaultValue="1000"
                      />
                    </div>
                  </div>

                  <div>
                    <Label>Filtri Pagina</Label>
                    <div className="flex gap-2 mt-2 flex-wrap">
                      <Badge variant="secondary">Stesso dominio</Badge>
                      <Badge variant="outline">Escl. Media</Badge>
                      <Badge variant="outline">Solo HTML</Badge>
                    </div>
                  </div>

                  <Button className="w-full">
                    <FolderTree className="w-4 h-4 mr-2" />
                    Avvia Crawl Struttura
                  </Button>
                </div>
              </TerminalCard>

              <TerminalCard title="crawl.tree">
                <div className="space-y-2 font-mono text-sm">
                  <div className="text-muted-foreground">Struttura sito (preview):</div>
                  <div className="pl-4 space-y-1">
                    <div className="text-cyber-green">├─ /index.html</div>
                    <div className="text-cyber-green">├─ /about.html</div>
                    <div className="text-muted-foreground">├─ /products/</div>
                    <div className="text-cyber-green pl-4">├─ /products/item1.html</div>
                    <div className="text-cyber-green pl-4">└─ /products/item2.html</div>
                    <div className="text-muted-foreground">└─ /contact.html</div>
                  </div>
                  <div className="text-xs text-muted-foreground pt-2">
                    Avvia crawl per analizzare struttura completa
                  </div>
                </div>
              </TerminalCard>
            </div>
          </TabsContent>
        </Tabs>

        {/* Recent Downloads */}
        <TerminalCard title="recent_downloads.log">
          <div className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <FileText className="w-5 h-5 text-primary" />
              Download Recenti
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between p-2 bg-secondary/30 rounded">
                <span className="font-mono">example.com/page1.html</span>
                <span className="text-xs text-muted-foreground">2 ore fa</span>
              </div>
              <div className="flex items-center justify-between p-2 bg-secondary/30 rounded">
                <span className="font-mono">target-site.org/about.html</span>
                <span className="text-xs text-muted-foreground">5 ore fa</span>
              </div>
              <div className="flex items-center justify-between p-2 bg-secondary/30 rounded">
                <span className="font-mono">research.edu/papers/</span>
                <span className="text-xs text-muted-foreground">1 giorno fa</span>
              </div>
            </div>
          </div>
        </TerminalCard>
      </div>
    </Layout>
  );
};

export default CrawlPage; 