// ECO-SHIELD React App — root component with routing
import React, { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import TopNav from './components/TopNav';
import { AnalysisProvider } from './context/AnalysisContext';

// Pages
import Dashboard from './pages/Dashboard';
import Scenarios from './pages/Scenarios';
import Upload from './pages/Upload';
import Explorer from './pages/Explorer';
import Anomalies from './pages/Anomalies';
import Diagnosis from './pages/Diagnosis';
import Recommendations from './pages/Recommendations';
import History from './pages/History';
import Settings from './pages/Settings';

export default function App() {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  return (
    <BrowserRouter>
      <AnalysisProvider>
        <div className="app-shell">
          <Sidebar
            isOpen={mobileSidebarOpen}
            onClose={() => setMobileSidebarOpen(false)}
          />
          <div className="main-content">
            <TopNav onToggleSidebar={() => setMobileSidebarOpen((prev) => !prev)} />
            <main className="page-content">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/scenarios" element={<Scenarios />} />
                <Route path="/upload" element={<Upload />} />
                <Route path="/explorer" element={<Explorer />} />
                <Route path="/anomalies" element={<Anomalies />} />
                <Route path="/diagnosis" element={<Diagnosis />} />
                <Route path="/recommendations" element={<Recommendations />} />
                <Route path="/history" element={<History />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="*" element={
                  <div style={{ padding: 60, textAlign: 'center' }}>
                    <div style={{ fontSize: 48, fontWeight: 700, color: 'var(--text-tertiary)' }}>404</div>
                    <div style={{ fontSize: 18, fontWeight: 600, marginTop: 12 }}>Page not found</div>
                  </div>
                } />
              </Routes>
            </main>
          </div>
        </div>
      </AnalysisProvider>
    </BrowserRouter>
  );
}
