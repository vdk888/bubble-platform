import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { authAPI } from '../../services/api';
import { User } from '../../types';

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<boolean>;
  register: (email: string, password: string, full_name?: string) => Promise<boolean>;
  logout: () => Promise<void>;
  isLoading: boolean;
  error: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      // Validate token and get user info
      authAPI.me()
        .then(response => {
          if (response.success && response.data) {
            setUser(response.data);
          } else {
            console.log('❌ Token validation failed - clearing tokens');
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            setUser(null);
          }
        })
        .catch((error) => {
          console.log('❌ Token validation error - clearing tokens:', error.response?.status);
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          setUser(null);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (email: string, password: string): Promise<boolean> => {
    console.log('🔐 AuthProvider.login called with:', { email, passwordLength: password.length });
    setIsLoading(true);
    setError(null);
    try {
      console.log('🌐 Making API call to login endpoint...');
      const response = await authAPI.login(email, password);
      console.log('📨 API Response:', {
        success: response.success,
        hasAccessToken: !!response.access_token,
        hasRefreshToken: !!response.refresh_token,
        hasUser: !!response.user
      });
      
      if (response.success && response.access_token && response.refresh_token) {
        console.log('✅ Login successful, storing tokens...');
        localStorage.setItem('access_token', response.access_token);
        localStorage.setItem('refresh_token', response.refresh_token);
        // User data is in response.user for AuthResponse structure
        setUser(response.user || null);
        console.log('👤 User set:', response.user);
        return true;
      } else {
        console.log('❌ Login failed - missing required fields');
        setError('Login failed');
        return false;
      }
    } catch (err: any) {
      console.log('Login error:', err.response?.data);
      if (err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          // Handle Pydantic validation errors
          const errorMessages = err.response.data.detail.map((e: any) => e.msg).join(', ');
          setError(errorMessages);
        } else {
          setError(err.response.data.detail);
        }
      } else {
        setError('Login failed');
      }
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string, full_name?: string): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await authAPI.register(email, password, full_name);
      if (response.success && response.access_token && response.refresh_token) {
        localStorage.setItem('access_token', response.access_token);
        localStorage.setItem('refresh_token', response.refresh_token);
        // User data is in response.user for AuthResponse structure
        setUser(response.user || null);
        return true;
      } else {
        setError('Registration failed');
        return false;
      }
    } catch (err: any) {
      console.log('Registration error:', err.response?.data);
      if (err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          // Handle Pydantic validation errors
          const errorMessages = err.response.data.detail.map((e: any) => e.msg).join(', ');
          setError(errorMessages);
        } else {
          setError(err.response.data.detail);
        }
      } else {
        setError('Registration failed');
      }
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    setIsLoading(true);
    try {
      await authAPI.logout();
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setUser(null);
      setIsLoading(false);
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, isLoading, error }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}