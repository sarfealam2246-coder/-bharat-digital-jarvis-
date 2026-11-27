import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  BarChart3,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  KeyRound,
  Mail,
  MessageSquare,
  Play,
  RefreshCw,
  Send,
  Trash2,
  Volume2,
  X
} from 'lucide-react';
import {
  DEFAULT_VAULT,
  loadDeals,
  loadLeads,
  loadLiveStatus,
  loadReports,
  loadVault,
  saveDeals,
  saveLeads,
  saveLiveStatus,
  saveReports,
  saveVault
} from './services/localMemory';
import {
  draftSmartReplyInApk,
  pullCloudState,
  syncVaultToGitHub,
  triggerWorkflowAction
} from './services/githubSync';
import { DealItem, LeadItem, LiveStatus, RunReport, VaultKeys } from './types/jarvis';

type Tab = 'jarvis' | 'leads' | 'vault';

export default function App() {
  const [tab, setTab] = useState<Tab>('jarvis');
  const [vault, setVault] = useState<VaultKeys>(DEFAULT_VAULT);
  const [leads, setLeads] = useState<LeadItem[]>([]);
  const [deals, setDeals] = useState<DealItem[]>([]);
  const [reports, setReports] = useState<RunReport[]>([]);
  const [liveStatus, setLiveStatus] = useState<LiveStatus | null>(null);
  const [jarvisUrl, setJarvisUrl] = useState<string>('');
  const [toast, setToast] = useState<string>('');
  const [busy, setBusy] = useState<boolean>(false);

  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    jarvisPanel: true,
    graphCity: true,
    graphCat: false,
    runReports: true,
    vaultGithub: true,
    vaultAi: true,
    vaultCloudflare: false,
    vaultComms: false
  });
  const [expandedLead, setExpandedLead] = useState<string | null>(null);
  const [replyInputs, setReplyInputs] = useState<Record<string, string>>({});
  const [cornerOpen, setCornerOpen] = useState<boolean>(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const toggleSec = (k: string) => setOpenSections((p) => ({ ...p, [k]: !p[k] }));
  const notify = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 4000);
  };

  useEffect(() => {
    (async () => {
      const [v, l, d, r, ls] = await Promise.all([
        loadVault(),
        loadLeads(),
        loadDeals(),
        loadReports(),
        loadLiveStatus()
      ]);
      setVault(v);
      setLeads(l);
      setDeals(d);
      setReports(r);
      setLiveStatus(ls);
      if (v.githubRepo) {
        setJarvisUrl(`https://raw.githubusercontent.com/${v.githubRepo}/main/memory/jarvis_brief.mp3?t=${Date.now()}`);
      }
    })();
  }, []);

  const speakText = (script: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(script);
      u.lang = 'hi-IN';
      window.speechSynthesis.speak(u);
    }
  };

  const speakJarvis = () => {
    const script =
      liveStatus?.jarvisScript ||
      `नमस्ते सर, मैं जार्विस बोल रहा हूँ। अभी आपके पास ${leads.filter((x) => x.status === 'NEW').length} नए क्लाइंट डेमो और ${deals.filter((x) => x.status === 'PENDING_APPROVAL').length} पेंडिंग डील हैं।`;
    if (jarvisUrl && audioRef.current) {
      audioRef.current.src = jarvisUrl;
      audioRef.current.play().catch(() => speakText(script));
    } else {
      speakText(script);
    }
    notify('Jarvis हिंदी रिपोर्ट सुना रहा है...');
  };

  const handleSyncFromCloud = async () => {
    setBusy(true);
    try {
      const cloud = await pullCloudState(vault);
      if (cloud.leads.length > 0) {
        const map = new Map<string, LeadItem>();
        leads.forEach((x) => map.set(x.slug, x));
        cloud.leads.forEach((x) => {
          const prev = map.get(x.slug);
          map.set(x.slug, prev ? { ...x, clientReplyText: prev.clientReplyText || x.clientReplyText, jarvisReplyDraft: prev.jarvisReplyDraft || x.jarvisReplyDraft } : x);
        });
        const merged = Array.from(map.values());
        setLeads(merged);
        await saveLeads(merged);
      }
      if (cloud.deals.length > 0) {
        const dMap = new Map<string, DealItem>();
        deals.forEach((x) => dMap.set(x.id, x));
        cloud.deals.forEach((x) => dMap.set(x.id, x));
        const mergedDeals = Array.from(dMap.values());
        setDeals(mergedDeals);
        await saveDeals(mergedDeals);
      }
      if (cloud.reports.length > 0) {
        setReports(cloud.reports);
        await saveReports(cloud.reports);
      }
      if (cloud.liveStatus) {
        setLiveStatus(cloud.liveStatus);
        await saveLiveStatus(cloud.liveStatus);
      }
      setJarvisUrl(cloud.jarvisAudioUrl);
      notify('क्लाउड से ताज़ा रिपोर्ट और डेटा सिंक हो गया!');
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : 'Sync error');
    } finally {
      setBusy(false);
    }
  };

  const handleSaveSingleKey = async (field: keyof VaultKeys, val: string, label: string) => {
    const next = { ...vault, [field]: val.trim() };
    setVault(next);
    await saveVault(next);
    notify(`${label} फोन में सेव हो गया!`);
  };

  const handleSyncSecrets = async () => {
    setBusy(true);
    try {
      await saveVault(vault);
      const msg = await syncVaultToGitHub(vault);
      notify(msg);
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : 'Secrets sync error');
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteLead = async (slug: string) => {
    const next = leads.filter((l) => l.slug !== slug);
    setLeads(next);
    await saveLeads(next);
    notify('क्लाइंट रिकॉर्ड हटाया गया।');
  };

  const openWhatsAppWithText = (lead: LeadItem, text: string) => {
    const digits = (lead.phone || '').replace(/\D/g, '');
    const waPhone = digits.length === 10 ? `91${digits}` : digits;
    if (waPhone) {
      window.open(`https://wa.me/${waPhone}?text=${encodeURIComponent(text)}`, '_blank');
    } else if (lead.postUrl) {
      window.open(lead.postUrl, '_blank');
    } else {
      notify('इस क्लाइंट का WhatsApp नंबर उपलब्ध नहीं है — ईमेल या डेमो लिंक इस्तेमाल करें।');
    }
  };

  const handleSendWhatsAppLead = async (lead: LeadItem) => {
    openWhatsAppWithText(lead, lead.pitchMessage);
    const updated = leads.map((l) => (l.slug === lead.slug ? { ...l, status: 'SENT' as const } : l));
    setLeads(updated);
    await saveLeads(updated);
    try {
      const price = String(lead.offerPriceInr || lead.amountInr || 2999);
      await triggerWorkflowAction(vault, 'mark_sent', lead.slug, price);
    } catch {
      // Saved locally in IndexedDB
    }
    notify(`${lead.name} के लिए WhatsApp खोला गया!`);
  };

  const handleSendEmailLead = async (lead: LeadItem) => {
    if (!lead.email) {
      notify('इस क्लाइंट का ईमेल उपलब्ध नहीं है।');
      return;
    }
    const subject = `${lead.name} के लिए तैयार वेबसाइट डेमो (${lead.city})`;
    window.open(
      `mailto:${encodeURIComponent(lead.email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(lead.pitchMessage)}`,
      '_blank'
    );
    const updated = leads.map((l) => (l.slug === lead.slug ? { ...l, status: 'SENT' as const } : l));
    setLeads(updated);
    await saveLeads(updated);
    try {
      const price = String(lead.offerPriceInr || lead.amountInr || 2999);
      await triggerWorkflowAction(vault, 'send_email', lead.slug, price);
    } catch {
      // Saved locally in IndexedDB
    }
    notify(`${lead.name} को ईमेल भेजा जा रहा है!`);
  };

  const handleCornerSkipLead = async (lead: LeadItem) => {
    const updated = leads.map((l) => (l.slug === lead.slug ? { ...l, status: 'SKIPPED' as const } : l));
    setLeads(updated);
    await saveLeads(updated);
    notify(`${lead.name} को छोड़ा गया।`);
  };

  const handleSaveClientReply = async (lead: LeadItem) => {
    const txt = (replyInputs[lead.slug] || '').trim();
    if (!txt) {
      notify('पहले क्लाइंट का WhatsApp रिप्लाई पेस्ट करें।');
      return;
    }
    setBusy(true);
    try {
      const draft = await draftSmartReplyInApk(vault, lead, txt);
      const updated = leads.map((l) =>
        l.slug === lead.slug ? { ...l, clientReplyText: txt, jarvisReplyDraft: draft } : l
      );
      setLeads(updated);
      await saveLeads(updated);
      speakText(`सर, ${lead.name} का जवाब सेव हो गया है। मैंने अगला जवाब तैयार कर दिया है।`);
      notify('Jarvis ने क्लाइंट के रिप्लाई के हिसाब से नया जवाब तैयार कर दिया!');
    } finally {
      setBusy(false);
    }
  };

  const handleMarkPaidUnlock = async (lead: LeadItem) => {
    const defaultAmt = lead.offerPriceInr || lead.amountInr || 2999;
    const raw = window.prompt(`${lead.name} से कितने रुपये (₹) मिले?`, String(defaultAmt));
    if (!raw) return;
    const amt = parseInt(raw.replace(/\D/g, ''), 10) || defaultAmt;
    setBusy(true);
    try {
      await triggerWorkflowAction(vault, 'unlock_and_upi', lead.slug, String(amt));
      const updated = leads.map((l) =>
        l.slug === lead.slug ? { ...l, status: 'PAID' as const, amountInr: amt } : l
      );
      setLeads(updated);
      await saveLeads(updated);
      if (liveStatus) {
        const nextLs = { ...liveStatus, totalEarnedInr: (liveStatus.totalEarnedInr || 0) + amt };
        setLiveStatus(nextLs);
        await saveLiveStatus(nextLs);
      }
      speakText(`बधाई हो सर! ${lead.name} से ${amt} रुपये मिले, डेमो अनलॉक हो रहा है।`);
      notify(`₹${amt} दर्ज! डेमो अनलॉक होने के लिए GitHub पर भेजा गया।`);
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : 'Unlock trigger failed');
    } finally {
      setBusy(false);
    }
  };

  const handleApproveDeal = async (deal: DealItem, mode: 'approve_reply' | 'approve_deal_upi' | 'cancel_deal') => {
    try {
      const amt = String(deal.amountInr || 2999);
      await triggerWorkflowAction(vault, mode, deal.id, amt);
      const nextStatus = mode === 'cancel_deal' ? 'CANCELLED' : mode === 'approve_deal_upi' ? 'PAID' : 'REPLIED';
      const updated = deals.map((d) => (d.id === deal.id ? { ...d, status: nextStatus as DealItem['status'] } : d));
      setDeals(updated);
      await saveDeals(updated);
      notify(mode === 'approve_deal_upi' ? 'डील पक्की! UPI लिंक भेजा जा रहा है।' : 'आदेश भेज दिया गया!');
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : 'Action failed');
    }
  };

  const cityCounts = useMemo(() => {
    const m: Record<string, number> = {};
    leads.forEach((l) => {
      m[l.city || 'India'] = (m[l.city || 'India'] || 0) + 1;
    });
    return Object.entries(m).sort((a, b) => b[1] - a[1]).slice(0, 6);
  }, [leads]);

  const catCounts = useMemo(() => {
    const m: Record<string, number> = {};
    leads.forEach((l) => {
      m[l.category || 'business'] = (m[l.category || 'business'] || 0) + 1;
    });
    return Object.entries(m).sort((a, b) => b[1] - a[1]).slice(0, 6);
  }, [leads]);

  const pendingOutbox = leads.filter((l) => l.status === 'NEW');
  const pendingDeals = deals.filter((d) => d.status === 'PENDING_APPROVAL');
  const cornerBadgeCount = pendingOutbox.length + pendingDeals.length;

  return (
    <div className="min-h-screen bg-[#F0F2F5] text-[#1C1E21] pb-24">
      <audio ref={audioRef} className="hidden" />

      <header className="sticky top-0 z-20 bg-white border-b border-gray-300 px-4 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-extrabold text-[#1877F2]">Bharat Digital Jarvis</h1>
          <p className="text-xs text-gray-600">24×7 All-India Relay & Locked Demo Studio</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={speakJarvis}
            className="bg-[#42B72A] text-white text-xs font-bold px-3 py-2 rounded-lg flex items-center gap-1"
          >
            <Volume2 className="w-4 h-4" /> Jarvis
          </button>
          <button
            onClick={handleSyncFromCloud}
            disabled={busy}
            className="bg-[#1877F2] text-white text-xs font-bold px-3 py-2 rounded-lg flex items-center gap-1"
          >
            <RefreshCw className={`w-4 h-4 ${busy ? 'animate-spin' : ''}`} /> Sync
          </button>
        </div>
      </header>

      {toast && (
        <div className="mx-4 mt-3 bg-white border-l-4 border-[#1877F2] border border-gray-300 rounded-lg px-3 py-2 text-sm font-semibold text-[#1C1E21]">
          {toast}
        </div>
      )}

      <nav className="bg-white border-b border-gray-300 px-3 py-2 flex gap-2">
        {[
          { id: 'jarvis', label: 'Jarvis & ग्राफ' },
          { id: 'leads', label: `क्लाइंट (${leads.length})` },
          { id: 'vault', label: 'Vault (10 Keys)' }
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id as Tab)}
            className={`flex-1 py-2 text-xs font-bold rounded-lg border ${
              tab === t.id ? 'bg-[#1877F2] text-white border-[#1877F2]' : 'bg-[#F0F2F5] text-[#1C1E21] border-gray-300'
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="p-4 max-w-2xl mx-auto space-y-3">
        {tab === 'jarvis' && (
          <>
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-white border border-gray-300 rounded-xl p-3 text-center">
                <div className="text-xs text-gray-500 font-semibold">कुल डेमो</div>
                <div className="text-xl font-extrabold text-[#1877F2]">{leads.length}</div>
              </div>
              <div className="bg-white border border-gray-300 rounded-xl p-3 text-center">
                <div className="text-xs text-gray-500 font-semibold">पेंडिंग टिक</div>
                <div className="text-xl font-extrabold text-amber-600">{cornerBadgeCount}</div>
              </div>
              <div className="bg-white border border-gray-300 rounded-xl p-3 text-center">
                <div className="text-xs text-gray-500 font-semibold">कुल कमाई</div>
                <div className="text-xl font-extrabold text-[#42B72A]">₹{liveStatus?.totalEarnedInr || 0}</div>
              </div>
            </div>

            <div className="bg-white border border-gray-300 rounded-xl overflow-hidden">
              <button
                onClick={() => toggleSec('jarvisPanel')}
                className="w-full px-4 py-3 flex items-center justify-between font-bold text-sm bg-white"
              >
                <span className="flex items-center gap-2 text-[#1877F2]">
                  <Volume2 className="w-4 h-4" /> Jarvis हिंदी रिपोर्ट और आदेश
                </span>
                {openSections.jarvisPanel ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
              {openSections.jarvisPanel && (
                <div className="px-4 pb-4 border-t border-gray-200 pt-3 space-y-3">
                  <p className="text-sm text-[#1C1E21] leading-relaxed">
                    {liveStatus?.jarvisScript || 'अभी Sync दबाएँ या नया एजेंट चलाएँ — Jarvis यहीं पूरा हाल हिंदी में सुनाएगा।'}
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={speakJarvis}
                      className="flex-1 bg-[#1877F2] text-white text-xs font-bold py-2.5 rounded-lg flex items-center justify-center gap-1"
                    >
                      <Play className="w-4 h-4" /> आवाज़ में सुनें
                    </button>
                    <button
                      onClick={async () => {
                        setBusy(true);
                        try {
                          await triggerWorkflowAction(vault, '', '', '2999');
                          notify('Agent 1 अभी चालू हो गया! 1–2 मिनट बाद Sync दबाएँ।');
                        } catch (e: unknown) {
                          notify(e instanceof Error ? e.message : 'Run error');
                        } finally {
                          setBusy(false);
                        }
                      }}
                      className="flex-1 bg-[#42B72A] text-white text-xs font-bold py-2.5 rounded-lg flex items-center justify-center gap-1"
                    >
                      <Send className="w-4 h-4" /> अभी बॉट चलाएँ
                    </button>
                  </div>
                </div>
              )}
            </div>

            <div className="bg-white border border-gray-300 rounded-xl overflow-hidden">
              <button
                onClick={() => toggleSec('graphCity')}
                className="w-full px-4 py-3 flex items-center justify-between font-bold text-sm"
              >
                <span className="flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-[#1877F2]" /> शहर-वार ग्राफ (All-India Radar)
                </span>
                {openSections.graphCity ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
              {openSections.graphCity && (
                <div className="px-4 pb-4 border-t border-gray-200 pt-3 space-y-2">
                  {cityCounts.length === 0 ? (
                    <p className="text-xs text-gray-500">डेटा आने पर शहर ग्राफ अपने-आप दिखेगा।</p>
                  ) : (
                    cityCounts.map(([city, cnt]) => (
                      <div key={city} className="space-y-1">
                        <div className="flex justify-between text-xs font-semibold">
                          <span>{city}</span>
                          <span>{cnt}</span>
                        </div>
                        <div className="w-full bg-[#F0F2F5] h-2.5 rounded-full overflow-hidden">
                          <div
                            className="bg-[#1877F2] h-full rounded-full"
                            style={{ width: `${Math.min(100, (cnt / Math.max(1, cityCounts[0][1])) * 100)}%` }}
                          />
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            <div className="bg-white border border-gray-300 rounded-xl overflow-hidden">
              <button
                onClick={() => toggleSec('graphCat')}
                className="w-full px-4 py-3 flex items-center justify-between font-bold text-sm"
              >
                <span className="flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-[#42B72A]" /> बिज़नेस कैटेगरी ग्राफ
                </span>
                {openSections.graphCat ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
              {openSections.graphCat && (
                <div className="px-4 pb-4 border-t border-gray-200 pt-3 space-y-2">
                  {catCounts.length === 0 ? (
                    <p className="text-xs text-gray-500">अभी कोई कैटेगरी डेटा नहीं है।</p>
                  ) : (
                    catCounts.map(([cat, cnt]) => (
                      <div key={cat} className="space-y-1">
                        <div className="flex justify-between text-xs font-semibold">
                          <span>{cat}</span>
                          <span>{cnt}</span>
                        </div>
                        <div className="w-full bg-[#F0F2F5] h-2.5 rounded-full overflow-hidden">
                          <div
                            className="bg-[#42B72A] h-full rounded-full"
                            style={{ width: `${Math.min(100, (cnt / Math.max(1, catCounts[0][1])) * 100)}%` }}
                          />
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            <div className="bg-white border border-gray-300 rounded-xl overflow-hidden">
              <button
                onClick={() => toggleSec('runReports')}
                className="w-full px-4 py-3 flex items-center justify-between font-bold text-sm"
              >
                <span>📋 24×7 लाइव रन रिपोर्ट्स ({reports.length})</span>
                {openSections.runReports ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
              {openSections.runReports && (
                <div className="px-4 pb-4 border-t border-gray-200 pt-3 space-y-2">
                  {reports.length === 0 ? (
                    <p className="text-xs text-gray-500">हर रन की रिपोर्ट (काम मिले या न मिले) यहाँ दिखेगी।</p>
                  ) : (
                    [...reports].reverse().slice(0, 10).map((r, i) => (
                      <div key={i} className="bg-[#F0F2F5] border border-gray-200 rounded-lg p-2.5 text-xs">
                        <div className="font-bold text-[#1877F2]">{r.shift.toUpperCase()} • {r.city}</div>
                        <div className="text-[#1C1E21] mt-0.5">{r.summary}</div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </>
        )}

        {tab === 'leads' && (
          <div className="space-y-2.5">
            {leads.length === 0 ? (
              <div className="bg-white border border-gray-300 rounded-xl p-5 text-center text-sm text-gray-600">
                अभी कोई क्लाइंट सेव नहीं है। ऊपर <strong>Sync</strong> दबाएँ या बॉट चलाएँ।
              </div>
            ) : (
              leads.map((l) => {
                const isOpen = expandedLead === l.slug;
                const price = l.offerPriceInr || l.amountInr || 2999;
                return (
                  <div key={l.slug} className="bg-white border border-gray-300 rounded-xl overflow-hidden">
                    <button
                      onClick={() => setExpandedLead(isOpen ? null : l.slug)}
                      className="w-full px-4 py-3 flex items-center justify-between text-left"
                    >
                      <div>
                        <div className="font-bold text-sm text-[#1C1E21]">{l.name}</div>
                        <div className="text-xs text-gray-500">
                          {l.city} • {l.category} • <span className="font-bold text-[#42B72A]">₹{price}</span> •{' '}
                          <span className="font-bold text-[#1877F2]">{l.status}</span>
                        </div>
                      </div>
                      {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                    {isOpen && (
                      <div className="px-4 pb-4 border-t border-gray-200 pt-3 space-y-2.5 text-xs">
                        <div className="flex flex-wrap gap-2 text-xs text-gray-700">
                          {l.phone && <span className="bg-[#F0F2F5] px-2 py-1 rounded">📞 {l.phone}</span>}
                          {l.email && <span className="bg-[#F0F2F5] px-2 py-1 rounded">✉️ {l.email}</span>}
                          {l.marketRateInr && <span className="bg-[#F0F2F5] px-2 py-1 rounded">मार्केट रेट: {l.marketRateInr}</span>}
                        </div>

                        <p className="text-[#1C1E21]"><strong>हिंदी सारांश:</strong> {l.hindiSummary}</p>
                        <p className="bg-[#F0F2F5] p-2.5 rounded-lg text-gray-700">{l.pitchMessage}</p>

                        <div className="flex flex-wrap gap-2 pt-1">
                          <a href={l.demoUrl} target="_blank" rel="noreferrer" className="bg-[#1877F2] text-white font-bold px-3 py-2 rounded-lg flex items-center gap-1">
                            <ExternalLink className="w-3.5 h-3.5" /> डेमो देखें
                          </a>
                          {(l.phone || l.postUrl) && (
                            <button onClick={() => handleSendWhatsAppLead(l)} className="bg-[#42B72A] text-white font-bold px-3 py-2 rounded-lg flex items-center gap-1">
                              <Check className="w-3.5 h-3.5" /> WhatsApp खोलें
                            </button>
                          )}
                          {l.email && (
                            <button onClick={() => handleSendEmailLead(l)} className="bg-[#1877F2] text-white font-bold px-3 py-2 rounded-lg flex items-center gap-1">
                              <Mail className="w-3.5 h-3.5" /> Email भेजें
                            </button>
                          )}
                          <button onClick={() => handleMarkPaidUnlock(l)} className="bg-amber-600 text-white font-bold px-3 py-2 rounded-lg flex items-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" /> पेमेंट मिला (Unlock)
                          </button>
                          <button onClick={() => handleDeleteLead(l.slug)} className="bg-red-600 text-white font-bold px-3 py-2 rounded-lg flex items-center gap-1">
                            <Trash2 className="w-3.5 h-3.5" /> Delete
                          </button>
                        </div>

                        <div className="bg-[#F0F2F5] border border-gray-300 rounded-lg p-2.5 space-y-2 mt-2">
                          <div className="font-bold text-[#1877F2]">📋 क्लाइंट का WhatsApp रिप्लाई यहाँ डालें</div>
                          <textarea
                            rows={2}
                            value={replyInputs[l.slug] ?? l.clientReplyText ?? ''}
                            onChange={(e) => setReplyInputs({ ...replyInputs, [l.slug]: e.target.value })}
                            placeholder="क्लाइंट ने WhatsApp पर जो लिखा, यहाँ Paste करें..."
                            className="w-full bg-white border border-gray-300 rounded-lg p-2 text-xs text-[#1C1E21]"
                          />
                          <button
                            onClick={() => handleSaveClientReply(l)}
                            disabled={busy}
                            className="w-full bg-[#1877F2] text-white font-bold py-2 rounded-lg"
                          >
                            🤖 Jarvis को बताएँ व अगला जवाब बनवाएँ
                          </button>
                          {l.jarvisReplyDraft && (
                            <div className="bg-white border border-gray-300 rounded-lg p-2 space-y-1.5">
                              <div className="font-bold text-[#42B72A]">Jarvis का तैयार जवाब:</div>
                              <p className="text-gray-800">{l.jarvisReplyDraft}</p>
                              <button
                                onClick={() => openWhatsAppWithText(l, l.jarvisReplyDraft || '')}
                                className="bg-[#42B72A] text-white font-bold px-3 py-1.5 rounded-lg"
                              >
                                📱 यह नया जवाब WhatsApp पर भेजें
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}

        {tab === 'vault' && (
          <div className="space-y-3">
            <button
              onClick={handleSyncSecrets}
              disabled={busy}
              className="w-full bg-[#42B72A] text-white font-extrabold py-3 rounded-xl text-sm"
            >
              {busy ? 'Sync हो रहा है...' : '🔄 Sync All 10 Keys to GitHub Secrets'}
            </button>

            <VaultGroup title="1. GitHub कनेक्शन (PAT व Repo)" open={openSections.vaultGithub} onToggle={() => toggleSec('vaultGithub')}>
              <KeyCard label="GitHub PAT Token" value={vault.githubPat} onChange={(val) => setVault({ ...vault, githubPat: val })} onSave={(val) => handleSaveSingleKey('githubPat', val, 'GitHub PAT')} secret />
              <KeyCard label="GitHub Repo (owner/repo)" value={vault.githubRepo} onChange={(val) => setVault({ ...vault, githubRepo: val })} onSave={(val) => handleSaveSingleKey('githubRepo', val, 'GitHub Repo')} />
            </VaultGroup>

            <VaultGroup title="2. मुख्य AI Keys (NVIDIA, Gemini, Groq)" open={openSections.vaultAi} onToggle={() => toggleSec('vaultAi')}>
              <KeyCard label="NVIDIA Master API Key (34+ AI)" value={vault.nvidiaKey} onChange={(val) => setVault({ ...vault, nvidiaKey: val })} onSave={(val) => handleSaveSingleKey('nvidiaKey', val, 'NVIDIA Key')} secret />
              <KeyCard label="Gemini API Key" value={vault.geminiKey} onChange={(val) => setVault({ ...vault, geminiKey: val })} onSave={(val) => handleSaveSingleKey('geminiKey', val, 'Gemini Key')} secret />
              <KeyCard label="Groq API Key" value={vault.groqKey} onChange={(val) => setVault({ ...vault, groqKey: val })} onSave={(val) => handleSaveSingleKey('groqKey', val, 'Groq Key')} secret />
            </VaultGroup>

            <VaultGroup title="3. Cloudflare ID/Token व Single Cloud Key" open={openSections.vaultCloudflare} onToggle={() => toggleSec('vaultCloudflare')}>
              <KeyCard label="Cloudflare Account ID" value={vault.cloudflareAccountId} onChange={(val) => setVault({ ...vault, cloudflareAccountId: val })} onSave={(val) => handleSaveSingleKey('cloudflareAccountId', val, 'Cloudflare Account ID')} />
              <KeyCard label="Cloudflare API Token" value={vault.cloudflareApiToken} onChange={(val) => setVault({ ...vault, cloudflareApiToken: val })} onSave={(val) => handleSaveSingleKey('cloudflareApiToken', val, 'Cloudflare API Token')} secret />
              <KeyCard label="Cloud Single API Key (बिना ID वाला)" value={vault.cloudSingleKey} onChange={(val) => setVault({ ...vault, cloudSingleKey: val })} onSave={(val) => handleSaveSingleKey('cloudSingleKey', val, 'Cloud Single Key')} secret />
            </VaultGroup>

            <VaultGroup title="4. Gmail Inbox व UPI ID" open={openSections.vaultComms} onToggle={() => toggleSec('vaultComms')}>
              <KeyCard label="Business Gmail Address" value={vault.gmailAddress} onChange={(val) => setVault({ ...vault, gmailAddress: val })} onSave={(val) => handleSaveSingleKey('gmailAddress', val, 'Gmail Address')} />
              <KeyCard label="Gmail App Password (16 अक्षर)" value={vault.gmailAppPassword} onChange={(val) => setVault({ ...vault, gmailAppPassword: val })} onSave={(val) => handleSaveSingleKey('gmailAppPassword', val, 'Gmail App Password')} secret />
              <KeyCard label="आपका UPI ID (पेमेंट के लिए)" value={vault.upiId} onChange={(val) => setVault({ ...vault, upiId: val })} onSave={(val) => handleSaveSingleKey('upiId', val, 'UPI ID')} />
            </VaultGroup>
          </div>
        )}
      </main>

      <div className="fixed bottom-4 right-4 z-30">
        {!cornerOpen ? (
          <button
            onClick={() => setCornerOpen(true)}
            className="bg-[#1877F2] text-white font-bold px-4 py-3 rounded-full border border-blue-700 flex items-center gap-2 text-sm"
          >
            <MessageSquare className="w-4 h-4" />
            <span>संदेश बॉक्स ({cornerBadgeCount})</span>
          </button>
        ) : (
          <div className="w-80 max-h-[75vh] overflow-y-auto bg-white border-2 border-[#1877F2] rounded-2xl p-3 space-y-2.5">
            <div className="flex items-center justify-between border-b border-gray-200 pb-2">
              <strong className="text-sm text-[#1877F2]">⚡ 1-टिक संदेश व डील बॉक्स</strong>
              <button onClick={() => setCornerOpen(false)} className="p-1 text-gray-500">
                <X className="w-4 h-4" />
              </button>
            </div>

            {pendingDeals.map((d) => (
              <div key={d.id} className="bg-[#F0F2F5] border border-gray-300 rounded-xl p-2.5 text-xs space-y-1.5">
                <div className="font-bold text-[#1877F2] flex items-center gap-1">
                  <Mail className="w-3.5 h-3.5" /> {d.sender}
                </div>
                <p>{d.hindiExplanation}</p>
                <div className="flex gap-1.5">
                  <button onClick={() => handleApproveDeal(d, 'approve_deal_upi')} className="flex-1 bg-[#42B72A] text-white font-bold py-1.5 rounded-lg">
                    ✅ ₹{d.amountInr || 2999} UPI भेजें
                  </button>
                  <button onClick={() => handleApproveDeal(d, 'cancel_deal')} className="bg-red-600 text-white font-bold px-2.5 py-1.5 rounded-lg">
                    ❌
                  </button>
                </div>
              </div>
            ))}

            {pendingOutbox.slice(0, 5).map((l) => {
              const price = l.offerPriceInr || l.amountInr || 2999;
              return (
                <div key={l.slug} className="bg-[#F0F2F5] border border-gray-300 rounded-xl p-2.5 text-xs space-y-1.5">
                  <div className="font-bold text-[#1C1E21]">
                    {l.name} ({l.city}) • <span className="text-[#42B72A]">₹{price}</span>
                  </div>
                  <p className="text-gray-600">{l.hindiSummary}</p>
                  <div className="flex flex-wrap gap-1.5">
                    <a href={l.demoUrl} target="_blank" rel="noreferrer" className="bg-white border border-gray-300 text-[#1877F2] font-bold px-2 py-1.5 rounded-lg">
                      👁️ डेमो
                    </a>
                    {(l.phone || l.postUrl) && (
                      <button onClick={() => handleSendWhatsAppLead(l)} className="flex-1 bg-[#42B72A] text-white font-bold py-1.5 rounded-lg flex items-center justify-center gap-1">
                        <Check className="w-3.5 h-3.5" /> WhatsApp
                      </button>
                    )}
                    {l.email && (
                      <button onClick={() => handleSendEmailLead(l)} className="flex-1 bg-[#1877F2] text-white font-bold py-1.5 rounded-lg flex items-center justify-center gap-1">
                        <Mail className="w-3.5 h-3.5" /> Email
                      </button>
                    )}
                    <button onClick={() => handleCornerSkipLead(l)} className="bg-gray-400 text-white font-bold px-2 py-1.5 rounded-lg">
                      छोड़ें
                    </button>
                  </div>
                </div>
              );
            })}

            {cornerBadgeCount === 0 && (
              <p className="text-xs text-gray-500 text-center py-3">अभी कोई नया पेंडिंग संदेश नहीं है।</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function VaultGroup({ title, open, onToggle, children }: { title: string; open: boolean; onToggle: () => void; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-gray-300 rounded-xl overflow-hidden">
      <button onClick={onToggle} className="w-full px-4 py-3 flex items-center justify-between font-bold text-sm">
        <span className="flex items-center gap-2"><KeyRound className="w-4 h-4 text-[#1877F2]" /> {title}</span>
        {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>
      {open && <div className="px-4 pb-4 border-t border-gray-200 pt-3 space-y-3">{children}</div>}
    </div>
  );
}

function KeyCard({ label, value, onChange, onSave, secret }: { label: string; value: string; onChange: (v: string) => void; onSave: (v: string) => void; secret?: boolean }) {
  return (
    <div className="bg-[#F0F2F5] border border-gray-300 rounded-lg p-2.5 space-y-1.5">
      <label className="block text-xs font-bold text-[#1C1E21]">{label}</label>
      <div className="flex gap-2">
        <input
          type={secret ? 'password' : 'text'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="यहाँ पेस्ट करें..."
          className="flex-1 bg-white border border-gray-300 rounded-lg px-2.5 py-1.5 text-xs text-[#1C1E21]"
        />
        <button onClick={() => onSave(value)} className="bg-[#1877F2] text-white text-xs font-bold px-3 py-1.5 rounded-lg">
          Save
        </button>
      </div>
    </div>
  );
}
