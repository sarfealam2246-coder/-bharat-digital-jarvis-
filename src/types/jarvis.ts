export interface VaultKeys {
  githubPat: string;
  githubRepo: string;
  nvidiaKey: string;
  geminiKey: string;
  groqKey: string;
  cloudflareAccountId: string;
  cloudflareApiToken: string;
  cloudSingleKey: string;
  gmailAddress: string;
  gmailAppPassword: string;
  upiId: string;
}

export interface LeadItem {
  slug: string;
  name: string;
  category: string;
  city: string;
  phone?: string;
  email?: string;
  postUrl?: string;
  demoUrl: string;
  hindiSummary: string;
  pitchMessage: string;
  status: 'NEW' | 'SENT' | 'PAID' | 'SKIPPED';
  payUrl?: string;
  amountInr?: number;
  offerPriceInr?: number;
  marketRateInr?: string;
  clientReplyText?: string;
  jarvisReplyDraft?: string;
  foundAt: string;
}

export interface DealItem {
  id: string;
  sender: string;
  subject: string;
  clientText: string;
  hindiExplanation: string;
  suggestedReply: string;
  status: 'PENDING_APPROVAL' | 'REPLIED' | 'PAID' | 'CANCELLED';
  payUrl?: string;
  amountInr?: number;
  receivedAt: string;
}

export interface RunReport {
  ts: string;
  shift: string;
  city: string;
  built: number;
  emails: number;
  summary: string;
}

export interface LiveStatus {
  lastRunAt: string;
  activeShift: string;
  lastCity: string;
  newBuilt: number;
  newEmails: number;
  pendingOutbox: number;
  pendingDeals: number;
  totalEarnedInr: number;
  jarvisScript: string;
  statusText: string;
}
