import React, { createContext, useContext, useState, useEffect } from 'react';
import * as SecureStore from 'expo-secure-store';
import { ApiService } from '../services/api';

interface User {
  id: number;
  username: string;
  full_name_ne: string;
  role: 'SUPER_ADMIN' | 'ADMIN' | 'PRINCIPAL' | 'TEACHER' | 'STUDENT' | 'PARENT' | 'USER';
  phone?: string;
  [key: string]: any;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  isAdmin: boolean;
  isTeacher: boolean;
  isStudent: boolean;
  isParent: boolean;
}

const AuthContext = createContext<AuthContextType>({} as AuthContextType);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check saved session token on startup
    const checkToken = async () => {
      try {
        const savedToken = await SecureStore.getItemAsync('auth_token');
        if (savedToken) {
          setToken(savedToken);
          const profile = await ApiService.getProfile();
          setUser(profile);
        }
      } catch (e) {
        // Token invalid or network offline
      } finally {
        setIsLoading(false);
      }
    };
    checkToken();
  }, []);

  const login = async (username: string, password: string) => {
    const data = await ApiService.login(username, password);
    setToken(data.token);
    setUser(data.user);
  };

  const logout = async () => {
    await ApiService.logout();
    setToken(null);
    setUser(null);
  };

  const role = user?.role;
  const isAdmin = role === 'SUPER_ADMIN' || role === 'ADMIN' || role === 'PRINCIPAL';
  const isTeacher = role === 'TEACHER';
  const isStudent = role === 'STUDENT';
  const isParent = role === 'PARENT';

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        logout,
        isAdmin,
        isTeacher,
        isStudent,
        isParent,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
