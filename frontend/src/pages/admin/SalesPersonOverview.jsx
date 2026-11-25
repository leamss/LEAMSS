import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Users, Phone, PhoneCall, PhoneIncoming, PhoneOutgoing, MessageSquare,
  Mail, Calendar, Clock, CheckCircle2, XCircle, AlertCircle,
  Search, RefreshCw, ChevronRight, Filter, Play, Pause,
  Download, Volume2, ArrowLeft, UserCheck, Shield, ExternalLink,
  ChevronDown, Copy, Check, Target
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || (typeof window !== 'undefined' && window.location.hostname.includes('leamss.com') ? 'https://api.leamss.com' : 'http://localhost:8001');
const API = `${BACKEND_URL}/api`;

const formatPhoneNumber = (phone) => {
  if (!phone) return 'No phone';
  let p = String(phone).trim();
  if (p.includes('E') || p.includes('e')) {
    try {
      const num = Number(p);
      if (!isNaN(num)) {
        p = num.toLocaleString('fullwide', { useGrouping: false });
      }
    } catch (e) {}
  }
  return p;
};

// Embedded Audio Player for Call Recordings
function CallAudioPlayer({ recordingUrl, durationSeconds, callerName }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(durationSeconds || 0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const audioRef = useRef(null);

  const fullUrl = useMemo(() => {
    if (!recordingUrl) return '';
    if (recordingUrl.startsWith('http') || recordingUrl.startsWith('blob:') || recordingUrl.startsWith('data:')) {
      return recordingUrl;
    }
    const base = BACKEND_URL || 'http://localhost:8001';
    return `${base}${recordingUrl.startsWith('/') ? '' : '/'}${recordingUrl}`;
  }, [recordingUrl]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onTimeUpdate = () => setCurrentTime(audio.currentTime);
    const onLoadedMetadata = () => {
      if (audio.duration && !isNaN(audio.duration)) {
        setDuration(Math.round(audio.duration));
      }
    };
    const onEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };

    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('loadedmetadata', onLoadedMetadata);
    audio.addEventListener('ended', onEnded);

    return () => {
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('loadedmetadata', onLoadedMetadata);
      audio.removeEventListener('ended', onEnded);
    };
  }, []);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      audio.play().then(() => setIsPlaying(true)).catch(() => {
        toast.error('Unable to play audio recording');
      });
    }
  };

  const handleSeek = (e) => {
    const newTime = parseFloat(e.target.value);
    setCurrentTime(newTime);
    if (audioRef.current) {
      audioRef.current.currentTime = newTime;
    }
  };

  const cyclePlaybackRate = () => {
    const rates = [1, 1.25, 1.5, 2];
    const nextRate = rates[(rates.indexOf(playbackRate) + 1) % rates.length];
    setPlaybackRate(nextRate);
    if (audioRef.current) {
      audioRef.current.playbackRate = nextRate;
    }
  };

  const formatSecs = (sec) => {
    const s = Math.floor(sec || 0);
    const m = Math.floor(s / 60);
    const rem = s % 60;
    return `${m}:${rem < 10 ? '0' : ''}${rem}`;
  };

  if (!recordingUrl) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-slate-400 bg-slate-50 px-2 py-1 rounded border border-dashed border-slate-200">
        <Volume2 className="h-3.5 w-3.5" /> No audio recording
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 bg-slate-900 text-white px-3 py-2 rounded-xl text-xs shadow-sm max-w-md w-full">
      <audio ref={audioRef} src={fullUrl} preload="metadata" />
      <button
        type="button"
        onClick={togglePlay}
        className="h-7 w-7 rounded-full bg-emerald-500 hover:bg-emerald-400 flex items-center justify-center text-slate-950 flex-shrink-0 transition-transform active:scale-95 shadow"
      >
        {isPlaying ? <Pause className="h-3.5 w-3.5 fill-current" /> : <Play className="h-3.5 w-3.5 fill-current ml-0.5" />}
      </button>

      <div className="flex-1 min-w-0">
        <div className="flex justify-between items-center text-[10px] text-slate-400 mb-0.5">
          <span className="font-mono">{formatSecs(currentTime)}</span>
          <span className="truncate max-w-[120px] text-slate-300 font-medium">{callerName || 'Call Recording'}</span>
          <span className="font-mono">{formatSecs(duration || durationSeconds || 0)}</span>
        </div>
        <input
          type="range"
          min="0"
          max={duration || durationSeconds || 100}
          step="0.1"
          value={currentTime}
          onChange={handleSeek}
          className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-400"
        />
      </div>

      <button
        type="button"
        onClick={cyclePlaybackRate}
        className="px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-mono text-slate-300 border border-slate-700"
      >
        {playbackRate}x
      </button>

      <a
        href={fullUrl}
        download="call_recording.wav"
        target="_blank"
        rel="noreferrer"
        className="p-1 text-slate-400 hover:text-white transition-colors"
        title="Download recording"
      >
        <Download className="h-3.5 w-3.5" />
      </a>
    </div>
  );
}

