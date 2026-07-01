import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./lib/auth";
import { CVStatusProvider } from "./lib/cvstatus";
import { CreditsProvider } from "./lib/credits";
import { ThemeProvider } from "./lib/theme";
import { Protected } from "./components/ui";
import Layout from "./components/Layout";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Onboarding from "./pages/Onboarding";
import BaseCV from "./pages/BaseCV";
import Generate from "./pages/Generate";
import Jobs from "./pages/Jobs";
import Applications from "./pages/Applications";
import ApplicationDetail from "./pages/ApplicationDetail";
import Billing from "./pages/Billing";

function Shell() {
  return (
    <CVStatusProvider>
      <CreditsProvider>
        <Layout />
      </CreditsProvider>
    </CVStatusProvider>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route element={<Protected><Shell /></Protected>}>
              <Route path="/onboarding" element={<Onboarding />} />
              <Route path="/cv" element={<BaseCV />} />
              <Route path="/generate" element={<Generate />} />
              <Route path="/jobs" element={<Jobs />} />
              <Route path="/applications" element={<Applications />} />
              <Route path="/applications/:id" element={<ApplicationDetail />} />
              <Route path="/billing" element={<Billing />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
