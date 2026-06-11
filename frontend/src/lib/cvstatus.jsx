import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api } from "./api";

const Ctx = createContext(null);

export function CVStatusProvider({ children }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const s = await api.getStatus();
      setStatus(s);
      return s;
    } catch {
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return <Ctx.Provider value={{ status, loading, refresh }}>{children}</Ctx.Provider>;
}

export const useCVStatus = () => useContext(Ctx);
