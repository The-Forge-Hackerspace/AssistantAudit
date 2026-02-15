"use client";

import Link from "next/link";
import {
  Radar,
  FileCode,
  Lock,
  Terminal,
  Wrench,
  ArrowRight,
  ShieldCheck,
  Castle,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const tools = [
  {
    title: "Scanner Réseau",
    description:
      "Découverte et inventaire automatique des équipements réseau via Nmap. Lancez des scans, identifiez les hôtes actifs et importez-les comme équipements.",
    icon: Radar,
    href: "/outils/scanner",
    color: "text-blue-500",
    bgColor: "bg-blue-500/10",
  },
  {
    title: "Analyseur de Configuration",
    description:
      "Upload et analyse automatique de fichiers de configuration réseau (FortiGate, OPNsense). Détection de faiblesses de sécurité et recommandations.",
    icon: FileCode,
    href: "/outils/config-parser",
    color: "text-orange-500",
    bgColor: "bg-orange-500/10",
  },
  {
    title: "Collecte SSH / WinRM",
    description:
      "Collecte automatique d'informations système sur les serveurs via SSH (Linux) ou WinRM (Windows). Analyse de conformité et pré-remplissage d'audit.",
    icon: Terminal,
    href: "/outils/collecte",
    color: "text-purple-500",
    bgColor: "bg-purple-500/10",
  },
  {
    title: "Vérificateur SSL/TLS",
    description:
      "Vérification de certificats et protocoles TLS. Détection d'expiration, auto-signature, protocoles obsolètes (SSLv3, TLS 1.0/1.1).",
    icon: Lock,
    href: "/outils/ssl-checker",
    color: "text-green-500",
    bgColor: "bg-green-500/10",
  },
  {
    title: "Audit Active Directory",
    description:
      "Audit automatisé d'un domaine AD via LDAP : comptes privilégiés, politique de mots de passe, GPO, LAPS, niveau fonctionnel et conformité CIS.",
    icon: ShieldCheck,
    href: "/outils/ad-auditor",
    color: "text-cyan-500",
    bgColor: "bg-cyan-500/10",
  },
  {
    title: "PingCastle",
    description:
      "Audit avancé Active Directory avec PingCastle : analyse healthcheck, scores de risque, règles de sécurité et terminal interactif.",
    icon: Castle,
    href: "/outils/pingcastle",
    color: "text-red-500",
    bgColor: "bg-red-500/10",
  },
];

export default function OutilsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Wrench className="h-6 w-6" />
          Outils d&apos;Infrastructure
        </h1>
        <p className="text-muted-foreground">
          Outils intégrés pour l&apos;audit technique de l&apos;infrastructure IT
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {tools.map((tool) => (
          <Link key={tool.href} href={tool.href}>
            <Card className="h-full hover:border-primary/50 hover:shadow-md transition-all cursor-pointer group">
              <CardHeader>
                <div className={`inline-flex p-3 rounded-lg ${tool.bgColor} w-fit`}>
                  <tool.icon className={`h-6 w-6 ${tool.color}`} />
                </div>
                <CardTitle className="flex items-center gap-2">
                  {tool.title}
                  <ArrowRight className="h-4 w-4 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
                </CardTitle>
                <CardDescription>{tool.description}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
