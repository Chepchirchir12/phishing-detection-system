import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Mail, Shield, ShieldAlert, ShieldCheck, RefreshCw, 
  ChevronRight, Info, LayoutDashboard, Inbox, AlertTriangle, 
  BarChart3, User, Filter, Zap, Plus, X, Trash2
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

function App() {
  const [view, setView] = useState('dashboard');
  const [emails, setEmails] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState('All Accounts');
  const [stats, setStats] = useState({ total: 0, phishing: 0, legitimate: 0, phishing_percent: 0 });
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [showAddAccount, setShowAddAccount] = useState(false);
  const [showPasteModal, setShowPasteModal] = useState(false);
  const [pasteData, setPasteData] = useState({ subject: '', body: '', sender: '' });
  const [pasteResult, setPasteResult] = useState(null);
  const [newAccount, setNewAccount] = useState({ email: '', password: '', name: '', imap_server: 'imap.gmail.com' });
  const [error, setError] = useState(null);

  useEffect(() => {
    const init = async () => {
      console.log("Initial load...");
      await fetchAccounts();
      await fetchStats();
      await fetchEmails();
    };
    init();
  }, []);

  useEffect(() => {
    if (selectedAccount) {
      fetchEmails();
      fetchStats();
    }
  }, [selectedAccount, view]);

  const fetchAccounts = async () => {
    try {
      const res = await axios.get(`${API_BASE}/accounts`);
      setAccounts(res.data);
    } catch (err) { setError("Failed to load accounts"); }
  };

  const fetchStats = async () => {
    try {
      const accParam = selectedAccount === 'All Accounts' ? 'All Accounts' : selectedAccount;
      const url = `${API_BASE}/stats?account=${encodeURIComponent(accParam)}`;
      const res = await axios.get(url);
      setStats(res.data);
    } catch (err) { 
      console.error("Stats error:", err); 
    }
  };

  const fetchEmails = async () => {
    setLoading(true);
    try {
      const folder = view === 'inbox' ? 'inbox' : (view === 'spam' ? 'spam' : 'all');
      const accParam = selectedAccount === 'All Accounts' ? 'All Accounts' : selectedAccount;
      const url = `${API_BASE}/emails?account=${encodeURIComponent(accParam)}&folder=${folder}`;
      const res = await axios.get(url);
      setEmails(res.data);
    } catch (err) { 
      console.error("Emails error:", err);
      setError("Failed to load emails"); 
    }
    finally { setLoading(false); }
  };

  const handleSync = async () => {
    setActionLoading(true);
    setError(null);
    try {
      await axios.post(`${API_BASE}/fetch`);
      await fetchEmails();
      await fetchStats();
    } catch (err) { 
      setError(err.response?.data?.detail || "Failed to sync emails. Check credentials."); 
    }
    finally { setActionLoading(false); }
  };

  const handleReclassify = async () => {
    setActionLoading(true);
    try {
      await axios.post(`${API_BASE}/reclassify`);
      await fetchEmails();
      await fetchStats();
    } catch (err) { setError("Failed to reclassify"); }
    finally { setActionLoading(false); }
  };

  const handleDeleteEmail = async (id) => {
    if (!window.confirm("Are you sure you want to delete this email?")) return;
    try {
      await axios.delete(`${API_BASE}/emails/${id}`);
      setSelectedEmail(null);
      await fetchEmails();
      await fetchStats();
    } catch (err) {
      setError("Failed to delete email");
    }
  };

  const handleAddAccount = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_BASE}/accounts`, newAccount);
      setShowAddAccount(false);
      setNewAccount({ email: '', password: '', name: '', imap_server: 'imap.gmail.com' });
      fetchAccounts();
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to add account");
    }
  };

  const handleDeleteAccount = async (email) => {
    if (!window.confirm(`Are you sure you want to remove ${email}?`)) return;
    try {
      await axios.delete(`${API_BASE}/accounts/${encodeURIComponent(email)}`);
      if (selectedAccount === email) setSelectedAccount('All Accounts');
      fetchAccounts();
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to remove account. (Note: Original accounts from .env cannot be removed from here)");
    }
  };

  const handlePasteAnalysis = async (e) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/analyze-paste`, pasteData);
      setPasteResult(res.data);
    } catch (err) {
      alert("Failed to analyze pasted email");
    } finally {
      setActionLoading(false);
    }
  };

  const openEmail = async (email) => {
    setSelectedEmail(email);
    setExplanation(null);
    try {
      const res = await axios.get(`${API_BASE}/explain/${email.id}`);
      setExplanation(res.data);
    } catch (err) { console.error(err); }
  };

  return (
    <div className="flex h-screen bg-[#f8fafc] text-slate-900 font-sans">
      {/* Sidebar */}
      <div className="w-72 bg-white border-r border-slate-200 flex flex-col shadow-sm">
        <div className="p-8 flex items-center gap-3">
          <div className="bg-blue-600 p-2 rounded-lg text-white">
            <Shield size={24} />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-800">PhishGuard</h1>
        </div>

        <nav className="flex-1 px-4 space-y-1 overflow-y-auto">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-4 mb-2 mt-4">Main Menu</div>
          <SidebarItem icon={<LayoutDashboard size={20}/>} label="Dashboard" active={view === 'dashboard'} onClick={() => setView('dashboard')} />
          <SidebarItem icon={<Inbox size={20}/>} label="Inbox" active={view === 'inbox'} onClick={() => setView('inbox')} count={stats.legitimate} />
          <SidebarItem icon={<AlertTriangle size={20}/>} label="Spam / Phishing" active={view === 'spam'} onClick={() => setView('spam')} count={stats.phishing} />
          <SidebarItem icon={<Mail size={20}/>} label="All Emails" active={view === 'all'} onClick={() => setView('all')} count={stats.total} />
          
          <button 
            onClick={() => setShowPasteModal(true)}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-slate-500 hover:bg-blue-50 hover:text-blue-700 transition-all duration-200 font-semibold mt-2"
          >
            <Zap size={20} className="text-amber-500" />
            Paste Email
          </button>

          <div className="flex justify-between items-center px-4 mb-2 mt-8">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Accounts</div>
            <button onClick={() => setShowAddAccount(true)} className="text-blue-600 hover:bg-blue-50 p-1 rounded-md transition">
              <Plus size={14} />
            </button>
          </div>
          
          <div className="space-y-1">
            <button 
              onClick={() => setSelectedAccount('All Accounts')}
              className={`w-full text-left px-4 py-2 rounded-xl text-sm transition ${selectedAccount === 'All Accounts' ? 'bg-blue-50 text-blue-700 font-bold' : 'text-slate-500 hover:bg-slate-50'}`}
            >
              All Accounts
            </button>
            {accounts.map(acc => (
              <div key={acc.email} className="group relative">
                <button 
                  onClick={() => setSelectedAccount(acc.email)}
                  className={`w-full text-left px-4 py-2 rounded-xl text-sm transition truncate pr-8 ${selectedAccount === acc.email ? 'bg-blue-50 text-blue-700 font-bold' : 'text-slate-500 hover:bg-slate-50'}`}
                  title={acc.email}
                >
                  {acc.name}
                </button>
                {acc.name.indexOf('Original') === -1 && (
                  <button 
                    onClick={(e) => { e.stopPropagation(); handleDeleteAccount(acc.email); }}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
            ))}
          </div>
        </nav>

        <div className="p-4 border-t border-slate-100 space-y-2">
          <button 
            onClick={handleSync}
            disabled={actionLoading}
            className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white py-3 rounded-xl font-semibold hover:bg-blue-700 transition disabled:opacity-50"
          >
            <RefreshCw size={18} className={actionLoading ? 'animate-spin' : ''} />
            Sync Emails
          </button>
          <button 
            onClick={handleReclassify}
            disabled={actionLoading}
            className="w-full flex items-center justify-center gap-2 bg-slate-100 text-slate-700 py-3 rounded-xl font-semibold hover:bg-slate-200 transition disabled:opacity-50"
          >
            <Zap size={18} />
            Reclassify All
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-20 bg-white border-b border-slate-200 px-10 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-bold text-slate-800 capitalize">{view}</h2>
            {selectedAccount !== 'All Accounts' && (
              <span className="bg-slate-100 text-slate-600 px-3 py-1 rounded-full text-xs font-medium border border-slate-200">
                {selectedAccount}
              </span>
            )}
          </div>
          
          {error && (
            <div className="bg-red-50 text-red-600 px-4 py-2 rounded-lg text-sm font-medium border border-red-100 flex items-center gap-2 animate-bounce">
              <AlertTriangle size={16} /> {error}
              <button onClick={() => setError(null)} className="ml-2 hover:text-red-800"><X size={14}/></button>
            </div>
          )}

          <div className="flex items-center gap-6">
            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
              <User size={20} />
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-10">
          {view === 'dashboard' ? (
            <div className="space-y-8">
              <div className="grid grid-cols-4 gap-6">
                <StatCard icon={<Mail className="text-blue-600"/>} label="Total Scanned" value={stats.total} color="blue" />
                <StatCard icon={<ShieldCheck className="text-green-600"/>} label="Safe Emails" value={stats.legitimate} color="green" />
                <StatCard icon={<ShieldAlert className="text-red-600"/>} label="Phishing Detected" value={stats.phishing} color="red" />
                <StatCard icon={<BarChart3 className="text-amber-600"/>} label="Phishing Rate" value={`${stats.phishing_percent}%`} color="amber" />
              </div>
              
              <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm">
                <div className="flex justify-between items-center mb-8">
                  <h3 className="text-lg font-bold">Recent Activity</h3>
                  <button onClick={() => setView('all')} className="text-blue-600 text-sm font-semibold hover:underline">View All</button>
                </div>
                <EmailTable emails={emails.slice(0, 10)} onOpen={openEmail} />
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
              {loading ? (
                <div className="p-20 flex flex-col items-center justify-center text-slate-400">
                  <RefreshCw size={48} className="animate-spin mb-4 text-blue-500" />
                  <p className="font-medium">Fetching emails...</p>
                </div>
              ) : (
                <EmailTable emails={emails} onOpen={openEmail} />
              )}
            </div>
          )}
        </main>
      </div>

      {/* Paste Email Modal */}
      {showPasteModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-8 w-full max-w-2xl shadow-2xl animate-in zoom-in-95 duration-200 flex flex-col max-h-[90vh]">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-bold">Paste Email for Analysis</h3>
              <button onClick={() => { setShowPasteModal(false); setPasteResult(null); setPasteData({ subject: '', body: '', sender: '' }); }} className="text-slate-400 hover:text-slate-600"><X/></button>
            </div>
            
            <div className="flex-1 overflow-y-auto pr-2">
              <form onSubmit={handlePasteAnalysis} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-400 uppercase mb-1">Sender Email</label>
                  <input required type="text" value={pasteData.sender} onChange={e => setPasteData({...pasteData, sender: e.target.value})} className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500" placeholder="e.g. support@example.com" />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-400 uppercase mb-1">Subject</label>
                  <input required type="text" value={pasteData.subject} onChange={e => setPasteData({...pasteData, subject: e.target.value})} className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500" placeholder="Email subject line" />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-400 uppercase mb-1">Email Body</label>
                  <textarea required rows={6} value={pasteData.body} onChange={e => setPasteData({...pasteData, body: e.target.value})} className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm" placeholder="Paste the full email content here..." />
                </div>
                <button type="submit" disabled={actionLoading} className="w-full bg-blue-600 text-white py-4 rounded-2xl font-bold hover:bg-blue-700 transition disabled:opacity-50">
                  {actionLoading ? 'Analyzing...' : 'Analyze Now'}
                </button>
              </form>

              {pasteResult && (
                <div className="mt-8 pt-8 border-t border-slate-100 space-y-6">
                  <div className={`p-6 rounded-3xl flex flex-col items-center text-center ${pasteResult.prediction.label === 'Phishing' ? 'bg-red-50 border border-red-100' : 'bg-green-50 border border-green-100'}`}>
                    <div className={pasteResult.prediction.label === 'Phishing' ? 'text-red-600 mb-3' : 'text-green-600 mb-3'}>
                      {pasteResult.prediction.label === 'Phishing' ? <ShieldAlert size={48} /> : <ShieldCheck size={48} />}
                    </div>
                    <h4 className="font-bold text-2xl mb-1">{pasteResult.prediction.label === 'Phishing' ? 'Threat Detected' : 'Verified Safe'}</h4>
                    <p className={`text-sm font-bold px-3 py-1 rounded-full ${pasteResult.prediction.label === 'Phishing' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
                      {pasteResult.prediction.label === 'Phishing' ? `Phishing Risk: ${pasteResult.prediction.risk_score}` : `Confidence Safe: ${(100 - parseFloat(pasteResult.prediction.risk_score)).toFixed(2)}%`}
                    </p>
                  </div>

                  <div className="space-y-4 text-sm">
                    <div className="flex items-center gap-2 text-slate-800 font-bold">
                      <Info size={18} className="text-blue-500" />
                      Analysis Summary
                    </div>
                    <p className={`p-4 rounded-xl border ${pasteResult.prediction.label === 'Phishing' ? 'bg-red-50 border-red-100 text-red-800' : 'bg-green-50 border-green-100 text-green-800'}`}>
                      {pasteResult.explanation.summary}
                    </p>
                    
                    {pasteResult.prediction.label === 'Phishing' && pasteResult.explanation.top_positive?.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {pasteResult.explanation.top_positive.map(item => (
                          <span key={item.token} className="bg-red-50 text-red-700 px-3 py-1.5 rounded-xl text-xs font-bold border border-red-100">
                            {item.token}
                          </span>
                        ))}
                      </div>
                    )}
                    
                    {pasteResult.prediction.label !== 'Phishing' && pasteResult.explanation.top_negative?.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {pasteResult.explanation.top_negative.map(item => (
                          <span key={item.token} className="bg-green-50 text-green-700 px-3 py-1.5 rounded-xl text-xs font-bold border border-green-100">
                            {item.token}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Account Modal */}
      {showAddAccount && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-8 w-full max-w-md shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-bold">Add Email Account</h3>
              <button onClick={() => setShowAddAccount(false)} className="text-slate-400 hover:text-slate-600"><X/></button>
            </div>
            <form onSubmit={handleAddAccount} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase mb-1">Display Name</label>
                <input required type="text" value={newAccount.name} onChange={e => setNewAccount({...newAccount, name: e.target.value})} className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500" placeholder="e.g. Personal Gmail" />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase mb-1">Email Address</label>
                <input required type="email" value={newAccount.email} onChange={e => setNewAccount({...newAccount, email: e.target.value})} className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500" placeholder="user@gmail.com" />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase mb-1">App Password</label>
                <input required type="password" value={newAccount.password} onChange={e => setNewAccount({...newAccount, password: e.target.value})} className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500" placeholder="16-character app password" />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase mb-1">IMAP Server</label>
                <input required type="text" value={newAccount.imap_server} onChange={e => setNewAccount({...newAccount, imap_server: e.target.value})} className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <button type="submit" className="w-full bg-blue-600 text-white py-4 rounded-2xl font-bold hover:bg-blue-700 transition mt-4">Add Account</button>
            </form>
          </div>
        </div>
      )}

      {/* Detail Slide-out */}
      {selectedEmail && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex justify-end" onClick={() => setSelectedEmail(null)}>
          <div className="w-[500px] bg-white h-full shadow-2xl flex flex-col animate-in slide-in-from-right duration-300" onClick={e => e.stopPropagation()}>
            <div className="p-8 border-b border-slate-100 flex justify-between items-center">
              <div className="flex items-center gap-4">
                <h3 className="text-xl font-bold">Email Analysis</h3>
                <button 
                  onClick={() => handleDeleteEmail(selectedEmail.id)}
                  className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                  title="Delete email"
                >
                  <Trash2 size={20} />
                </button>
              </div>
              <button onClick={() => setSelectedEmail(null)} className="p-2 hover:bg-slate-100 rounded-full transition text-slate-400"><X/></button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-8 space-y-8">
              <div className={`p-6 rounded-3xl flex flex-col items-center text-center ${selectedEmail.prediction === 'Phishing' ? 'bg-red-50 border border-red-100' : 'bg-green-50 border border-green-100'}`}>
                <div className={selectedEmail.prediction === 'Phishing' ? 'text-red-600 mb-3' : 'text-green-600 mb-3'}>
                  {selectedEmail.prediction === 'Phishing' ? <ShieldAlert size={48} /> : <ShieldCheck size={48} />}
                </div>
                <h4 className="font-bold text-2xl mb-1">{selectedEmail.prediction === 'Phishing' ? 'Threat Detected' : 'Verified Safe'}</h4>
                {selectedEmail.prediction === 'Phishing' ? (
                  <p className="text-sm font-bold px-3 py-1 rounded-full bg-red-100 text-red-700">
                    Phishing Risk: {selectedEmail.risk_score}
                  </p>
                ) : (
                  <p className="text-sm font-bold px-3 py-1 rounded-full bg-green-100 text-green-700">
                    Confidence Safe: {(100 - parseFloat(selectedEmail.risk_score)).toFixed(2)}%
                  </p>
                )}
              </div>

              <div className="space-y-4">
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Subject</span>
                  <p className="font-bold text-slate-800 text-lg leading-tight">{selectedEmail.subject || '(No Subject)'}</p>
                </div>
                <div className="flex flex-col gap-1 border-t border-slate-50 pt-4">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">From</span>
                  <p className="text-slate-600 font-medium">{selectedEmail.sender}</p>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center gap-2 text-slate-800 font-bold border-b border-slate-100 pb-2">
                  <Info size={18} className="text-blue-500" />
                  Analysis Summary
                </div>
                {explanation ? (
                  <div className="space-y-6">
                    {/* Summary box — green for safe, amber for phishing */}
                    <p className={`leading-relaxed p-5 rounded-2xl border text-sm ${
                      selectedEmail.prediction === 'Phishing'
                        ? 'bg-red-50 border-red-100 text-red-800'
                        : 'bg-green-50 border-green-100 text-green-800'
                    }`}>
                      {explanation.summary}
                    </p>

                    {/* Verdict context */}
                    <p className="text-xs text-slate-500 italic">{explanation.verdict_context}</p>

                    {/* Token badges: phishing → red Risk Factors; safe → green Safe Indicators */}
                    {selectedEmail.prediction === 'Phishing' && explanation.top_positive?.length > 0 && (
                      <div className="space-y-3">
                        <h5 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                          <Filter size={14} /> Risk Factors Detected
                        </h5>
                        <div className="flex flex-wrap gap-2">
                          {explanation.top_positive.map(item => (
                            <span key={item.token} className="bg-red-50 text-red-700 px-3 py-1.5 rounded-xl text-xs font-bold border border-red-100">
                              {item.token}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {selectedEmail.prediction !== 'Phishing' && explanation.top_negative?.length > 0 && (
                      <div className="space-y-3">
                        <h5 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                          <Filter size={14} /> Safe Indicators
                        </h5>
                        <div className="flex flex-wrap gap-2">
                          {explanation.top_negative.map(item => (
                            <span key={item.token} className="bg-green-50 text-green-700 px-3 py-1.5 rounded-xl text-xs font-bold border border-green-100">
                              {item.token}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="space-y-4 animate-pulse">
                    <div className="h-4 bg-slate-100 rounded-full w-full"></div>
                    <div className="h-4 bg-slate-100 rounded-full w-5/6"></div>
                    <div className="h-4 bg-slate-100 rounded-full w-4/6"></div>
                  </div>
                )}
              </div>

              <div className="space-y-4 border-t border-slate-50 pt-8">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Email Body</span>
                <div className="bg-slate-50 p-6 rounded-2xl text-xs text-slate-500 font-mono whitespace-pre-wrap max-h-64 overflow-y-auto border border-slate-100">
                  {selectedEmail.body}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SidebarItem({ icon, label, active, onClick, count }) {
  return (
    <button 
      onClick={onClick}
      className={`w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-200 group ${active ? 'bg-blue-50 text-blue-700 shadow-sm' : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'}`}
    >
      <div className="flex items-center gap-3 font-semibold">
        <span className={`${active ? 'text-blue-600' : 'text-slate-400 group-hover:text-slate-500'}`}>{icon}</span>
        {label}
      </div>
      {count !== undefined && (
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${active ? 'bg-blue-200 text-blue-800' : 'bg-slate-100 text-slate-500'}`}>
          {count}
        </span>
      )}
    </button>
  );
}

function StatCard({ icon, label, value, color }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600 border-blue-100',
    green: 'bg-green-50 text-green-600 border-green-100',
    red: 'bg-red-50 text-red-600 border-red-100',
    amber: 'bg-amber-50 text-amber-600 border-amber-100'
  };
  return (
    <div className={`p-6 bg-white border border-slate-200 rounded-3xl shadow-sm flex flex-col gap-3 transition-transform hover:scale-[1.02] cursor-default`}>
      <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${colors[color]} border shadow-sm`}>
        {icon}
      </div>
      <div>
        <div className="text-3xl font-black text-slate-800 tracking-tight">{value}</div>
        <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">{label}</div>
      </div>
    </div>
  );
}

function EmailTable({ emails, onOpen }) {
  if (emails.length === 0) return <div className="p-20 text-center text-slate-400 font-medium">No emails found.</div>;
  
  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <table className="w-full text-left">
      <thead>
        <tr className="bg-slate-50 border-b border-slate-100 text-slate-400 text-[10px] font-black uppercase tracking-[0.2em]">
          <th className="px-8 py-5 w-16 text-center">Status</th>
          <th className="px-4 py-5">Sender</th>
          <th className="px-4 py-5">Subject</th>
          <th className="px-4 py-5">Date</th>
          <th className="px-4 py-5 text-right pr-8">Risk Score</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-50">
        {emails.map(e => (
          <tr key={e.id} onClick={() => onOpen(e)} className="hover:bg-slate-50/50 cursor-pointer transition duration-150 group">
            <td className="px-8 py-5 text-center">
              <div className="flex justify-center">
                {e.prediction === 'Phishing' ? 
                  <ShieldAlert size={20} className="text-red-500" /> : 
                  <ShieldCheck size={20} className="text-green-500" />
                }
              </div>
            </td>
            <td className="px-4 py-5 text-sm font-semibold text-slate-600 truncate max-w-[150px]">{e.sender}</td>
            <td className="px-4 py-5">
              <div className="flex flex-col min-w-0">
                <span className="text-sm font-bold text-slate-800 truncate max-w-[300px] group-hover:text-blue-600 transition-colors">{e.subject || '(No Subject)'}</span>
                <span className="text-xs text-slate-400 truncate max-w-[300px]">{e.body?.substring(0, 60)}...</span>
              </div>
            </td>
            <td className="px-4 py-5 text-xs font-bold text-slate-400">{formatDate(e.timestamp)}</td>
            <td className="px-4 py-5 text-right pr-8">
              <span className={`text-xs font-black px-3 py-1 rounded-full ${e.prediction === 'Phishing' ? 'bg-red-50 text-red-600 border border-red-100' : 'bg-green-50 text-green-600 border border-green-100'}`}>
                {e.prediction === 'Phishing' ? `Risk: ${e.risk_score}` : `Safe: ${(100 - parseFloat(e.risk_score)).toFixed(1)}%`}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default App;
