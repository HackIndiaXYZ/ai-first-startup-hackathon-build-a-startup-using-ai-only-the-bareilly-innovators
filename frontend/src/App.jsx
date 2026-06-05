import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { 
  LayoutDashboard, Terminal, Blocks, Settings, 
  Heart, Briefcase, Bot, Code, Play, Square, 
  Mic, MicOff, Hand, BatteryCharging, Activity 
} from 'lucide-react';

const API = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

/* ── Constants & Utilities ── */
const ORB_COLORS = { idle:'#1e3a5f', listening:'#3b82f6', speaking:'#8b5cf6', thinking:'#d97706' };
const ORB_GLOW = { idle:'rgba(30,58,95,0)', listening:'rgba(59,130,246,0.6)', speaking:'rgba(139,92,246,0.6)', thinking:'rgba(217,119,6,0.5)' };

export default function App() {
  const [page, setPage] = useState('home');
  const [orbState, setOrbState] = useState('idle');
  const [statusText, setStatusText] = useState('Tap karke bolo');
  const [isConnected, setIsConnected] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [amplitude, setAmplitude] = useState(0);
  const [modules, setModules] = useState([]);
  const [history, setHistory] = useState([]);
  const [chat, setChat] = useState([]);
  const [cmdInput, setCmdInput] = useState('');
  const [textInput, setTextInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [serverOnline, setServerOnline] = useState(false);
  const [sysInfo, setSysInfo] = useState(null);
  const [settings, setSettings] = useState({ api_key:'', user_name:'Rao Alok Yadav', personality_mode:'gf', gemini_model:'native_audio', gemini_voice:'Aoede', temperature:0.9 });
  const [settingsDirty, setSettingsDirty] = useState(false);
  const [voices, setVoices] = useState([]);
  const [models, setModels] = useState([]);
  const [personalities, setPersonalities] = useState([]);
  const [inputTranscript, setInputTranscript] = useState('');
  const [outputTranscript, setOutputTranscript] = useState('');

  const wsRef = useRef(null);
  const chatEndRef = useRef(null);
  const wsReconnectRef = useRef(null);
  const iframeRef = useRef(null);

  // Broadcast amplitude and personality to particle iframe
  useEffect(() => {
    if (iframeRef.current && iframeRef.current.contentWindow) {
      iframeRef.current.contentWindow.postMessage({ type: 'amplitude', value: amplitude, personality: settings.personality_mode }, '*');
    }
  }, [amplitude, settings.personality_mode]);

  /* ── WebSocket ── */
  const connectWS = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => setServerOnline(true);

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === 'init' || msg.type === 'state') {
          const st = msg.state || msg;
          setOrbState(st.orb_state || 'idle');
          setStatusText(st.status_text || '');
          setIsConnected(!!st.is_connected);
          setIsMuted(!!st.is_muted);
          if (msg.type === 'init') {
            if (msg.modules) setModules(msg.modules);
            if (msg.chat) setChat(msg.chat);
          }
        } else if (msg.type === 'amplitude') {
          setAmplitude(msg.value || 0);
        } else if (msg.type === 'chat_message') {
          setChat(prev => {
            const exists = prev.some(m => m.text === msg.text && Math.abs(m.timestamp - msg.timestamp) < 1);
            return exists ? prev : [...prev, msg];
          });
        } else if (msg.type === 'input_transcript') {
          setInputTranscript(msg.text || '');
        } else if (msg.type === 'output_transcript') {
          setOutputTranscript(prev => prev + (msg.text || ''));
        } else if (msg.type === 'command') {
          setHistory(prev => [...prev, msg]);
        } else if (msg.type === 'settings_updated') {
          setSettings(msg.settings);
        }
      } catch {}
    };

    ws.onclose = () => {
      setServerOnline(false);
      wsReconnectRef.current = setTimeout(connectWS, 3000);
    };

    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => {
    connectWS();
    fetchStatus();
    fetchHistory();
    fetchSettings();
    fetchSystemInfo();
    const iv = setInterval(() => { fetchStatus(); fetchHistory(); fetchSystemInfo(); }, 5000);
    return () => {
      clearInterval(iv);
      clearTimeout(wsReconnectRef.current);
      wsRef.current?.close();
    };
  }, [connectWS]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    if (chat.length > 0) setOutputTranscript('');
  }, [chat]);

  /* ── API calls ── */
  const fetchStatus = async () => {
    try {
      const r = await axios.get(`${API}/status`);
      setModules(r.data.modules || []);
      setServerOnline(true);
    } catch { setServerOnline(false); }
  };

  const fetchSystemInfo = async () => {
    try {
      const r = await axios.get(`${API}/system-info`);
      setSysInfo(r.data);
    } catch {}
  };

  const fetchHistory = async () => {
    try { const r = await axios.get(`${API}/history`); setHistory(r.data.history || []); } catch {}
  };

  const fetchSettings = async () => {
    try {
      const r = await axios.get(`${API}/settings`);
      setSettings(s => ({ ...s, ...r.data.settings }));
      setVoices(r.data.voices || []);
      setModels(r.data.models || []);
      setPersonalities(r.data.personalities || []);
    } catch {}
  };

  const startVoice = async () => {
    setLoading(true);
    try { await axios.post(`${API}/voice/start`); } catch (e) { alert('Failed: ' + e.message); }
    setLoading(false);
  };

  const stopVoice = async () => {
    try { await axios.post(`${API}/voice/stop`); } catch {}
  };

  const sendText = async () => {
    if (!textInput.trim()) return;
    const txt = textInput; setTextInput('');
    try { await axios.post(`${API}/voice/send-text`, { text: txt }); } catch (e) { alert('Not connected: ' + e.message); }
  };

  const sendCmd = async () => {
    if (!cmdInput.trim()) return;
    setLoading(true);
    try {
      const r = await axios.post(`${API}/command`, { command: cmdInput });
      setHistory(prev => [...prev, { command: cmdInput, response: r.data.response, timestamp: new Date().toISOString() }]);
      setCmdInput('');
    } catch { alert('Server offline.'); }
    setLoading(false);
  };

  const toggleMute = async () => {
    try { await axios.post(`${API}/voice/mute`); } catch {}
  };

  const interrupt = async () => {
    try { await axios.post(`${API}/voice/interrupt`); } catch {}
  };

  const saveSettings = async () => {
    try {
      await axios.post(`${API}/settings`, settings);
      setSettingsDirty(false);
      alert('Settings saved! Restart voice session to apply changes.');
    } catch (e) { alert('Save failed: ' + e.message); }
  };

  /* ── Orb ── */
  const Orb = () => {
    return (
      <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:'15px', padding:'10px 0' }}>
        <div style={{ fontSize:'16px', fontWeight: 500, color:'#94a3b8', textAlign:'center', letterSpacing: '1px' }}>{statusText}</div>
        {inputTranscript && <div style={{ fontSize:'13px', color:'#60a5fa', fontStyle:'italic', textAlign:'center', maxWidth:'300px', background: 'rgba(59,130,246,0.1)', padding: '8px 16px', borderRadius: '20px' }}>You: "{inputTranscript}"</div>}
        {outputTranscript && <div style={{ fontSize:'13px', color:'#a78bfa', textAlign:'center', maxWidth:'300px', background: 'rgba(139,92,246,0.1)', padding: '8px 16px', borderRadius: '20px' }}>Sivi: "{outputTranscript}"</div>}
      </div>
    );
  };

  /* ── Pages ── */
  const renderHome = () => (
    <>
      <div className="glass-panel" style={{ position: 'relative', overflow: 'hidden', flex:1, padding:'0', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <iframe ref={iframeRef} src="/particles.html" style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 'none', zIndex: 0, opacity: 0.85, pointerEvents: 'none' }} />
        <div style={{ position: 'relative', zIndex: 1, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div style={{ flex: 1, display: 'flex', alignItems: 'flex-end', justifyContent: 'center', paddingBottom: '10px' }}>
            <Orb />
          </div>
          <div>
            <div style={{ padding:'0 24px 24px', display:'flex', gap:'12px', justifyContent:'center', flexWrap:'wrap' }}>
            {!isConnected
              ? <button className="btn-primary" onClick={startVoice} disabled={loading} style={{display:'flex', alignItems:'center', gap:'8px'}}>
                  {loading ? 'Connecting...' : <><Play size={16} /> Start Sivi</>}
                </button>
              : <>
                  <button className="btn-danger" onClick={stopVoice} style={{display:'flex', alignItems:'center', gap:'8px'}}><Square size={16} /> Stop</button>
                  <button className="btn-secondary" onClick={toggleMute} style={{display:'flex', alignItems:'center', gap:'8px'}}>{isMuted ? <><Mic size={16} /> Unmute</> : <><MicOff size={16} /> Mute</>}</button>
                  <button className="btn-secondary" onClick={interrupt} style={{display:'flex', alignItems:'center', gap:'8px'}}><Hand size={16} /> Interrupt</button>
                </>
            }
          </div>
            <div style={{ padding:'0 24px 24px', display:'flex', gap:'12px' }}>
              <input className="input-field" style={{flex: 1}} value={textInput} onChange={e => setTextInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && sendText()} placeholder="Type message to Sivi..." />
              <button className="btn-primary" onClick={sendText} disabled={!isConnected}>Send</button>
            </div>
          </div>
        </div>
      </div>
      <div className="glass-panel" style={{ flex:'0 0 380px', padding:'24px', overflowY:'auto', display:'flex', flexDirection:'column' }}>
        <div style={{ fontWeight:700, fontSize: '18px', marginBottom:'16px', color:'#e2e8f0' }}>Live Chat</div>
        {chat.length === 0 && <div style={{ color:'#475569', textAlign:'center', padding:'40px', fontSize: '15px' }}>Start voice session and say something!</div>}
        {chat.map((m, i) => (
          <div key={i} style={{ display:'flex', justifyContent: m.is_user ? 'flex-end' : 'flex-start', marginBottom:'12px' }}>
            <div className={m.is_user ? "chat-bubble-user" : "chat-bubble-ai"} style={{ maxWidth:'75%', padding:'12px 18px', fontSize:'14px', lineHeight:'1.6' }}>
              {m.text}
            </div>
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>
    </>
  );

  const renderCommands = () => (
    <div className="glass-panel" style={{ flex:1, padding:'24px', display:'flex', flexDirection:'column' }}>
      <div style={{ fontWeight:700, fontSize:'18px', marginBottom:'16px' }}>Command Terminal</div>
      <div style={{ flex:1, overflowY:'auto', marginBottom:'16px' }}>
        {history.length === 0 && <div style={{ color:'#475569', textAlign:'center', padding:'60px' }}>No commands yet.</div>}
        {[...history].reverse().map((h, i) => (
          <div key={i} className="module-card">
            <div style={{ display:'flex', justifyContent:'space-between', marginBottom:'8px' }}>
              <span style={{ fontFamily:'monospace', color:'#22d3ee', fontSize: '14px' }}>➤ {h.command}</span>
              <span style={{ fontSize:'12px', color:'#64748b' }}>{new Date(h.timestamp).toLocaleTimeString()}</span>
            </div>
            <div style={{ color:'#cbd5e1', fontSize:'14px', fontFamily: 'monospace', background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '8px' }}>↪ {h.response}</div>
          </div>
        ))}
      </div>
      <div style={{ display:'flex', gap:'12px' }}>
        <input className="input-field" style={{flex: 1}} value={cmdInput} onChange={e => setCmdInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && sendCmd()} placeholder="Type a command (e.g. open notepad)..." />
        <button className="btn-primary" onClick={sendCmd} disabled={loading}>Run</button>
      </div>
    </div>
  );

  const renderModules = () => (
    <div className="glass-panel" style={{ flex:1, padding:'24px', overflowY:'auto' }}>
      <div style={{ fontWeight:700, fontSize:'18px', marginBottom:'16px' }}>Modules ({modules.length})</div>
      {modules.map((m, i) => {
        const col = m.status === 'active' ? '#4ade80' : m.status === 'no-key' ? '#facc15' : '#64748b';
        return (
          <div key={i} className="module-card" style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
            <div>
              <div style={{ fontWeight:600, fontSize:'15px', color: '#f8fafc', marginBottom: '4px' }}>{m.name}</div>
              <div style={{ color:'#64748b', fontSize:'12px', fontFamily:'monospace' }}>{m.file}</div>
            </div>
            <div style={{ display:'flex', alignItems:'center', gap:'8px', background: 'rgba(0,0,0,0.2)', padding: '6px 12px', borderRadius: '20px' }}>
              <div style={{ width:'10px', height:'10px', borderRadius:'50%', background:col, boxShadow: m.status==='active' ? `0 0 10px ${col}` : 'none' }} />
              <span style={{ fontSize:'12px', color:col, textTransform:'uppercase', fontWeight:700 }}>{m.status}</span>
            </div>
          </div>
        );
      })}
    </div>
  );

  const renderSettings = () => (
    <div className="glass-panel" style={{ flex:1, padding:'32px', overflowY:'auto' }}>
      <div style={{ fontWeight:700, fontSize:'20px', marginBottom:'24px' }}>Settings</div>

      {[
        { key:'api_key', label:'Gemini API Key', type:'password', hint:'AIza...' },
        { key:'user_name', label:'Your Name', type:'text', hint:'Rao Alok Yadav' },
      ].map(f => (
        <div key={f.key} style={{ marginBottom:'20px' }}>
          <label style={{ fontSize:'13px', color:'#94a3b8', display:'block', marginBottom:'8px', fontWeight: 500 }}>{f.label}</label>
          <input className="input-field" type={f.type} value={settings[f.key] || ''} placeholder={f.hint}
            onChange={e => { setSettings(p => ({ ...p, [f.key]: e.target.value })); setSettingsDirty(true); }}
            style={{ width:'100%', boxSizing:'border-box' }} />
        </div>
      ))}

      <div style={{ marginBottom:'20px' }}>
        <label style={{ fontSize:'13px', color:'#94a3b8', display:'block', marginBottom:'8px', fontWeight: 500 }}>Personality Mode</label>
        <select className="input-field" value={settings.personality_mode} onChange={e => { setSettings(p => ({ ...p, personality_mode: e.target.value })); setSettingsDirty(true); }}
          style={{ width:'100%', boxSizing:'border-box' }}>
          {personalities.map(p => <option key={p.id} value={p.id}>{p.label} — {p.language}</option>)}
        </select>
      </div>

      <div style={{ marginBottom:'20px' }}>
        <label style={{ fontSize:'13px', color:'#94a3b8', display:'block', marginBottom:'8px', fontWeight: 500 }}>AI Model</label>
        <select className="input-field" value={settings.gemini_model} onChange={e => { setSettings(p => ({ ...p, gemini_model: e.target.value })); setSettingsDirty(true); }}
          style={{ width:'100%', boxSizing:'border-box' }}>
          {models.map(m => <option key={m.id} value={m.id}>{m.label}</option>)}
        </select>
      </div>

      <div style={{ marginBottom:'20px' }}>
        <label style={{ fontSize:'13px', color:'#94a3b8', display:'block', marginBottom:'8px', fontWeight: 500 }}>Voice</label>
        <select className="input-field" value={settings.gemini_voice} onChange={e => { setSettings(p => ({ ...p, gemini_voice: e.target.value })); setSettingsDirty(true); }}
          style={{ width:'100%', boxSizing:'border-box' }}>
          {voices.map(v => <option key={v.id} value={v.id}>{v.label}</option>)}
        </select>
      </div>

      <div style={{ marginBottom:'32px' }}>
        <label style={{ fontSize:'13px', color:'#94a3b8', display:'block', marginBottom:'8px', fontWeight: 500 }}>Temperature: <span style={{color:'#60a5fa'}}>{settings.temperature}</span></label>
        <input type="range" min="0" max="1" step="0.1" value={settings.temperature}
          onChange={e => { setSettings(p => ({ ...p, temperature: parseFloat(e.target.value) })); setSettingsDirty(true); }}
          style={{ width:'100%', cursor:'pointer' }} />
      </div>

      <button className="btn-primary" onClick={saveSettings} disabled={!settingsDirty}>
        Save Configuration
      </button>
      <div style={{ fontSize:'12px', color:'#64748b', marginTop:'16px' }}>Settings are persistently saved to sivi_settings.json</div>
    </div>
  );

  const navItems = [
    { id:'home', label:'Dashboard', icon: <LayoutDashboard size={18} /> },
    { id:'commands', label:'Commands', icon: <Terminal size={18} /> },
    { id:'modules', label:'Modules', icon: <Blocks size={18} /> },
    { id:'settings', label:'Settings', icon: <Settings size={18} /> },
  ];

  const activeCount = modules.filter(m => m.status === 'active').length;

  const getThemeVars = (mode) => {
    switch (mode) {
      case 'gf':
        return {
          '--theme-primary-start': '#ec4899',
          '--theme-primary-end': '#f43f5e',
          '--theme-primary-rgb': '236, 72, 153',
          '--theme-secondary-rgb': '244, 63, 94',
          '--theme-bg-1': 'rgba(236, 72, 153, 0.15)',
          '--theme-bg-2': 'rgba(244, 63, 94, 0.15)',
        };
      case 'developer':
        return {
          '--theme-primary-start': '#f97316',
          '--theme-primary-end': '#ef4444',
          '--theme-primary-rgb': '249, 115, 22',
          '--theme-secondary-rgb': '239, 68, 68',
          '--theme-bg-1': 'rgba(249, 115, 22, 0.15)',
          '--theme-bg-2': 'rgba(239, 68, 68, 0.15)',
        };
      case 'assistant':
        return {
          '--theme-primary-start': '#14b8a6',
          '--theme-primary-end': '#10b981',
          '--theme-primary-rgb': '20, 184, 166',
          '--theme-secondary-rgb': '16, 185, 129',
          '--theme-bg-1': 'rgba(20, 184, 166, 0.15)',
          '--theme-bg-2': 'rgba(16, 185, 129, 0.15)',
        };
      case 'professional':
      default:
        return {
          '--theme-primary-start': '#3b82f6',
          '--theme-primary-end': '#06b6d4',
          '--theme-primary-rgb': '59, 130, 246',
          '--theme-secondary-rgb': '139, 92, 246',
          '--theme-bg-1': 'rgba(59, 130, 246, 0.15)',
          '--theme-bg-2': 'rgba(139, 92, 246, 0.15)',
        };
    }
  };

  const modeEmojis = { 
    gf: <Heart size={22} fill="currentColor" />, 
    professional: <Briefcase size={22} />, 
    assistant: <Bot size={22} />, 
    developer: <Code size={22} /> 
  };
  const currentEmoji = modeEmojis[settings.personality_mode] || <Activity size={22} />;

  return (
    <div className="app-wrapper" style={{ display:'flex', padding:'24px', gap:'24px', height:'100vh', width:'100vw', ...getThemeVars(settings.personality_mode) }}>
      
      {/* Sidebar */}
      <aside className="glass-panel" style={{ width:'260px', display:'flex', flexDirection:'column', padding: '24px', flexShrink:0 }}>
        <div style={{ display:'flex', alignItems:'center', gap:'12px', marginBottom: '32px' }}>
          <div style={{ width:'42px', height:'42px', borderRadius:'12px', background:'linear-gradient(135deg, var(--theme-primary-start), var(--theme-primary-end))', display:'flex', alignItems:'center', justifyContent:'center', boxShadow:'0 8px 20px rgba(var(--theme-primary-rgb),0.4)', fontSize:'20px', color: '#fff' }}>{currentEmoji}</div>
          <h1 style={{ fontSize:'24px', fontWeight:800, letterSpacing:'4px', background:'linear-gradient(135deg, var(--theme-primary-start), var(--theme-primary-end))', WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent' }}>Sivi</h1>
        </div>

        <nav style={{ display:'flex', flexDirection:'column', gap:'6px' }}>
          {navItems.map(n => (
            <button key={n.id} onClick={() => setPage(n.id)} className={`nav-btn ${page === n.id ? 'active' : ''}`}>
              <span style={{display:'flex', alignItems:'center', justifyContent:'center'}}>{n.icon}</span><span>{n.label}</span>
            </button>
          ))}
        </nav>

        <div style={{ display:'flex', flexDirection:'column', gap:'10px', marginTop:'auto' }}>
          <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '12px', padding:'12px 16px', display:'flex', alignItems:'center', gap:'10px' }}>
            <div style={{ width:'10px', height:'10px', borderRadius:'50%', background: serverOnline ? '#4ade80' : '#ef4444', boxShadow: serverOnline ? '0 0 10px #4ade80' : '0 0 10px #ef4444' }} />
            <span style={{ fontSize:'13px', fontWeight: 500, color:'#cbd5e1' }}>{serverOnline ? 'Server Online' : 'Server Offline'}</span>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '12px', padding:'12px 16px', display:'flex', alignItems:'center', gap:'10px' }}>
            <div style={{ width:'10px', height:'10px', borderRadius:'50%', background: isConnected ? '#a78bfa' : '#64748b', boxShadow: isConnected ? '0 0 10px #a78bfa' : 'none' }} />
            <span style={{ fontSize:'13px', fontWeight: 500, color:'#cbd5e1' }}>{isConnected ? 'Sivi Active' : 'Sivi Offline'}</span>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '12px', padding:'16px' }}>
            <div style={{ fontSize:'12px', color:'#94a3b8', marginBottom: '4px' }}>Active System Modules</div>
            <div style={{ fontSize:'20px', fontWeight:800, color:'#60a5fa' }}>{activeCount} <span style={{fontSize:'14px', color:'#475569', fontWeight: 600}}>/ {modules.length}</span></div>
          </div>
          {sysInfo && (
            <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '12px', padding:'16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ fontSize:'12px', color:'#94a3b8', marginBottom: '4px', fontWeight: 600 }}>System Health</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: '#cbd5e1' }}>CPU</span>
                <span style={{ color: sysInfo.cpu_percent > 80 ? '#ef4444' : '#4ade80', fontWeight: 'bold' }}>{sysInfo.cpu_percent}%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: '#cbd5e1' }}>RAM</span>
                <span style={{ color: sysInfo.ram_percent > 85 ? '#ef4444' : '#60a5fa', fontWeight: 'bold' }}>{sysInfo.ram_used_gb}GB ({sysInfo.ram_percent}%)</span>
              </div>
              {sysInfo.battery_percent >= 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                  <span style={{ color: '#cbd5e1' }}>Battery</span>
                  <span style={{ color: sysInfo.battery_percent < 20 && !sysInfo.battery_plugged ? '#ef4444' : '#a78bfa', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    {sysInfo.battery_percent}% {sysInfo.battery_plugged && <BatteryCharging size={14} />}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      </aside>

      {/* Main */}
      <main style={{ flex:1, display:'flex', flexDirection:'column', gap:'24px', minHeight:0 }}>
        <div className="glass-panel" style={{ padding:'18px 24px', display:'flex', justifyContent:'space-between', alignItems:'center' }}>
          <h2 style={{ fontSize:'18px', fontWeight:700, letterSpacing:'0.5px' }}>
            {{ home:'Sivi Voice Dashboard', commands:'Command Terminal', modules:'Module Status', settings:'System Settings' }[page]}
          </h2>
          <div style={{ fontSize:'13px', color:'#64748b', fontFamily:'monospace', background: 'rgba(0,0,0,0.2)', padding: '6px 12px', borderRadius: '20px' }}>localhost:8000 • ws:8000/ws</div>
        </div>
        <div style={{ display: 'flex', gap: '24px', flex: 1, height: '100%', overflow: 'hidden' }}>
          {{ home: renderHome, commands: renderCommands, modules: renderModules, settings: renderSettings }[page]?.()}
        </div>
      </main>
    </div>
  );
}
