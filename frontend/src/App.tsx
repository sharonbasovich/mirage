import { createContext, useContext, useState, type ReactNode } from "react";
import { BrowserRouter, Link, NavLink, Route, Routes } from "react-router-dom";
import type { Analysis } from "./types";
import About from "./pages/About";
import Lab from "./pages/Lab";
import Ledger from "./pages/Ledger";
import Upload from "./pages/Upload";
import Verdict from "./pages/Verdict";

interface ResultCtx {
  programId: string | null;
  analysis: Analysis | null;
  setResult: (pid: string, a: Analysis) => void;
}

const Ctx = createContext<ResultCtx>({
  programId: null,
  analysis: null,
  setResult: () => {},
});
export const useResult = () => useContext(Ctx);

const NAV = [
  { to: "/", label: "Strategy Lab" },
  { to: "/verdict", label: "Verdict" },
  { to: "/ledger", label: "Trial Ledger" },
  { to: "/audit", label: "Audit Upload" },
  { to: "/about", label: "About / Methods" },
];

function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-edge sticky top-0 bg-ink/90 backdrop-blur z-10">
        <div className="max-w-7xl mx-auto px-4 flex items-center gap-6 h-14">
          <Link to="/" className="flex items-baseline gap-2">
            <span className="text-xl font-bold text-accent">Mirage</span>
            <span className="text-xs text-dim hidden sm:inline">
              the backtest lie detector
            </span>
          </Link>
          <nav className="flex gap-1 ml-auto overflow-x-auto">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded-lg text-sm whitespace-nowrap transition-colors ${
                    isActive ? "bg-edge text-accent" : "text-dim hover:text-gray-200"
                  }`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <div className="bg-amber-500/10 border-b border-amber-500/40 text-amber-200 text-xs sm:text-sm px-4 py-2 text-center">
        Public demo — stored results are <b>temporary, shared and per-instance</b>:
        saved programs, ledger entries and certificates can reset at any time.
        Every run is computed live; nothing here is durable storage.
      </div>
      <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
      <footer className="border-t border-edge mt-10 py-4 text-center text-xs text-dim">
        Research prototype for GIBC V2. Not a product, not a financial service,
        not financial advice.
      </footer>
    </div>
  );
}

export default function App() {
  const [programId, setProgramId] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const setResult = (pid: string, a: Analysis) => {
    setProgramId(pid);
    setAnalysis(a);
  };
  return (
    <Ctx.Provider value={{ programId, analysis, setResult }}>
      <BrowserRouter>
        <Shell>
          <Routes>
            <Route path="/" element={<Lab />} />
            <Route path="/verdict" element={<Verdict />} />
            <Route path="/ledger" element={<Ledger />} />
            <Route path="/audit" element={<Upload />} />
            <Route path="/about" element={<About />} />
          </Routes>
        </Shell>
      </BrowserRouter>
    </Ctx.Provider>
  );
}
