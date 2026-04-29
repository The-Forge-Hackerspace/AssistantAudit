/**
 * RBAC : un utilisateur "auditeur" ne peut pas POST/PUT/DELETE sur /users
 * et un "lecteur" ne peut pas créer de ressources.
 *
 * On crée les users via l'API admin, on ouvre un contexte HTTP séparé pour
 * chaque rôle, on assert, on nettoie.
 */
import { test, expect, request as pwRequest } from '@playwright/test';
import { uniq } from './helpers';

const PWD = 'E2eRoleTest99!aa';

async function createUserAndLogin(
  baseURL: string,
  adminCtx: import('@playwright/test').APIRequestContext,
  role: 'auditeur' | 'lecteur',
) {
  const username = uniq(role).replace(/-/g, '').slice(0, 20);
  const email = `${username}@e2e.example.com`;
  const r = await adminCtx.post('/api/v1/users/', {
    data: {
      username,
      email,
      full_name: `E2E ${role}`,
      role,
      password: PWD,
    },
  });
  if (r.status() !== 201) throw new Error('user create: ' + (await r.text()));
  const user = await r.json();
  const userCtx = await pwRequest.newContext({
    baseURL,
    ignoreHTTPSErrors: true,
    storageState: { cookies: [], origins: [] },
  });
  const login = await userCtx.post('/api/v1/auth/login', {
    form: { username: email, password: PWD },
  });
  if (login.status() === 429) {
    await userCtx.dispose();
    test.skip(true, 'rate limit /auth/login lors du setup RBAC');
    return { user, userCtx: null as never };
  }
  if (login.status() !== 200) {
    await userCtx.dispose();
    throw new Error('login: ' + login.status() + ' ' + (await login.text()));
  }
  return { user, userCtx };
}

test('auditeur : POST /users → 403', async ({ request, baseURL }) => {
  const { user, userCtx } = await createUserAndLogin(baseURL!, request, 'auditeur');
  try {
    const r = await userCtx.post('/api/v1/users/', {
      data: {
        username: uniq('hack').replace(/-/g, '').slice(0, 20),
        email: 'hack@e2e.example.com',
        role: 'admin',
        password: PWD,
      },
    });
    expect(r.status()).toBe(403);
  } finally {
    await userCtx.dispose();
    await request.delete(`/api/v1/users/${user.id}`);
  }
});

test('lecteur : POST /entreprises → 403', async ({ request, baseURL }) => {
  const { user, userCtx } = await createUserAndLogin(baseURL!, request, 'lecteur');
  try {
    const r = await userCtx.post('/api/v1/entreprises', {
      data: { nom: uniq('LecteurE'), contacts: [] },
    });
    expect(r.status()).toBe(403);
  } finally {
    await userCtx.dispose();
    await request.delete(`/api/v1/users/${user.id}`);
  }
});

test('lecteur : GET /entreprises autorisé (read-only)', async ({ request, baseURL }) => {
  const { user, userCtx } = await createUserAndLogin(baseURL!, request, 'lecteur');
  try {
    const r = await userCtx.get('/api/v1/entreprises');
    expect(r.status()).toBe(200);
  } finally {
    await userCtx.dispose();
    await request.delete(`/api/v1/users/${user.id}`);
  }
});
