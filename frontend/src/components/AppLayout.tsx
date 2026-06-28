import { FileBarChart, GitCompare, LayoutDashboard, ScrollText, ShieldCheck, Sparkles, Upload, Waves } from "lucide-react";
import { useEffect } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { GuideDialog } from "@/components/GuideDialog";
import { PresenterTour } from "@/components/PresenterTour";
import { TopBar } from "@/components/TopBar";
import { WhatIfPanel } from "@/components/WhatIfPanel";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";

const GUIDE_SEEN_KEY = "vfin_guide_seen";

const NAV = [
  { to: "/app", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/app/briefing", label: "Advisor Briefing", icon: Sparkles, end: false },
  { to: "/app/verification", label: "Verification", icon: ShieldCheck, end: false },
  { to: "/app/borrowing-base", label: "Borrowing Base", icon: ScrollText, end: false },
  { to: "/app/fccr", label: "FCCR Covenant", icon: FileBarChart, end: false },
  { to: "/app/cash-flow", label: "Cash Flow", icon: Waves, end: false },
  { to: "/app/compare", label: "Compare", icon: GitCompare, end: false },
  { to: "/app/setup", label: "Upload Data", icon: Upload, end: false },
];

export function AppLayout() {
  const guideOpen = useAppStore((s) => s.guideOpen);
  const setGuideOpen = useAppStore((s) => s.setGuideOpen);

  useEffect(() => {
    if (!localStorage.getItem(GUIDE_SEEN_KEY)) {
      setGuideOpen(true);
      localStorage.setItem(GUIDE_SEEN_KEY, "1");
    }
  }, [setGuideOpen]);

  return (
    <div className="flex min-h-screen flex-col">
      <GuideDialog open={guideOpen} onOpenChange={setGuideOpen} />
      <PresenterTour />
      <TopBar />
      <div className="flex flex-1">
        <nav className="no-print w-52 shrink-0 border-r bg-background p-3">
          <ul className="space-y-1">
            {NAV.map(({ to, label, icon: Icon, end }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                      isActive ? "bg-primary/10 text-primary" : "text-foreground/70 hover:bg-accent",
                    )
                  }
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>

        <aside className="no-print w-80 shrink-0 overflow-auto border-l bg-background">
          <WhatIfPanel />
        </aside>
      </div>
    </div>
  );
}
