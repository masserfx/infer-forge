"use client";

import { Menu, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-provider";
import { ROLE_LABELS } from "@/types";
import { NotificationBell } from "@/components/layout/notification-bell";

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
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-10 flex h-16 items-center gap-2 sm:gap-4 border-b bg-background px-2 sm:px-4 lg:px-6">
      {/* Mobile menu */}
      <Sheet>
        <SheetTrigger asChild>
          <Button variant="outline" size="icon" className="md:hidden min-w-[44px] min-h-[44px]">
            <Menu className="h-5 w-5" />
            <span className="sr-only">Otevřít menu</span>
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-64">
          <div className="flex h-16 items-center px-2">
            <Link href="/dashboard" className="flex items-center gap-2 font-bold text-lg">
              INFERBOX
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
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors min-h-[44px]",
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
      <div className="flex-1 min-w-0">
        <h1 className="text-base sm:text-lg font-semibold truncate">
          {navItems.find((item) => pathname?.startsWith(item.href))?.label || "INFERBOX"}
        </h1>
      </div>

      {/* User menu */}
      <div className="flex items-center gap-1 sm:gap-2">
        <NotificationBell />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="flex items-center gap-2 min-w-[44px] min-h-[44px]">
              <div className="h-8 w-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-medium">
                {user?.full_name.charAt(0).toUpperCase() || "U"}
              </div>
              <div className="hidden lg:block text-left">
                <div className="text-sm font-medium">{user?.full_name}</div>
                <div className="text-xs text-muted-foreground">
                  {user?.role && ROLE_LABELS[user.role]}
                </div>
              </div>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">{user?.full_name}</p>
                <p className="text-xs leading-none text-muted-foreground">{user?.email}</p>
                {user?.role && (
                  <Badge variant="secondary" className="w-fit mt-1">
                    {ROLE_LABELS[user.role]}
                  </Badge>
                )}
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/nastaveni" className="cursor-pointer">
                <Settings className="mr-2 h-4 w-4" />
                Nastavení
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={logout} className="cursor-pointer text-red-600">
              <LogOut className="mr-2 h-4 w-4" />
              Odhlásit se
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
