import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import UniverseDashboard from './components/universe/UniverseDashboard';
import './index.css';
import './devAuth.js'; // Development authentication

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          {/* For now, redirect to universe dashboard */}
          <Route path="/" element={<Navigate to="/universes" replace />} />
          <Route path="/universes" element={<UniverseDashboard />} />
          {/* Add more routes as we build other components */}
        </Routes>
      </div>
    </Router>
  );
}

export default App;