import { DealItem, LeadItem, LiveStatus, RunReport, VaultKeys } from '../types/jarvis';

const DB_NAME = 'bharat_jarvis_db';
const DB_VER = 1;
const STORE = 'kv_store';

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VER);
    req.onupgradeneeded = () => {
      if (!req.result.objectStoreNames.contains(STORE)) {
        req.result.createObjectStore(STORE);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function idbGet<T>(key: string, fallback: T): Promise<T> {
  try {
    const db = await openDb();
    return await new Promise((resolve) => {
      const tx = db.transaction(STORE, 'readonly');
      const req = tx.objectStore(STORE).get(key);
      req.onsuccess = () => resolve((req.result as T) ?? fallback);
      req.onerror = () => resolve(fallback);
    });
  } catch {
    return fallback;
  }
}

async function idbSet<T>(key: string, val: T): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite');
    tx.objectStore(STORE).put(val, key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export const DEFAULT_VAULT: VaultKeys = {
  githubPat: '',
  githubRepo: 'sarfealam2246-coder/bharat-digital-jarvis',
  nvidiaKey: '',
  geminiKey: '',
  groqKey: '',
  cloudflareAccountId: '',
  cloudflareApiToken: '',
  cloudSingleKey: '',
  gmailAddress: 'sarfe293@gmail.com',
  gmailAppPassword: '',
  upiId: ''
};

export async function loadVault(): Promise<VaultKeys> {
  const saved = await idbGet<Partial<VaultKeys>>('vault', {});
  return { ...DEFAULT_VAULT, ...saved };
}

export async function saveVault(v: VaultKeys): Promise<void> {
  await idbSet('vault', v);
}

export async function loadLeads(): Promise<LeadItem[]> {
  return idbGet<LeadItem[]>('leads', []);
}

export async function saveLeads(items: LeadItem[]): Promise<void> {
  await idbSet('leads', items);
}

export async function loadDeals(): Promise<DealItem[]> {
  return idbGet<DealItem[]>('deals', []);
}

export async function saveDeals(items: DealItem[]): Promise<void> {
  await idbSet('deals', items);
}

export async function loadReports(): Promise<RunReport[]> {
  return idbGet<RunReport[]>('reports', []);
}

export async function saveReports(items: RunReport[]): Promise<void> {
  await idbSet('reports', items);
}

export async function loadLiveStatus(): Promise<LiveStatus | null> {
  return idbGet<LiveStatus | null>('live_status', null);
}

export async function saveLiveStatus(s: LiveStatus | null): Promise<void> {
  await idbSet('live_status', s);
}
