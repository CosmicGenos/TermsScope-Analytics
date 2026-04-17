import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getCurrentUser } from '../services/api';

interface User {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: () => void;
  logout: () => void;
  setToken: (token: string) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(
    localStorage.getItem('termsscope_token')
  );
  const [isLoading, setIsLoading] = useState(!!localStorage.getItem('termsscope_token'));

  const setToken = useCallback((newToken: string) => {
    localStorage.setItem('termsscope_token', newToken);
    setTokenState(newToken);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('termsscope_token');
    setTokenState(null);
    setUser(null);
  }, []);

  const login = useCallback(() => {
    // Redirect to backend Google OAuth endpoint
    window.location.href = '/api/auth/google/login';
  }, []);

  // Hydrate user on mount or token change
  useEffect(() => {
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    setIsLoading(true);

    getCurrentUser()
      .then((res) => {
        if (!cancelled) {
          setUser(res.data);
        }
      })
      .catch(() => {
        if (!cancelled) {
          // Token is invalid
          localStorage.removeItem('termsscope_token');
          setTokenState(null);
          setUser(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        setToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
