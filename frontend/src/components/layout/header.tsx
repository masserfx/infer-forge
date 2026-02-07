"use client";

import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from "@/components/ui/sheet";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ClipboardList,
  Calculator,
  BarChart3,
  Inbox,
  FileText,
  RefreshCw,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

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
    href: "/pohoda",
    label: "Pohoda",
    icon: RefreshCw,
  },
  {
    href: "/nastaveni",
    label: "Nastavení",
    icon: Settings,
  },
];

export function Header() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-4 lg:px-6">
      {/* Mobile menu */}
      <Sheet>
        <SheetTrigger asChild>
          <Button variant="outline" size="icon" className="lg:hidden">
            <Menu className="h-5 w-5" />
            <span className="sr-only">Otevřít menu</span>
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-64">
          <div className="flex h-16 items-center px-2">
            <Link href="/dashboard" className="flex items-center gap-2 font-bold text-lg">
              INFER FORGE
            </Link>
          </div>
          <nav className="flex flex-col space-y-1 mt-4">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  )}
                >
                  <Icon className="h-5 w-5" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </SheetContent>
      </Sheet>

      {/* Desktop breadcrumbs placeholder */}
      <div className="flex-1">
        <h1 className="text-lg font-semibold">
          {navItems.find((item) => pathname?.startsWith(item.href))?.label || "INFER FORGE"}
        </h1>
      </div>

      {/* User placeholder */}
      <div className="flex items-center gap-4">
        <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center text-xs font-medium">
          U
        </div>
      </div>
    </header>
  );
}
