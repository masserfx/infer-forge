"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import type { User } from "@/types";
import { getMe, login as apiLogin, setAuthToken, getAuthToken } from "@/lib/api";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const isAuthenticated = !!user;

  // Try to load user on mount if token exists
  useEffect(() => {
    const loadUser = async () => {
      const token = getAuthToken();
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const userData = await getMe();
        setUser(userData);
      } catch {
        // Token expired or invalid, clear it
        setAuthToken(null);
      } finally {
        setIsLoading(false);
      }
    };

    loadUser();
  }, []);

  const login = async (email: string, password: string) => {
    const response = await apiLogin(email, password);
    setAuthToken(response.access_token);
    setUser(response.user);
    router.push("/dashboard");
  };

  const logout = () => {
    setAuthToken(null);
    setUser(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
