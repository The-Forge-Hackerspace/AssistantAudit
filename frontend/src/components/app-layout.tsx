"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import {
  LayoutDashboard,
  Building2,
  ClipboardCheck,
  MapPin,
  Server,
  BookOpen,
  ShieldCheck,
  LogOut,
  User,
  ChevronUp,
  Wrench,
  Radar,
  FileCode,
  Lock,
  Terminal,
  Castle,
  Map,
} from "lucide-react";

const navItems = [
  {
    label: "Général",
    items: [
      { title: "Dashboard", href: "/", icon: LayoutDashboard },
    ],
  },
  {
    label: "Gestion",
    items: [
      { title: "Entreprises", href: "/entreprises", icon: Building2 },
      { title: "Sites", href: "/sites", icon: MapPin },
      { title: "Équipements", href: "/equipements", icon: Server },
    ],
  },
  {
    label: "Audit",
    items: [
      { title: "Projets d'audit", href: "/audits", icon: ClipboardCheck },
      { title: "Référentiels", href: "/frameworks", icon: BookOpen },
    ],
  },
  {
    label: "Outils",
    items: [
      { title: "Scanner réseau", href: "/outils/scanner", icon: Radar },
      { title: "Config parser", href: "/outils/config-parser", icon: FileCode },
      { title: "Collecte SSH/WinRM", href: "/outils/collecte", icon: Terminal },
      { title: "SSL/TLS", href: "/outils/ssl-checker", icon: Lock },
      { title: "Audit AD", href: "/outils/ad-auditor", icon: ShieldCheck },
      { title: "Cartographie réseau", href: "/outils/network-map", icon: Map },
      { title: "PingCastle", href: "/outils/pingcastle", icon: Castle },
    ],
  },
];

function AppSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const initials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "??";

  const roleBadgeVariant = (role: string) => {
    switch (role) {
      case "admin":
        return "destructive" as const;
      case "auditeur":
        return "default" as const;
      default:
        return "secondary" as const;
    }
  };

  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary">
            <ShieldCheck className="h-5 w-5 text-primary-foreground" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold">AssistantAudit</span>
            <span className="text-xs text-muted-foreground">v2.0.0</span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent>
        {navItems.map((group) => (
          <SidebarGroup key={group.label}>
            <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton
                      asChild
                      isActive={
                        item.href === "/"
                          ? pathname === "/"
                          : pathname.startsWith(item.href)
                      }
                    >
                      <Link href={item.href}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton size="lg">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="text-xs">
                      {initials}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex flex-col flex-1 text-left text-sm">
                    <span className="font-medium truncate">
                      {user?.full_name}
                    </span>
                    <div className="flex items-center gap-1">
                      <Badge
                        variant={roleBadgeVariant(user?.role || "")}
                        className="text-[10px] px-1 py-0 h-4"
                      >
                        {user?.role}
                      </Badge>
                    </div>
                  </div>
                  <ChevronUp className="h-4 w-4 ml-auto" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent side="top" align="start" className="w-56">
                <DropdownMenuItem asChild>
                  <Link href="/profile">
                    <User className="mr-2 h-4 w-4" />
                    Mon profil
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout} className="text-destructive">
                  <LogOut className="mr-2 h-4 w-4" />
                  Se déconnecter
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}

import { ThemeToggle } from "@/components/theme-toggle";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-14 items-center gap-2 border-b px-4">
          <SidebarTrigger />
          <Separator orientation="vertical" className="h-6" />
          <div className="flex-1" />
          <ThemeToggle />
          <span className="text-sm text-muted-foreground">
            {user?.full_name}
          </span>
        </header>
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  );
}
