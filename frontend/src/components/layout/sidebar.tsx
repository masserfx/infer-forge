"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ClipboardList,
  Kanban,
  Trophy,
  Calculator,
  BarChart3,
  Inbox,
  FileText,
  RefreshCw,
  Settings,
  Package,
  Handshake,
  Presentation,
  Network,
  Cpu,
  LogOut,
  User,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-provider";
import { Button } from "@/components/ui/button";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
  {
    href: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
  },
  {
    href: "/zakazky",
    label: "Zakázky",
    icon: ClipboardList,
  },
  {
    href: "/kanban",
    label: "Pipeline",
    icon: Kanban,
  },
  {
    href: "/trziste-ukolu",
    label: "Tržiště úkolů",
    icon: Trophy,
  },
  {
    href: "/kalkulace",
    label: "Kalkulace",
    icon: Calculator,
  },
  {
    href: "/reporting",
    label: "Reporting",
    icon: BarChart3,
  },
  {
    href: "/inbox",
    label: "Inbox",
    icon: Inbox,
  },
  {
    href: "/dokumenty",
    label: "Dokumenty",
    icon: FileText,
  },
  {
    href: "/materialy",
    label: "Ceník materiálů",
    icon: Package,
  },
  {
    href: "/subdodavatele",
    label: "Subdodavatelé",
    icon: Handshake,
  },
  {
    href: "/automatizace",
    label: "Automatizace",
    icon: Cpu,
  },
  {
    href: "/pohoda",
    label: "Pohoda",
    icon: RefreshCw,
  },
  {
    href: "/diagram",
    label: "Architektura",
    icon: Network,
  },
  {
    href: "/prezentace",
    label: "Prezentace",
    icon: Presentation,
  },
  {
    href: "/nastaveni",
    label: "Nastavení",
    icon: Settings,
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "hidden md:flex md:flex-col md:border-r md:bg-muted/40 transition-all duration-300",
        isCollapsed ? "md:w-16 lg:w-16" : "md:w-64 lg:w-64"
      )}
    >
      <div className="flex h-16 items-center border-b px-4 justify-between">
        {!isCollapsed && (
          <Link href="/dashboard" className="flex items-center gap-2 text-lg">
            <span className="font-normal">infer</span><span className="font-bold">box</span>
          </Link>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 ml-auto"
          onClick={() => setIsCollapsed(!isCollapsed)}
        >
          {isCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
          <span className="sr-only">
            {isCollapsed ? "Rozbalit sidebar" : "Sbalit sidebar"}
          </span>
        </Button>
      </div>
      <nav className="flex-1 space-y-1 p-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors min-h-[44px]",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                isCollapsed && "justify-center px-0"
              )}
              title={isCollapsed ? item.label : undefined}
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              {!isCollapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>
      {user && (
        <div className="border-t p-2">
          {!isCollapsed && (
            <div className="flex items-center gap-3 px-3 py-2 mb-1">
              <User className="h-5 w-5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="truncate text-sm font-medium">{user.full_name}</p>
                <p className="truncate text-xs text-muted-foreground">{user.email}</p>
              </div>
            </div>
          )}
          <button
            onClick={logout}
            className={cn(
              "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive min-h-[44px]",
              isCollapsed && "justify-center px-0"
            )}
            title={isCollapsed ? "Odhlásit se" : undefined}
          >
            <LogOut className="h-5 w-5 flex-shrink-0" />
            {!isCollapsed && <span>Odhlásit se</span>}
          </button>
        </div>
      )}
    </aside>
  );
}
