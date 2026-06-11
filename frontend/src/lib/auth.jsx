import { createContext, useContext, useState, useCallback } from "react";
import { api, tokenStore } from "./api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [authed, setAuthed] = useState(!!tokenStore.get());

  const login = useCallback(async (email, password) => {
    const { access_token } = await api.login(email, password);
    tokenStore.set(access_token);
    setAuthed(true);
  }, []);

  const register = useCallback(async (email, password, full_name) => {
    await api.register(email, password, full_name);
    await login(email, password);
  }, [login]);

  const logout = useCallback(() => {
    tokenStore.clear();
    setAuthed(false);
  }, []);

  return (
    <AuthCtx.Provider value={{ authed, login, register, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
