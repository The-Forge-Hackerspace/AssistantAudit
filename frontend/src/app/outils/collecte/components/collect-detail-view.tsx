"use client";

import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Shield,
  Cpu,
  HardDrive,
  Network,
  Users,
} from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

import type { CollectResultRead } from "@/types";

// ── Info row helper ──
function InfoRow({ label, value }: { label: string; value: string | undefined | null }) {
  return (
    <div className="flex justify-between py-1 border-b border-dashed last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-right max-w-[60%] truncate">{value || "N/A"}</span>
    </div>
  );
}

// ── Props ──
export interface CollectDetailViewProps {
  collect: CollectResultRead;
}

export function CollectDetailView({ collect }: CollectDetailViewProps) {
  const summary = collect.summary;
  const isWindows = collect.method === "winrm";
  const isOPNsense = summary?.device_profile === "opnsense" || collect.device_profile === "opnsense";
  const isFirewall = isOPNsense || summary?.device_profile === "stormshield" || summary?.device_profile === "fortigate";

  return (
    <div className="flex flex-col gap-6">
      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Card>
            <CardContent className="pt-3 text-center">
              {isFirewall ? (
                <Shield className="size-5 mx-auto mb-1 text-muted-foreground" />
              ) : (
                <Cpu className="size-5 mx-auto mb-1 text-muted-foreground" />
              )}
              <p className="text-sm font-medium">{summary.os_name}</p>
              <p className="text-xs text-muted-foreground">{summary.os_version}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-3 text-center">
              <Shield className="size-5 mx-auto mb-1 text-muted-foreground" />
              {summary.compliance_score != null ? (
                <>
                  <p className="text-2xl font-bold">{summary.compliance_score}%</p>
                  <p className="text-xs text-muted-foreground">Conformité</p>
                </>
              ) : summary.firewall_rules_count != null ? (
                <>
                  <p className="text-2xl font-bold">{summary.firewall_rules_count}</p>
                  <p className="text-xs text-muted-foreground">Règles pare-feu</p>
                </>
              ) : (
                <>
                  <p className="text-2xl font-bold">—</p>
                  <p className="text-xs text-muted-foreground">Conformité</p>
                </>
              )}
            </CardContent>
          </Card>
          <Card className="border-green-200">
            <CardContent className="pt-3 text-center">
              <CheckCircle2 className="size-5 mx-auto mb-1 text-green-600" />
              <p className="text-2xl font-bold text-green-600">{summary.compliant}</p>
              <p className="text-xs text-muted-foreground">Conformes</p>
            </CardContent>
          </Card>
          <Card className="border-red-200">
            <CardContent className="pt-3 text-center">
              <XCircle className="size-5 mx-auto mb-1 text-red-600" />
              <p className="text-2xl font-bold text-red-600">{summary.non_compliant}</p>
              <p className="text-xs text-muted-foreground">Non conformes</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tabs */}
      <Tabs defaultValue="findings" className="w-full">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="findings" className="gap-1">
            <AlertTriangle className="size-3" /> Findings
          </TabsTrigger>
          <TabsTrigger value="system" className="gap-1">
            <Cpu className="size-3" /> Système
          </TabsTrigger>
          <TabsTrigger value="security" className="gap-1">
            <Shield className="size-3" /> Sécurité
          </TabsTrigger>
          <TabsTrigger value="network" className="gap-1">
            <Network className="size-3" /> Réseau
          </TabsTrigger>
          <TabsTrigger value="users" className="gap-1">
            <Users className="size-3" /> Comptes
          </TabsTrigger>
          <TabsTrigger value="storage" className="gap-1">
            <HardDrive className="size-3" /> Stockage
          </TabsTrigger>
        </TabsList>

        {/* Findings tab */}
        <TabsContent value="findings" className="flex flex-col gap-3">
          {collect.findings && collect.findings.length > 0 ? (
            collect.findings.map((f, idx) => (
              <div
                key={idx}
                className="rounded-lg border p-4 bg-red-50 dark:bg-red-950/20"
              >
                <div className="flex items-start gap-3">
                  <XCircle className="size-5 mt-0.5 shrink-0 text-red-600" />
                  <div className="flex-1 flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <Badge variant="destructive">{f.severity}</Badge>
                      <Badge variant="outline">{f.control_ref}</Badge>
                      <span className="font-semibold text-sm">{f.title}</span>
                    </div>
                    <p className="text-sm">{f.description}</p>
                    {f.remediation && (
                      <p className="text-sm italic">
                        <strong>Recommandation :</strong> {f.remediation}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <CheckCircle2 className="size-10 mx-auto mb-2 text-green-500 opacity-50" />
              <p>Aucun finding détecté — tous les contrôles sont conformes</p>
            </div>
          )}
        </TabsContent>

        {/* System tab */}
        <TabsContent value="system">
          <div className="flex flex-col gap-4">
            {collect.os_info && (
              <div className="rounded-lg border p-4">
                <h3 className="font-semibold mb-2">Informations système</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {isOPNsense ? (
                    <>
                      <InfoRow label="Distribution" value={collect.os_info.distro as string} />
                      <InfoRow label="Version" value={collect.os_info.version as string} />
                      <InfoRow label="Version complète" value={collect.os_info.version_full as string} />
                      <InfoRow label="Kernel" value={collect.os_info.kernel as string} />
                      <InfoRow label="Architecture" value={collect.os_info.arch as string} />
                      <InfoRow label="Uptime" value={collect.os_info.uptime as string} />
                    </>
                  ) : isWindows ? (
                    <>
                      <InfoRow label="OS" value={collect.os_info.caption as string} />
                      <InfoRow label="Version" value={collect.os_info.version as string} />
                      <InfoRow label="Build" value={collect.os_info.build as string} />
                      <InfoRow label="Domaine" value={collect.os_info.domain as string} />
                      <InfoRow
                        label="Joint au domaine"
                        value={collect.os_info.is_domain_joined ? "Oui" : "Non"}
                      />
                    </>
                  ) : (
                    <>
                      <InfoRow label="Distribution" value={collect.os_info.distro as string} />
                      <InfoRow label="Version" value={collect.os_info.version_id as string} />
                      <InfoRow label="Kernel" value={collect.os_info.kernel as string} />
                      <InfoRow label="Architecture" value={collect.os_info.arch as string} />
                      <InfoRow label="Uptime" value={collect.os_info.uptime as string} />
                    </>
                  )}
                </div>
              </div>
            )}

            {collect.updates && (
              <div className="rounded-lg border p-4">
                <h3 className="font-semibold mb-2">Mises à jour</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {isOPNsense ? (
                    <>
                      <InfoRow
                        label="Mises à jour disponibles"
                        value={collect.updates.updates_available ? "Oui" : "Non"}
                      />
                    </>
                  ) : isWindows ? (
                    <>
                      <InfoRow label="Dernière MàJ" value={collect.updates.last_update_date as string} />
                      <InfoRow
                        label="WSUS configuré"
                        value={collect.updates.wsus_configured ? "Oui" : "Non"}
                      />
                      {collect.updates.wsus_server && (
                        <InfoRow label="Serveur WSUS" value={collect.updates.wsus_server as string} />
                      )}
                    </>
                  ) : (
                    <>
                      <InfoRow
                        label="MàJ en attente"
                        value={String(collect.updates.pending_updates ?? "N/A")}
                      />
                      <InfoRow
                        label="MàJ sécurité"
                        value={String(collect.updates.security_updates ?? "N/A")}
                      />
                      <InfoRow
                        label="MàJ auto"
                        value={collect.updates.auto_updates_configured ? "Oui" : "Non"}
                      />
                    </>
                  )}
                </div>
                {isOPNsense && !!collect.updates.pkg_audit && (
                  <div className="mt-3">
                    <h4 className="text-sm font-medium mb-1">Audit des packages (pkg audit)</h4>
                    <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto">
                      {collect.updates.pkg_audit as string}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {collect.services && (
              <div className="rounded-lg border p-4">
                <h3 className="font-semibold mb-2">{isOPNsense ? "Services & VPN" : "Services"}</h3>
                {isOPNsense ? (
                  <div className="flex flex-col gap-3">
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <InfoRow label="OpenVPN" value={collect.services.openvpn_status as string || "Non configuré"} />
                      <InfoRow label="IPsec" value={collect.services.ipsec_status as string || "Non configuré"} />
                      <InfoRow label="WireGuard" value={collect.services.wireguard_status as string || "Non configuré"} />
                      <InfoRow label="CARP (HA)" value={collect.services.carp_status as string || "Non configuré"} />
                    </div>
                    {!!collect.services.services_list && (
                      <div className="mt-2">
                        <h4 className="text-sm font-medium mb-1">Liste des services</h4>
                        <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-60 overflow-y-auto">
                          {collect.services.services_list as string}
                        </pre>
                      </div>
                    )}
                  </div>
                ) : (
                  <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-60 overflow-y-auto">
                    {isWindows
                      ? (collect.services.services_running as string || "N/A")
                      : (collect.services.running as string || "N/A")}
                  </pre>
                )}
              </div>
            )}
          </div>
        </TabsContent>

        {/* Security tab */}
        <TabsContent value="security">
          <div className="flex flex-col gap-4">
            {collect.security && (
              <>
                {/* Pare-feu */}
                <div className="rounded-lg border p-4">
                  <h3 className="font-semibold mb-2">Pare-feu</h3>
                  {isOPNsense ? (
                    <div className="flex flex-col gap-3">
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <InfoRow label="Moteur" value={collect.security.firewall_engine as string || "pf"} />
                        <InfoRow label="Activé" value={(collect.security.firewall_enabled as boolean) ? "Oui" : "Non"} />
                        <InfoRow label="Nombre de règles" value={String(collect.security.firewall_rules_count ?? 0)} />
                        <InfoRow label="États actifs" value={collect.security.states_count as string || "N/A"} />
                      </div>
                      {!!collect.security.firewall_rules && (
                        <div>
                          <h4 className="text-sm font-medium mb-1">Règles pf</h4>
                          <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-60 overflow-y-auto">
                            {collect.security.firewall_rules as string}
                          </pre>
                        </div>
                      )}
                      {!!collect.security.nat_rules && (
                        <div>
                          <h4 className="text-sm font-medium mb-1">Règles NAT</h4>
                          <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto">
                            {collect.security.nat_rules as string}
                          </pre>
                        </div>
                      )}
                      {!!collect.security.aliases && (
                        <div>
                          <h4 className="text-sm font-medium mb-1">Aliases</h4>
                          <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto">
                            {collect.security.aliases as string}
                          </pre>
                        </div>
                      )}
                    </div>
                  ) : isWindows ? (
                    <div className="flex flex-col gap-2">
                      <InfoRow
                        label="Tous profils activés"
                        value={(collect.security.firewall_all_enabled as boolean) ? "Oui" : "Non"}
                      />
                      <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                        {collect.security.firewall_raw as string || "N/A"}
                      </pre>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-2">
                      <InfoRow label="Status" value={collect.security.firewall_status as string} />
                      <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto">
                        {collect.security.firewall_details as string || "N/A"}
                      </pre>
                    </div>
                  )}
                </div>

                {/* SSH / RDP / IDS */}
                {isOPNsense ? (
                  <>
                    <div className="rounded-lg border p-4">
                      <h3 className="font-semibold mb-2">SSH</h3>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <InfoRow label="PermitRootLogin" value={collect.security.ssh_permit_root_login as string} />
                      </div>
                      {!!collect.security.ssh_config_raw && (
                        <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto mt-2">
                          {collect.security.ssh_config_raw as string}
                        </pre>
                      )}
                    </div>

                    <div className="rounded-lg border p-4">
                      <h3 className="font-semibold mb-2">IDS / IPS (Suricata)</h3>
                      <InfoRow label="Statut" value={collect.security.suricata_status as string || "Non actif"} />
                    </div>

                    <div className="rounded-lg border p-4">
                      <h3 className="font-semibold mb-2">Journalisation</h3>
                      <InfoRow label="Syslog distant" value={collect.security.syslog_remote as string || "Non configuré"} />
                    </div>
                  </>
                ) : isWindows ? (
                  <>
                    <div className="rounded-lg border p-4">
                      <h3 className="font-semibold mb-2">RDP</h3>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <InfoRow
                          label="RDP activé"
                          value={(collect.security.rdp_enabled as boolean) ? "Oui" : "Non"}
                        />
                        <InfoRow
                          label="NLA activé"
                          value={(collect.security.rdp_nla_enabled as boolean) ? "Oui" : "Non"}
                        />
                      </div>
                    </div>

                    <div className="rounded-lg border p-4">
                      <h3 className="font-semibold mb-2">Antivirus / EDR</h3>
                      <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                        {collect.security.defender_raw as string || "N/A"}
                      </pre>
                    </div>

                    <div className="rounded-lg border p-4">
                      <h3 className="font-semibold mb-2">Journalisation</h3>
                      <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto">
                        {collect.security.audit_policy as string || "N/A"}
                      </pre>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="rounded-lg border p-4">
                      <h3 className="font-semibold mb-2">SSH</h3>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <InfoRow label="PermitRootLogin" value={collect.security.ssh_permit_root_login as string} />
                        <InfoRow label="PasswordAuth" value={collect.security.ssh_password_authentication as string} />
                      </div>
                      <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto mt-2">
                        {collect.security.sshd_config_raw as string || "N/A"}
                      </pre>
                    </div>

                    <div className="rounded-lg border p-4">
                      <h3 className="font-semibold mb-2">Antivirus / EDR</h3>
                      <InfoRow label="Agent détecté" value={collect.security.antivirus_edr as string || "Aucun"} />
                    </div>

                    <div className="rounded-lg border p-4">
                      <h3 className="font-semibold mb-2">Journalisation</h3>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <InfoRow label="rsyslog" value={collect.security.rsyslog_active as string} />
                        <InfoRow label="auditd" value={collect.security.auditd_active as string} />
                      </div>
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        </TabsContent>

        {/* Network tab */}
        <TabsContent value="network">
          {collect.network && (
            <div className="flex flex-col gap-4">
              <div className="rounded-lg border p-4">
                <h3 className="font-semibold mb-2">{isOPNsense ? "Interfaces" : "Configuration IP"}</h3>
                <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-60 overflow-y-auto">
                  {collect.network.interfaces as string ||
                   collect.network.ip_config as string ||
                   collect.network.ip_addresses as string || "N/A"}
                </pre>
              </div>
              {isOPNsense && !!collect.network.routes && (
                <div className="rounded-lg border p-4">
                  <h3 className="font-semibold mb-2">Routes</h3>
                  <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-60 overflow-y-auto">
                    {collect.network.routes as string}
                  </pre>
                </div>
              )}
              <div className="rounded-lg border p-4">
                <h3 className="font-semibold mb-2">Ports en écoute</h3>
                <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-60 overflow-y-auto">
                  {collect.network.listening_ports as string || "N/A"}
                </pre>
              </div>
              <div className="rounded-lg border p-4">
                <h3 className="font-semibold mb-2">DNS</h3>
                <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                  {collect.network.dns_servers as string ||
                   collect.network.dns as string || "N/A"}
                </pre>
              </div>
            </div>
          )}
        </TabsContent>

        {/* Users tab */}
        <TabsContent value="users">
          {collect.users && (
            <div className="flex flex-col gap-4">
              {isOPNsense ? (
                <div className="rounded-lg border p-4">
                  <h3 className="font-semibold mb-2">Comptes système avec shell</h3>
                  <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-60 overflow-y-auto">
                    {collect.users.users_with_shell as string || "N/A"}
                  </pre>
                </div>
              ) : isWindows ? (
                <>
                  <div className="rounded-lg border p-4">
                    <h3 className="font-semibold mb-2">Compte Administrateur</h3>
                    <InfoRow
                      label="Renommé"
                      value={(collect.users.admin_renamed as boolean) ? "Oui" : "Non"}
                    />
                    <pre className="text-xs bg-muted p-3 rounded overflow-x-auto mt-2">
                      {collect.users.admin_account_raw as string || "N/A"}
                    </pre>
                  </div>
                  <div className="rounded-lg border p-4">
                    <h3 className="font-semibold mb-2">Utilisateurs locaux</h3>
                    <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto">
                      {collect.users.local_users as string || "N/A"}
                    </pre>
                  </div>
                  <div className="rounded-lg border p-4">
                    <h3 className="font-semibold mb-2">Administrateurs locaux</h3>
                    <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto">
                      {collect.users.local_admins as string || "N/A"}
                    </pre>
                  </div>
                  <div className="rounded-lg border p-4">
                    <h3 className="font-semibold mb-2">Politique de mot de passe</h3>
                    <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                      {(collect.users.password_policy as Record<string, unknown>)?.raw as string || "N/A"}
                    </pre>
                  </div>
                </>
              ) : (
                <>
                  <div className="rounded-lg border p-4">
                    <h3 className="font-semibold mb-2">Utilisateurs avec shell</h3>
                    {Array.isArray(collect.users.users_with_shell) ? (
                      <div className="rounded-md border">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Utilisateur</TableHead>
                              <TableHead>UID</TableHead>
                              <TableHead>Shell</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {(collect.users.users_with_shell as { username: string; uid: string; shell: string }[]).map(
                              (u, idx) => (
                                <TableRow key={idx}>
                                  <TableCell className="font-mono text-sm">{u.username}</TableCell>
                                  <TableCell className="text-sm">{u.uid}</TableCell>
                                  <TableCell className="font-mono text-sm">{u.shell}</TableCell>
                                </TableRow>
                              )
                            )}
                          </TableBody>
                        </Table>
                      </div>
                    ) : (
                      <pre className="text-xs bg-muted p-3 rounded">N/A</pre>
                    )}
                  </div>
                  <div className="rounded-lg border p-4">
                    <h3 className="font-semibold mb-2">Sudoers</h3>
                    <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto">
                      {collect.users.sudoers_raw as string || "N/A"}
                    </pre>
                  </div>
                  <div className="rounded-lg border p-4">
                    <h3 className="font-semibold mb-2">Dernières connexions</h3>
                    <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto">
                      {collect.users.last_logins as string || "N/A"}
                    </pre>
                  </div>
                </>
              )}
            </div>
          )}
        </TabsContent>

        {/* Storage tab */}
        <TabsContent value="storage">
          {collect.storage && (
            <div className="flex flex-col gap-4">
              {isOPNsense ? (
                <div className="rounded-lg border p-4">
                  <h3 className="font-semibold mb-2">Configuration OPNsense</h3>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <InfoRow label="Taille config.xml" value={collect.storage.config_xml_size as string || "N/A"} />
                    <InfoRow label="Sauvegardes" value={`${collect.storage.config_backup_count ?? 0} fichier(s)`} />
                  </div>
                </div>
              ) : (
                <div className="rounded-lg border p-4">
                  <h3 className="font-semibold mb-2">Utilisation disque</h3>
                  <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                    {collect.storage.disk_usage as string || "N/A"}
                  </pre>
                </div>
              )}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
