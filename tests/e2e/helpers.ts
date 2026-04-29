/**
 * Helpers partagés pour les specs E2E :
 *  - construction de noms uniques par run
 *  - création/suppression de ressources via l'API (setup propre, pas via UI)
 */
import type { APIRequestContext } from '@playwright/test';

let counter = 0;
export function uniq(prefix: string): string {
  counter += 1;
  return `${prefix}-${Date.now()}-${counter}-${Math.random().toString(36).slice(2, 7)}`;
}

export interface CreatedEntreprise {
  id: number;
  nom: string;
}
export interface CreatedSite {
  id: number;
  nom: string;
  entreprise_id: number;
}
export interface CreatedEquipement {
  id: number;
  ip_address: string;
  site_id: number;
}

export async function createEntreprise(
  api: APIRequestContext,
  overrides: Partial<{ nom: string; secteur_activite: string }> = {},
): Promise<CreatedEntreprise> {
  const nom = overrides.nom ?? uniq('E2E-Entreprise');
  const r = await api.post('/api/v1/entreprises', {
    data: {
      nom,
      secteur_activite: overrides.secteur_activite ?? 'Tests E2E',
      contacts: [],
    },
  });
  if (r.status() !== 201) {
    throw new Error(`createEntreprise failed: ${r.status()} ${await r.text()}`);
  }
  return r.json();
}

export async function deleteEntreprise(
  api: APIRequestContext,
  id: number,
): Promise<void> {
  await api.delete(`/api/v1/entreprises/${id}`);
}

export async function createSite(
  api: APIRequestContext,
  entrepriseId: number,
  overrides: Partial<{ nom: string }> = {},
): Promise<CreatedSite> {
  const nom = overrides.nom ?? uniq('E2E-Site');
  const r = await api.post('/api/v1/sites', {
    data: { nom, entreprise_id: entrepriseId, adresse: '1 rue Test' },
  });
  if (r.status() !== 201) {
    throw new Error(`createSite failed: ${r.status()} ${await r.text()}`);
  }
  return r.json();
}

export async function deleteSite(api: APIRequestContext, id: number): Promise<void> {
  await api.delete(`/api/v1/sites/${id}`);
}

export async function createEquipement(
  api: APIRequestContext,
  siteId: number,
  overrides: Partial<{ ip_address: string; type_equipement: string; hostname: string }> = {},
): Promise<CreatedEquipement> {
  const ip =
    overrides.ip_address ??
    `10.${Math.floor(Math.random() * 250) + 1}.${Math.floor(Math.random() * 250) + 1}.${
      Math.floor(Math.random() * 250) + 1
    }`;
  const r = await api.post('/api/v1/equipements', {
    data: {
      site_id: siteId,
      type_equipement: overrides.type_equipement ?? 'serveur',
      ip_address: ip,
      hostname: overrides.hostname ?? uniq('host'),
    },
  });
  if (r.status() !== 201) {
    throw new Error(`createEquipement failed: ${r.status()} ${await r.text()}`);
  }
  return r.json();
}

export async function deleteEquipement(
  api: APIRequestContext,
  id: number,
): Promise<void> {
  await api.delete(`/api/v1/equipements/${id}`);
}