export default function SalesPersonOverview({ initialTab = 'internal', onOpenLeadWorkspace, initialRepId = null, autoSelectSingleRep = false }) {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(initialTab || 'internal'); // 'internal' | 'external'
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState({ team_summary: {}, sales_reps: [] });
  const [searchTerm, setSearchTerm] = useState('');
  
  // Drilldown navigation states:
  // Level 1: selectedRep = null
  // Level 2: selectedRep != null, selectedClient = null
  // Level 3: selectedRep != null, selectedClient != null
  const [selectedRep, setSelectedRep] = useState(null);
  const [repDetail, setRepDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [selectedClient, setSelectedClient] = useState(null);

  // Level 2 & Level 3 filters
  const [clientSearchTerm, setClientSearchTerm] = useState('');
  const [clientStageFilter, setClientStageFilter] = useState('all');
  const [activityFilter, setActivityFilter] = useState('all');
  const [copiedPhone, setCopiedPhone] = useState(false);

  const token = localStorage.getItem('token');
  const authHeader = useMemo(() => ({ headers: { Authorization: `Bearer ${token}` } }), [token]);

  // Sync activeTab when initialTab changes
  useEffect(() => {
    if (initialTab && (initialTab === 'internal' || initialTab === 'external')) {
      setActiveTab(initialTab);
    }
  }, [initialTab]);

  const loadOverview = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/crm/sales-reps/overview`, authHeader);
      const overviewData = res.data || { team_summary: {}, sales_reps: [] };
      setData(overviewData);
      if (initialRepId) {
        const found = overviewData.sales_reps?.find(r => r.id === initialRepId || r.email === initialRepId);
        if (found) {
          loadRepDetail(found);
        }
      } else if (autoSelectSingleRep && overviewData.sales_reps?.length === 1) {
        loadRepDetail(overviewData.sales_reps[0]);
      }
    } catch (err) {
      console.error(err);
      toast.error('Failed to load Sales Person overview');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOverview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadRepDetail = async (rep, actType = 'all') => {
    setSelectedRep(rep);
    setSelectedClient(null);
    setLoadingDetail(true);
    try {
      const res = await axios.get(`${API}/crm/sales-reps/${rep.id}/detail?activity_type=${actType}`, authHeader);
      setRepDetail(res.data);
    } catch (err) {
      console.error(err);
      toast.error('Failed to load assigned clients');
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleSelectClient = (client) => {
    setSelectedClient(client);
    setActivityFilter('all');
  };

  const handleCopyPhone = (phone) => {
    if (!phone) return;
    navigator.clipboard.writeText(phone);
    setCopiedPhone(true);
    toast.success('Phone copied to clipboard');
    setTimeout(() => setCopiedPhone(false), 2000);
  };

  // Filter salespersons for active tab
  const internalReps = useMemo(() => {
    return (data.sales_reps || []).filter(r => r.salesperson_type === 'internal');
  }, [data.sales_reps]);

  const externalReps = useMemo(() => {
    return (data.sales_reps || []).filter(r => r.salesperson_type === 'external');
  }, [data.sales_reps]);

  const displayedReps = useMemo(() => {
    const list = activeTab === 'external' ? externalReps : internalReps;
    if (!searchTerm) return list;
    const q = searchTerm.toLowerCase();
    return list.filter(r =>
      (r.name || '').toLowerCase().includes(q) ||
      (r.email || '').toLowerCase().includes(q)
    );
  }, [activeTab, internalReps, externalReps, searchTerm]);

  // Clients filtered in Level 2
  const filteredClients = useMemo(() => {
    if (!repDetail?.clients) return [];
    return repDetail.clients.filter(c => {
      const matchesSearch = !clientSearchTerm ||
        (c.name || '').toLowerCase().includes(clientSearchTerm.toLowerCase()) ||
        (c.email || '').toLowerCase().includes(clientSearchTerm.toLowerCase()) ||
        (c.phone || '').toLowerCase().includes(clientSearchTerm.toLowerCase()) ||
        (c.service_interested || '').toLowerCase().includes(clientSearchTerm.toLowerCase()) ||
        (c.country_of_interest || '').toLowerCase().includes(clientSearchTerm.toLowerCase());

      if (!matchesSearch) return false;

      if (clientStageFilter !== 'all') {
        const stage = (c.stage || c.status || '').toLowerCase();
        if (clientStageFilter.toLowerCase() === 'converted') {
          if (!['converted', 'won', 'closed_won', 'case_created'].includes(stage) && !c.converted) return false;
        } else if (stage !== clientStageFilter.toLowerCase()) {
          return false;
        }
      }

      return true;
    });
  }, [repDetail, clientSearchTerm, clientStageFilter]);

  // Activities for selected client in Level 3
  const clientActivities = useMemo(() => {
    if (!repDetail?.activities || !selectedClient) return [];
    const list = repDetail.activities.filter(a => a.lead_id === selectedClient.id);
    if (activityFilter === 'all') return list;
    return list.filter(a => a.type === activityFilter);
  }, [repDetail, selectedClient, activityFilter]);

  // Stage Badge helper
  const renderStageBadge = (stage) => {
    const s = String(stage || 'new').toLowerCase();
    let bg = 'bg-slate-100 text-slate-700 border-slate-200';
    if (['won', 'converted', 'case_created', 'payment_received'].includes(s)) {
      bg = 'bg-emerald-50 text-emerald-700 border-emerald-200';
    } else if (['lost', 'not_interested', 'archived', 'closed_lost'].includes(s)) {
      bg = 'bg-rose-50 text-rose-700 border-rose-200';
    } else if (['connected', 'proposal', 'assessment', 'in_progress'].includes(s)) {
      bg = 'bg-blue-50 text-blue-700 border-blue-200';
    } else if (['contacted', 'callback', 'follow_up'].includes(s)) {
      bg = 'bg-amber-50 text-amber-700 border-amber-200';
    }
    return (
      <Badge variant="outline" className={`font-semibold capitalize px-2 py-0.5 text-xs ${bg}`}>
        {s.replace(/_/g, ' ')}
      </Badge>
    );
  };

  /* ────────────────────────────────────────────────────────────
     LEVEL 3: CLIENT DETAILS & ACTIVITY HISTORY
     Flow: Salesperson → Assigned Clients/Leads → Client Details → Activities
     ──────────────────────────────────────────────────────────── */
  if (selectedRep && selectedClient) {
    return (
      <div className="space-y-6" data-testid="level3-client-details-activities">
        {/* Breadcrumb Navigation */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center gap-2 text-sm text-slate-500 overflow-x-auto pb-1 sm:pb-0">
            <button
              onClick={() => { setSelectedRep(null); setSelectedClient(null); }}
              className="hover:text-slate-900 font-medium transition-colors whitespace-nowrap"
            >
              Sales Team
            </button>
            <ChevronRight className="h-4 w-4 text-slate-400 flex-shrink-0" />
            <button
              onClick={() => setSelectedClient(null)}
              className="hover:text-slate-900 font-medium transition-colors whitespace-nowrap"
            >
              {selectedRep.name}
            </button>
            <ChevronRight className="h-4 w-4 text-slate-400 flex-shrink-0" />
            <span className="font-semibold text-slate-900 whitespace-nowrap">{selectedClient.name}</span>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setSelectedClient(null)}
            className="self-start sm:self-auto text-xs"
          >
            <ArrowLeft className="h-3.5 w-3.5 mr-1" />
            Back to Assigned Clients
          </Button>
        </div>

        {/* Client Profile Header Banner */}
        <Card className="p-6 bg-gradient-to-r from-slate-900 to-slate-800 text-white rounded-2xl shadow-sm border-0">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="flex items-start gap-4">
              <div className="h-16 w-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-teal-400 flex items-center justify-center text-white text-xl font-bold shadow-md flex-shrink-0">
                {(selectedClient.name || 'C').slice(0, 2).toUpperCase()}
              </div>
              <div className="space-y-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-2xl font-bold">{selectedClient.name}</h2>
                  {renderStageBadge(selectedClient.stage || selectedClient.status)}
                  <Badge variant="outline" className="bg-white/10 text-slate-200 border-white/20 text-xs">
                    Assigned to: {selectedRep.name} ({selectedRep.salesperson_type === 'external' ? 'External Partner' : 'Internal Sales'})
                  </Badge>
                </div>
                <div className="flex flex-wrap items-center gap-4 text-sm text-slate-300">
                  {selectedClient.phone && (
                    <span className="flex items-center gap-1.5">
                      <Phone className="h-4 w-4 text-emerald-400" />
                      <span>{formatPhoneNumber(selectedClient.phone)}</span>
                      <button
                        onClick={() => handleCopyPhone(selectedClient.phone)}
                        className="text-slate-400 hover:text-white p-0.5"
                        title="Copy phone"
                      >
                        {copiedPhone ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                      </button>
                    </span>
                  )}
                  {selectedClient.email && (
                    <span className="flex items-center gap-1.5">
                      <Mail className="h-4 w-4 text-sky-400" />
                      <span>{selectedClient.email}</span>
                    </span>
                  )}
                  {selectedClient.country_of_interest && (
                    <span className="flex items-center gap-1.5">
                      <span className="text-amber-400">📍</span>
                      <span>Target: {selectedClient.country_of_interest}</span>
                    </span>
                  )}
                  {selectedClient.service_interested && (
                    <span className="flex items-center gap-1.5">
                      <span className="text-teal-400">🎯</span>
                      <span>Service: {selectedClient.service_interested}</span>
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Quick Action to open full lead workspace if available */}
            {onOpenLeadWorkspace && (
              <Button
                onClick={() => onOpenLeadWorkspace(selectedClient)}
                className="bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold shadow self-start lg:self-center"
              >
                <ExternalLink className="h-4 w-4 mr-1.5" />
                Open 360° Lead Workspace
              </Button>
            )}
          </div>
        </Card>

        {/* Activity History Header & Filter Tabs */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-bold text-slate-900">Activity History</h3>
              <p className="text-xs text-slate-500">
                Complete log of calls, WhatsApp messages, emails, follow-ups, and scheduled meetings for {selectedClient.name}.
              </p>
            </div>

            {/* Activity Type Filters */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
              {[
                { key: 'all', label: 'All Activities' },
                { key: 'call', label: 'Calls', icon: Phone },
                { key: 'whatsapp', label: 'WhatsApp', icon: MessageSquare },
                { key: 'email', label: 'Emails', icon: Mail },
                { key: 'followup', label: 'Follow-ups', icon: Clock },
                { key: 'meeting', label: 'Meetings', icon: Calendar },
              ].map(f => {
                const Icon = f.icon;
                const active = activityFilter === f.key;
                return (
                  <button
                    key={f.key}
                    onClick={() => setActivityFilter(f.key)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                      active
                        ? 'bg-slate-900 text-white shadow-xs'
                        : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    {Icon && <Icon className="h-3.5 w-3.5" />}
                    <span>{f.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Activities Timeline List */}
          <div className="space-y-3">
            {clientActivities.length === 0 ? (
              <Card className="p-8 text-center bg-white border border-dashed border-slate-300">
                <Clock className="h-10 w-10 text-slate-300 mx-auto mb-2" />
                <p className="text-sm font-semibold text-slate-700">No activities found</p>
                <p className="text-xs text-slate-400 mt-1">
                  No interactions matching the selected filter have been recorded for this client yet.
                </p>
              </Card>
            ) : (
              clientActivities.map((act) => {
                const isCall = act.type === 'call';
                const isWA = act.type === 'whatsapp';
                const isEmail = act.type === 'email';
                const isFollowUp = act.type === 'followup';
                const isMeeting = act.type === 'meeting';

                return (
                  <Card key={act.id} className="p-4 bg-white border border-slate-200/80 shadow-xs hover:border-slate-300 transition-all">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3">
                        {/* Icon by Activity Type */}
                        <div className={`p-2.5 rounded-xl flex-shrink-0 ${
                          isCall ? 'bg-amber-100 text-amber-700' :
                          isWA ? 'bg-emerald-100 text-emerald-700' :
                          isEmail ? 'bg-blue-100 text-blue-700' :
                          isFollowUp ? 'bg-purple-100 text-purple-700' :
                          isMeeting ? 'bg-rose-100 text-rose-700' :
                          'bg-slate-100 text-slate-700'
                        }`}>
                          {isCall && <Phone className="h-4 w-4" />}
                          {isWA && <MessageSquare className="h-4 w-4" />}
                          {isEmail && <Mail className="h-4 w-4" />}
                          {isFollowUp && <Clock className="h-4 w-4" />}
                          {isMeeting && <Calendar className="h-4 w-4" />}
                        </div>

                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-sm text-slate-900">{act.title}</span>
                            {act.direction && (
                              <Badge variant="outline" className="text-[10px] uppercase font-medium px-1.5 py-0 bg-slate-50">
                                {act.direction}
                              </Badge>
                            )}
                            {act.outcome && (
                              <Badge variant="outline" className="text-[10px] capitalize px-1.5 py-0 bg-emerald-50 text-emerald-700 border-emerald-200">
                                {act.outcome}
                              </Badge>
                            )}
                          </div>

                          {act.description && (
                            <p className="text-xs text-slate-600 line-clamp-3 whitespace-pre-wrap">{act.description}</p>
                          )}

                          {/* Embedded Call Audio Player if Call Recording exists */}
                          {isCall && act.recording_url && (
                            <div className="pt-2">
                              <CallAudioPlayer
                                recordingUrl={act.recording_url}
                                durationSeconds={act.duration_seconds}
                                callerName={act.client_name || selectedClient.name}
                              />
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Timestamp */}
                      <span className="text-[11px] text-slate-400 whitespace-nowrap font-mono flex-shrink-0">
                        {act.timestamp ? new Date(act.timestamp).toLocaleString() : ''}
                      </span>
                    </div>
                  </Card>
                );
              })
            )}
          </div>
        </div>
      </div>
    );
  }

  /* ────────────────────────────────────────────────────────────
     LEVEL 2: ASSIGNED CLIENTS / LEADS FOR SELECTED SALESPERSON
     Flow: Salesperson → Assigned Clients/Leads
     ──────────────────────────────────────────────────────────── */
  if (selectedRep) {
    return (
      <div className="space-y-6" data-testid="level2-assigned-clients">
        {/* Breadcrumb Navigation */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <button
              onClick={() => setSelectedRep(null)}
              className="hover:text-slate-900 font-medium transition-colors"
            >
              Sales Team
            </button>
            <ChevronRight className="h-4 w-4 text-slate-400" />
            <span className="font-semibold text-slate-900">{selectedRep.name}</span>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setSelectedRep(null)}
            className="self-start sm:self-auto text-xs"
          >
            <ArrowLeft className="h-3.5 w-3.5 mr-1" />
            Back to Salespersons
          </Button>
        </div>

        {/* Selected Salesperson Header Banner */}
        <Card className="p-6 bg-white border border-slate-200/80 rounded-2xl shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className={`h-14 w-14 rounded-2xl flex items-center justify-center text-white font-bold text-lg shadow-sm ${
                selectedRep.salesperson_type === 'external'
                  ? 'bg-gradient-to-br from-amber-500 to-orange-600'
                  : 'bg-gradient-to-br from-indigo-600 to-blue-700'
              }`}>
                {(selectedRep.name || 'SP').slice(0, 2).toUpperCase()}
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-xl font-bold text-slate-900">{selectedRep.name}</h2>
                  <Badge className={`text-xs px-2 py-0.5 font-semibold ${
                    selectedRep.salesperson_type === 'external'
                      ? 'bg-amber-100 text-amber-800 border-amber-300'
                      : 'bg-indigo-100 text-indigo-800 border-indigo-300'
                  }`}>
                    {selectedRep.role_label || (selectedRep.salesperson_type === 'external' ? 'External Partner (L0)' : 'Internal Sales')}
                  </Badge>
                  {selectedRep.designation && selectedRep.designation !== selectedRep.role_label && (
                    <Badge variant="outline" className="text-xs bg-slate-50 text-slate-600">
                      {selectedRep.designation}
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-slate-500 mt-0.5">{selectedRep.email}</p>
                {selectedRep.role_description && (
                  <p className="text-[11px] text-slate-500 mt-1 max-w-xl">
                    <span className="font-semibold text-slate-700">Role & Scope:</span> {selectedRep.role_description}
                  </p>
                )}
              </div>
            </div>

            {/* Total Assigned Clients Count */}
            <div className="flex items-center gap-3 bg-slate-50 px-4 py-2.5 rounded-xl border border-slate-200 self-start sm:self-auto">
              <Users className="h-5 w-5 text-indigo-600" />
              <div>
                <p className="text-xs text-slate-500 font-medium">Total Assigned Clients/Leads</p>
                <p className="text-xl font-bold text-slate-900">
                  {loadingDetail ? '...' : (repDetail?.clients?.length ?? selectedRep.total_assigned_clients)}
                </p>
              </div>
            </div>
          </div>
        </Card>

        {/* Search & Stage Filter Bar */}
        <Card className="p-4 bg-white border border-slate-200/80">
          <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
            <div className="relative w-full sm:w-80">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search clients by name, phone, email..."
                value={clientSearchTerm}
                onChange={(e) => setClientSearchTerm(e.target.value)}
                className="pl-9 h-9 text-sm"
              />
            </div>

            <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
              <span className="text-xs text-slate-500 font-medium flex items-center gap-1 mr-1">
                <Filter className="h-3.5 w-3.5" /> Stage:
              </span>
              {[
                { key: 'all', label: 'All' },
                { key: 'new', label: 'New' },
                { key: 'contacted', label: 'Contacted' },
                { key: 'connected', label: 'Connected' },
                { key: 'converted', label: 'Converted' },
                { key: 'lost', label: 'Lost' },
              ].map(st => (
                <button
                  key={st.key}
                  onClick={() => setClientStageFilter(st.key)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                    clientStageFilter === st.key
                      ? 'bg-slate-900 text-white shadow-xs'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {st.label}
                </button>
              ))}
            </div>
          </div>
        </Card>

        {/* Clients Table */}
        <Card className="overflow-hidden border border-slate-200 shadow-xs bg-white">
          {loadingDetail ? (
            <div className="p-12 text-center text-slate-500 text-sm">
              <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-indigo-600" />
              Loading assigned clients...
            </div>
          ) : filteredClients.length === 0 ? (
            <div className="p-12 text-center">
              <Users className="h-10 w-10 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-700">No assigned clients found</p>
              <p className="text-xs text-slate-400 mt-1">
                No clients match your filter or are currently assigned to {selectedRep.name}.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 font-semibold text-xs">
                  <tr>
                    <th className="py-3.5 px-4">Client Name</th>
                    <th className="py-3.5 px-4">Contact</th>
                    <th className="py-3.5 px-4">Service & Target</th>
                    <th className="py-3.5 px-4 text-center">Status / Stage</th>
                    <th className="py-3.5 px-4 text-center">Interactions</th>
                    <th className="py-3.5 px-4 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredClients.map((client) => {
                    const totalInteractions = (client.total_calls || 0) + (client.total_messages || 0) + (client.total_emails || 0) + (client.total_followups || 0);
                    return (
                      <tr
                        key={client.id}
                        onClick={() => handleSelectClient(client)}
                        className="hover:bg-slate-50/80 cursor-pointer transition-colors group"
                      >
                        {/* Client Name */}
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-3">
                            <div className="h-9 w-9 rounded-full bg-slate-800 text-white flex items-center justify-center font-bold text-xs shadow-xs flex-shrink-0">
                              {(client.name || 'C').slice(0, 2).toUpperCase()}
                            </div>
                            <div>
                              <p className="font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors">
                                {client.name}
                              </p>
                              {client.source && (
                                <p className="text-[11px] text-slate-400">Source: {client.source}</p>
                              )}
                            </div>
                          </div>
                        </td>

                        {/* Contact */}
                        <td className="py-3.5 px-4">
                          <div className="text-xs text-slate-700 space-y-0.5">
                            <div className="flex items-center gap-1 font-mono">
                              <Phone className="h-3 w-3 text-slate-400" />
                              <span>{formatPhoneNumber(client.phone)}</span>
                            </div>
                            {client.email && (
                              <div className="flex items-center gap-1 text-slate-500">
                                <Mail className="h-3 w-3 text-slate-400" />
                                <span className="truncate max-w-[180px]">{client.email}</span>
                              </div>
                            )}
                          </div>
                        </td>

                        {/* Service & Country */}
                        <td className="py-3.5 px-4">
                          <div className="text-xs">
                            <span className="font-medium text-slate-800">{client.service_interested || 'General Consultation'}</span>
                            <p className="text-[11px] text-slate-400">Target: {client.country_of_interest || 'N/A'}</p>
                          </div>
                        </td>

                        {/* Stage */}
                        <td className="py-3.5 px-4 text-center">
                          {renderStageBadge(client.stage || client.status)}
                        </td>

                        {/* Interactions */}
                        <td className="py-3.5 px-4 text-center">
                          <div className="inline-flex items-center gap-1.5 text-xs text-slate-600 bg-slate-100 px-2 py-1 rounded-lg">
                            <MessageSquare className="h-3 w-3 text-slate-400" />
                            <span className="font-medium">{totalInteractions}</span>
                            <span className="text-[10px] text-slate-400">logs</span>
                          </div>
                        </td>

                        {/* Action */}
                        <td className="py-3.5 px-4 text-center">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSelectClient(client);
                            }}
                            className="text-xs text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 font-medium"
                          >
                            Details & History →
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    );
  }

  /* ────────────────────────────────────────────────────────────
     LEVEL 1: SALESPERSONS DIRECTORY
     Requirements:
     - Show Internal and External Salespersons separately.
     - For each salesperson, show ONLY: Name, Total Assigned Clients/Leads.
     - When Admin clicks on a salesperson → show all their assigned clients.
     ──────────────────────────────────────────────────────────── */
  return (
    <div className="space-y-6" data-testid="level1-salespersons-directory">
      {/* 1. Header & Segmented Tabs */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900">Salespersons & Client Assignments</h2>
            <p className="text-xs text-slate-500 mt-1">
              Select an internal or external salesperson to review all their assigned clients and activity history.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            <Button
              onClick={() => navigate('/admin/sales/targets')}
              className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white text-xs flex items-center gap-1.5 shadow-sm"
              data-testid="goto-targets-management-btn"
            >
              <Target className="h-3.5 w-3.5" />
              Target Management
            </Button>
            <Button
              onClick={loadOverview}
              variant="outline"
              size="sm"
              disabled={loading}
              className="text-xs"
            >
              <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Separated Tabs: Internal Salespersons vs External Salespersons */}
        <div className="flex items-center gap-2 border-b border-slate-200 pt-2">
          <button
            onClick={() => setActiveTab('internal')}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold border-b-2 transition-all ${
              activeTab === 'internal'
                ? 'border-indigo-600 text-indigo-600 bg-indigo-50/50 rounded-t-lg'
                : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
            data-testid="tab-internal-salespersons"
          >
            <UserCheck className="h-4 w-4" />
            <span>Internal Salespersons</span>
            <Badge variant="secondary" className="text-xs font-bold px-1.5 py-0 bg-slate-100 text-slate-700">
              {internalReps.length}
            </Badge>
          </button>

          <button
            onClick={() => setActiveTab('external')}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold border-b-2 transition-all ${
              activeTab === 'external'
                ? 'border-amber-600 text-amber-600 bg-amber-50/50 rounded-t-lg'
                : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
            data-testid="tab-external-salespersons"
          >
            <Users className="h-4 w-4" />
            <span>External Salespersons / Partners</span>
            <Badge variant="secondary" className="text-xs font-bold px-1.5 py-0 bg-slate-100 text-slate-700">
              {externalReps.length}
            </Badge>
          </button>
        </div>
      </div>

      {/* 2. Search Bar */}
      <Card className="p-4 bg-white border border-slate-200/80">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            placeholder={`Search ${activeTab === 'external' ? 'external partners' : 'internal salespersons'} by name...`}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 h-9 text-sm"
          />
        </div>
      </Card>

      {/* 3. Salesperson Cards (Clean: shows ONLY Name and Total Assigned Clients/Leads) */}
      {loading ? (
        <div className="p-12 text-center text-slate-500 text-sm">
          <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-indigo-600" />
          Loading sales team data...
        </div>
      ) : displayedReps.length === 0 ? (
        <Card className="p-12 text-center bg-white border border-dashed border-slate-300">
          <Users className="h-10 w-10 text-slate-300 mx-auto mb-2" />
          <p className="text-sm font-semibold text-slate-700">
            No {activeTab === 'external' ? 'External Salespersons / Partners' : 'Internal Salespersons'} found
          </p>
          <p className="text-xs text-slate-400 mt-1">
            {searchTerm ? 'No salespersons match your search query.' : 'No members configured in this category.'}
          </p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="salespersons-grid">
          {displayedReps.map((rep) => {
            const isExternal = rep.salesperson_type === 'external';
            const initials = (rep.name || 'SP').split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();

            return (
              <Card
                key={rep.id}
                onClick={() => loadRepDetail(rep)}
                className="p-5 bg-white border border-slate-200/80 hover:border-indigo-400 hover:shadow-md cursor-pointer transition-all group flex flex-col justify-between"
                data-testid={`salesperson-card-${rep.id}`}
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    {/* Salesperson Avatar */}
                    <div className={`h-12 w-12 rounded-xl flex items-center justify-center text-white font-bold text-base shadow-xs ${
                      isExternal
                        ? 'bg-gradient-to-br from-amber-500 to-orange-600'
                        : 'bg-gradient-to-br from-indigo-600 to-blue-700'
                    }`}>
                      {initials}
                    </div>

                    <Badge variant="outline" className={`text-xs px-2 py-0.5 font-semibold ${
                      isExternal
                        ? 'bg-amber-50 text-amber-700 border-amber-200'
                        : 'bg-indigo-50 text-indigo-700 border-indigo-200'
                    }`}>
                      {rep.role_label || (isExternal ? 'External Partner (L0)' : 'Internal Sales')}
                    </Badge>
                  </div>

                  {/* SALESPERSON NAME */}
                  <h3 className="text-lg font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">
                    {rep.name}
                  </h3>
                  <div className="flex items-center gap-2 mt-0.5">
                    <p className="text-xs text-slate-400 truncate">{rep.email}</p>
                    {rep.designation && rep.designation !== rep.role_label && (
                      <span className="text-[11px] text-slate-600 font-medium bg-slate-100 px-1.5 py-0.5 rounded">
                        {rep.designation}
                      </span>
                    )}
                  </div>

                  {/* ROLE & RESPONSIBILITIES SUMMARY */}
                  {rep.role_description && (
                    <p className="text-[11px] text-slate-500 line-clamp-2 mt-2 bg-slate-50 p-2 rounded-lg border border-slate-100/80">
                      <span className="font-semibold text-slate-600">Scope:</span> {rep.role_description}
                    </p>
                  )}
                </div>

                {/* TOTAL ASSIGNED CLIENTS / LEADS */}
                <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between">
                  <div>
                    <p className="text-xs text-slate-500 font-medium">Total Assigned Clients/Leads</p>
                    <p className="text-2xl font-extrabold text-slate-900 mt-0.5">
                      {rep.total_assigned_clients}
                    </p>
                  </div>

                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-xs text-indigo-600 group-hover:translate-x-1 transition-transform p-0 hover:bg-transparent font-semibold flex items-center gap-1"
                  >
                    <span>View Clients</span>
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
