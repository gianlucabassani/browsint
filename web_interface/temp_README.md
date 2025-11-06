# Browsint Web Interface

Modern React-based web interface for the Browsint OSINT toolkit.

## Features

- **Dashboard**: Overview of system status, database info, and API keys
- **Web Crawl & Download**: Single page download, batch download, and website crawling
- **OSINT Web Scraping**: Page analysis with OSINT data extraction
- **Profilazione OSINT**: Domain, email, and username investigation
- **System Options**: Database management and API key configuration

## Tech Stack

- **Frontend**: React 18 + TypeScript + Vite
- **UI Components**: Radix UI + Tailwind CSS
- **Styling**: Custom cyber theme with terminal aesthetics
- **Routing**: React Router DOM
- **Backend**: FastAPI (Python)

## Development Setup

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Python 3.8+ with FastAPI

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start development server:
```bash
npm run dev
```

The React app will be available at `http://localhost:3000`

### Building for Production

1. Build the React app:
```bash
npm run build
```

2. The built files will be in `dist/` directory

3. Start the FastAPI server:
```bash
python app.py
```

The web interface will be available at `http://localhost:8000`

## Project Structure

```
web_interface/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── ui/             # Radix UI components
│   │   ├── Layout.tsx      # Main layout component
│   │   ├── Navigation.tsx  # Sidebar navigation
│   │   └── TerminalCard.tsx # Terminal-style card component
│   ├── pages/              # Page components
│   │   ├── Index.tsx       # Dashboard
│   │   ├── CrawlPage.tsx   # Web crawling interface
│   │   ├── ScrapingPage.tsx # OSINT scraping interface
│   │   ├── ProfilingPage.tsx # OSINT profiling interface
│   │   ├── SystemPage.tsx  # System management
│   │   └── NotFound.tsx    # 404 page
│   ├── lib/                # Utility functions
│   ├── hooks/              # Custom React hooks
│   ├── App.tsx             # Main app component
│   ├── main.tsx            # Entry point
│   └── index.css           # Global styles
├── dist/                   # Built files (after npm run build)
├── package.json            # Dependencies and scripts
├── vite.config.ts          # Vite configuration
├── tailwind.config.ts      # Tailwind CSS configuration
├── tsconfig.json           # TypeScript configuration
└── app.py                  # FastAPI backend
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## API Integration (TODO)

The React frontend communicates with the FastAPI backend through REST API endpoints:

- `/api/status` - System status
- `/api/download/*` - Download and crawling operations
- `/api/osint/*` - OSINT analysis operations
- `/api/database/*` - Database management
- `/api/keys` - API key management

