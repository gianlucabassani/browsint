import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import CrawlPage from "./pages/CrawlPage";
import ScrapingPage from "./pages/ScrapingPage";
import ProfilingPage from "./pages/ProfilingPage";
import SystemPage from "./pages/SystemPage";
import NotFound from "./pages/NotFound";

const App = () => (
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<Index />} />
      <Route path="/crawl" element={<CrawlPage />} />
      <Route path="/scraping" element={<ScrapingPage />} />
      <Route path="/profiling" element={<ProfilingPage />} />
      <Route path="/system" element={<SystemPage />} />
      {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  </BrowserRouter>
);

export default App; 