import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import UniverseDashboard from './components/universe/UniverseDashboard';
import { AuthProvider, useAuth } from './components/auth/AuthProvider';
import { AuthPage } from './components/auth/AuthPage';
import './index.css';

// Development authentication - directly in React component
const DEV_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmN2YxNmM4ZS0yMTI1LTQxYjEtYjQwMi1lZjBlYjJlMDM0M2UiLCJlbWFpbCI6ImpvcmlzODg4QGhvdG1haWwuZnIiLCJyb2xlIjoidXNlciIsInN1YnNjcmlwdGlvbl90aWVyIjoiZnJlZSIsImlhdCI6MTc1NjA3MjcwOSwiZXhwIjoxNzU2MDc0NTA5LCJqdGkiOiIwZjI1cVJQek5IWFkyX1BNN1RsQ25faFNIZlB4aGdWX0tZQmg4Mm5sdFFrIiwidHlwZSI6ImFjY2Vzc190b2tlbiJ9.sCLooBMBvyymOGv50rQgINNqY8-EUWVed0yTewiM71g";

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
  
  // Force set authentication token in development for quick testing
  useEffect(() => {
    if (process.env.NODE_ENV === 'development' && !localStorage.getItem('access_token')) {
      console.log('🔄 SETTING FRESH TOKEN IN REACT APP');
      localStorage.setItem('access_token', DEV_TOKEN);
      console.log('✅ Token set successfully:', DEV_TOKEN.substring(0, 50) + '...');
      window.location.reload(); // Refresh to trigger auth validation
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