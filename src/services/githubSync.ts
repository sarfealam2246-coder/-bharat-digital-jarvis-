import nacl from 'tweetnacl';
import { seal } from 'tweetnacl-sealedbox-js';
import { DealItem, LeadItem, LiveStatus, RunReport, VaultKeys } from '../types/jarvis';

function b64ToUint8(b64: string): Uint8Array {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function uint8ToB64(arr: Uint8Array): string {
  let s = '';
  for (let i = 0; i < arr.length; i++) s += String.fromCharCode(arr[i]);
  return btoa(s);
}

async function putSecret(repo: string, pat: string, pubKeyId: string, pubKeyB64: string, name: string, value: string) {
  if (!value.trim()) return;
  const msgBytes = new TextEncoder().encode(value.trim());
  const sealed = seal(msgBytes, b64ToUint8(pubKeyB64));
  const res = await fetch(`https://api.github.com/repos/${repo}/actions/secrets/${name}`, {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${pat}`,
      Accept: 'application/vnd.github+json',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ encrypted_value: uint8ToB64(sealed), key_id: pubKeyId })
  });
  if (!res.ok) throw new Error(`Secret ${name} sync failed (${res.status})`);
}

export async function syncVaultToGitHub(v: VaultKeys): Promise<string> {
  if (!v.githubPat.trim() || !v.githubRepo.includes('/')) {
    throw new Error('GitHub PAT aur Repo Name (owner/repo) zaroori hai.');
  }
  const keyRes = await fetch(`https://api.github.com/repos/${v.githubRepo}/actions/secrets/public-key`, {
    headers: { Authorization: `Bearer ${v.githubPat}`, Accept: 'application/vnd.github+json' }
  });
  if (!keyRes.ok) throw new Error(`GitHub Public Key error (${keyRes.status})`);
  const { key_id, key } = await keyRes.json();

  const pairs: [string, string][] = [
    ['GH_AUTO_PAT', v.githubPat],
    ['NVIDIA_API_KEY', v.nvidiaKey],
    ['GEMINI_API_KEY', v.geminiKey],
    ['GROQ_API_KEY', v.groqKey],
    ['CLOUDFLARE_ACCOUNT_ID', v.cloudflareAccountId],
    ['CLOUDFLARE_API_TOKEN', v.cloudflareApiToken],
    ['CLOUD_SINGLE_API_KEY', v.cloudSingleKey],
    ['GMAIL_ADDRESS', v.gmailAddress],
    ['GMAIL_APP_PASSWORD', v.gmailAppPassword],
    ['MY_UPI_ID', v.upiId]
  ];
  let count = 0;
  for (const [k, val] of pairs) {
    if (val.trim()) {
      await putSecret(v.githubRepo, v.githubPat, key_id, key, k, val);
      count++;
    }
  }
  return `${count} Secrets GitHub par surakshit sync ho gaye!`;
}

async function fetchRawJson<T>(repo: string, pat: string, path: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(`https://api.github.com/repos/${repo}/contents/${path}?t=${Date.now()}`, {
      headers: pat ? { Authorization: `Bearer ${pat}`, Accept: 'application/vnd.github.raw' } : { Accept: 'application/vnd.github.raw' }
    });
    if (!res.ok) return fallback;
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}

export async function pullCloudState(v: VaultKeys): Promise<{
  leads: LeadItem[];
  deals: DealItem[];
  reports: RunReport[];
  liveStatus: LiveStatus | null;
  jarvisAudioUrl: string;
}> {
  const [leads, deals, reports, liveStatus] = await Promise.all([
    fetchRawJson<LeadItem[]>(v.githubRepo, v.githubPat, 'memory/leads_history.json', []),
    fetchRawJson<DealItem[]>(v.githubRepo, v.githubPat, 'memory/deal_chats.json', []),
    fetchRawJson<RunReport[]>(v.githubRepo, v.githubPat, 'memory/run_reports.json', []),
    fetchRawJson<LiveStatus | null>(v.githubRepo, v.githubPat, 'memory/live_status.json', null)
  ]);
  const jarvisAudioUrl = `https://raw.githubusercontent.com/${v.githubRepo}/main/memory/jarvis_brief.mp3?t=${Date.now()}`;
  return { leads, deals, reports, liveStatus, jarvisAudioUrl };
}

export async function triggerWorkflowAction(
  v: VaultKeys,
  apkAction: string = '',
  targetId: string = '',
  amount: string = '1499'
): Promise<void> {
  if (!v.githubPat.trim() || !v.githubRepo.includes('/')) {
    throw new Error('Pehle Vault me GitHub PAT aur Repo save karein.');
  }
  const res = await fetch(
    `https://api.github.com/repos/${v.githubRepo}/actions/workflows/agent_1_relay.yml/dispatches`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${v.githubPat}`,
        Accept: 'application/vnd.github+json',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        ref: 'main',
        inputs: { apk_action: apkAction, apk_target_id: targetId, apk_amount: amount }
      })
    }
  );
  if (!res.ok) throw new Error(`Workflow trigger failed (${res.status})`);
}

void nacl;
