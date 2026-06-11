import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api } from "./api";

const Ctx = createContext(null);

export function CreditsProvider({ children }) {
  const [summary, setSummary] = useState(null);

  const refresh = useCallback(async () => {
    try { setSummary(await api.billingSummary()); }
    catch { /* ignore */ }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return <Ctx.Provider value={{ summary, refresh }}>{children}</Ctx.Provider>;
}

export const useCredits = () => useContext(Ctx);
