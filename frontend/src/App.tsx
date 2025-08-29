import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import UniverseDashboard from './components/universe/UniverseDashboard';
import { AuthProvider, useAuth } from './components/auth/AuthProvider';
import { AuthPage } from './components/auth/AuthPage';
import './index.css';


// Protected Route Component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();

  console.log('🛡️ ProtectedRoute rendered:', { hasUser: !!user, isLoading });

  if (isLoading) {
    console.log('⏳ Showing loading state');
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  if (!user) {
    console.log('❌ No user, redirecting to /auth');
    return <Navigate to="/auth" replace />;
  }

  console.log('✅ User authenticated, showing protected content');
  return <>{children}</>;
}

function AppRoutes() {
  const { user, isLoading } = useAuth();
  
  console.log('🔄 AppRoutes rendered:', { 
    hasUser: !!user, 
    userId: user?.id, 
    isLoading,
    currentPath: window.location.pathname 
  });
  
  // Clear any expired tokens on app start to prevent reload loops
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      try {
        // Check if token is expired by parsing JWT
        const payload = JSON.parse(atob(token.split('.')[1]));
        const now = Math.floor(Date.now() / 1000);
        if (payload.exp && payload.exp < now) {
          console.log('🧹 Clearing expired token to prevent reload loop');
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
        }
      } catch (error) {
        console.log('🧹 Clearing invalid token to prevent reload loop');
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      }
    }
  }, []);

  return (
    <div className="App">
      <Routes>
        <Route 
          path="/auth" 
          element={
            user ? <Navigate to="/universes" replace /> : <AuthPage />
          } 
        />
        <Route 
          path="/" 
          element={
            user ? <Navigate to="/universes" replace /> : <Navigate to="/auth" replace />
          } 
        />
        <Route 
          path="/universes" 
          element={
            <ProtectedRoute>
              <UniverseDashboard />
            </ProtectedRoute>
          } 
        />
        {/* Add more protected routes as we build other components */}
      </Routes>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <AppRoutes />
      </Router>
    </AuthProvider>
  );
}

export default App;