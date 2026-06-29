import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { 
  LayoutDashboard, Terminal, Blocks, Settings, 
  Heart, Briefcase, Bot, Code, Play, Square, 
  Mic, MicOff, Hand, BatteryCharging, Activity,
  CloudRain, Newspaper, Battery, Calendar, Monitor, Clock, ShieldCheck, Zap, Sun, Cpu, Wifi
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
  const [agentList, setAgentList] = useState([]);
  const [history, setHistory] = useState([]);
  const [chat, setChat] = useState([]);
  const [cmdInput, setCmdInput] = useState('');
  const [textInput, setTextInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [serverOnline, setServerOnline] = useState(false);
  const [sysInfo, setSysInfo] = useState(null);
  const [dashboardData, setDashboardData] = useState(null);
  const [settings, setSettings] = useState({ api_key:'', user_name:'Rao Alok Yadav', personality_mode:'sivi', gemini_model:'native_audio', gemini_voice:'Aoede', temperature:0.9 });
  const [settingsDirty, setSettingsDirty] = useState(false);
  const [voices, setVoices] = useState([]);
  const [models, setModels] = useState([]);
  const [personalities, setPersonalities] = useState([]);
  const [inputTranscript, setInputTranscript] = useState('');
  const [outputTranscript, setOutputTranscript] = useState('');
  const [currentTime, setCurrentTime] = useState(new Date());
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3500);
  };
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

  // Track global mouse position for Acertinity cursor highlight
  useEffect(() => {
    const handleMouseMove = (e) => {
      document.documentElement.style.setProperty('--mouse-x', `${e.clientX}px`);
      document.documentElement.style.setProperty('--mouse-y', `${e.clientY}px`);
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

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
    fetchAgents();
    fetchHistory();
    fetchSettings();
    fetchSystemInfo();
    fetchDashboardData();
    const iv = setInterval(() => { fetchStatus(); fetchAgents(); fetchHistory(); fetchSystemInfo(); fetchDashboardData(); }, 5000);
    const timeIv = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => {
      clearInterval(iv);
      clearInterval(timeIv);
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
    } catch (e) { 
      setServerOnline(false); 
      console.error("fetchStatus error:", e);
    }
  };

  const fetchAgents = async () => {
    try {
      const r = await axios.get(`${API}/agents`);
      setAgentList(r.data.agents || []);
    } catch (e) { console.error("fetchAgents error:", e); }
  };

  const fetchSystemInfo = async () => {
    try {
      const r = await axios.get(`${API}/system-info`);
      setSysInfo(r.data);
    } catch (e) { console.error("fetchSystemInfo error:", e); }
  };

  const fetchDashboardData = async () => {
    try {
      const r = await axios.get(`${API}/dashboard-data`);
      setDashboardData(r.data);
    } catch (e) { console.error("fetchDashboardData error:", e); }
  };

  const fetchHistory = async () => {
    try { 
      const r = await axios.get(`${API}/history`); 
      setHistory(r.data.history || []); 
    } catch (e) { console.error("fetchHistory error:", e); }
  };

  const fetchSettings = async () => {
    try {
      const r = await axios.get(`${API}/settings`);
      setSettings(s => ({ ...s, ...r.data.settings }));
      setVoices(r.data.voices || []);
      setModels(r.data.models || []);
      setPersonalities(r.data.personalities || []);
    } catch (e) { console.error("fetchSettings error:", e); }
  };

  const startVoice = async () => {
    setLoading(true);
    try { 
      await axios.post(`${API}/voice/start`); 
      showToast('Voice session started', 'success');
    } catch (e) { 
      showToast('Failed to start voice: ' + e.message); 
      console.error(e);
    }
    setLoading(false);
  };

  const stopVoice = async () => {
    try { 
      await axios.post(`${API}/voice/stop`); 
      showToast('Voice session stopped', 'success');
    } catch (e) { 
      showToast('Failed to stop voice', 'error'); 
      console.error(e);
    }
  };

  const sendText = async () => {
    if (!textInput.trim()) return;
    const txt = textInput; setTextInput('');
    try { 
      await axios.post(`${API}/voice/send-text`, { text: txt }); 
    } catch (e) { 
      showToast('Message failed: ' + e.message, 'error'); 
      console.error(e);
    }
  };

  const sendCmd = async () => {
    if (!cmdInput.trim()) return;
    setLoading(true);
    try {
      const r = await axios.post(`${API}/command`, { command: cmdInput });
      setHistory(prev => [...prev, { command: cmdInput, response: r.data.response, timestamp: new Date().toISOString() }]);
      setCmdInput('');
    } catch (e) { 
      showToast('Command failed to execute. Server might be offline.', 'error'); 
      console.error(e);
    }
    setLoading(false);
  };

  const toggleMute = async () => {
    try { 
      await axios.post(`${API}/voice/mute`); 
    } catch (e) { 
      showToast('Failed to toggle mute', 'error'); 
      console.error(e);
    }
  };

  const interrupt = async () => {
    try { 
      await axios.post(`${API}/voice/interrupt`); 
    } catch (e) { 
      showToast('Failed to interrupt Sivi', 'error'); 
      console.error(e);
    }
  };

  const saveSettings = async () => {
    try {
      await axios.post(`${API}/settings`, settings);
      setSettingsDirty(false);
      showToast('Settings saved successfully!', 'success');
    } catch (e) { 
      showToast('Failed to save settings: ' + e.message, 'error'); 
      console.error(e);
    }
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
  const renderHome = () => {
    // Current time formatting (Indian Standard Time)
    const now = currentTime;
    
    // Get hour in IST (0-23) robustly
    const istTime = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Kolkata" }));
    const hour = istTime.getHours();

    let greeting = 'GOOD MORNING';
    if (hour >= 12 && hour < 17) greeting = 'GOOD AFTERNOON';
    else if (hour >= 17 && hour < 21) greeting = 'GOOD EVENING';
    else if (hour >= 21 || hour < 4) greeting = 'GOOD NIGHT';
    
    const timeString = now.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: true }).toUpperCase();
    const dateString = now.toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', day: 'numeric', month: 'long', year: 'numeric' });
    const dayString = now.toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', weekday: 'long' });

    // Battery & CPU from sysInfo
    const battery = sysInfo?.battery_percent >= 0 ? sysInfo.battery_percent : 100;
    const isCharging = sysInfo?.battery_plugged || false;

    return (
      <div style={{ position: 'relative', flex:1, display: 'flex', flexDirection: 'column', overflowY: 'auto', overflowX: 'hidden' }}>
        <iframe ref={iframeRef} src="/particles.html" style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 'none', zIndex: 0, opacity: 0.6, pointerEvents: 'none' }} />
        
        {/* Top Header */}
        <div style={{ position: 'relative', zIndex: 1, textAlign: 'center', paddingTop: '5px' }}>
          <h1 className="responsive-header">SMART BRIEFINGS</h1>
          <p className="responsive-subheader">Ab on hote hi, Sivi batayegi sab kuch.</p>
        </div>

        {/* Acertinity UI Background with Cursor Highlight */}
        <div className="acertinity-bg">
          <div className="acertinity-grid"></div>
          <div className="acertinity-grid-highlight"></div>
        </div>

        {/* Dashboard Grid */}
        <div className="dashboard-grid" style={{ position: 'relative', zIndex: 1, flex: 1 }}>
          
          {/* Left Column (Weather & System) */}
          <div className="dashboard-column" style={{ justifyContent: 'center' }}>
            {/* Weather Card */}
            <div className="glass-panel hover-glow" style={{ padding: '25px', minHeight: '130px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <div style={{ fontSize: '12px', color: '#94a3b8', letterSpacing: '1px', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CloudRain size={16}/> WEATHER & LOCATION
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                <Sun size={32} color="#fbbf24" />
                <div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#fff', lineHeight: 1 }}>
                    {dashboardData?.weather?.split(':')[0]?.split(',')[0]?.trim() || "Delhi"}
                  </div>
                  <div style={{ color: '#cbd5e1', fontSize: '13px', marginTop: '4px' }}>
                    {dashboardData?.weather?.split(':')[1]?.trim() || "Loading..."}
                  </div>
                </div>
              </div>
            </div>

            {/* System Info */}
            <div className="glass-panel hover-glow" style={{ padding: '15px', display: 'flex', gap: '10px' }}>
               <div style={{ flex: 1, background: 'rgba(15,23,42,0.4)', borderRadius: '10px', padding: '10px', textAlign: 'center' }}>
                  <BatteryCharging size={18} color={dashboardData?.system?.is_charging ? "#34d399" : "#fbbf24"} style={{ margin: '0 auto 5px' }} />
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#e2e8f0' }}>{dashboardData?.system?.battery || 0}%</div>
               </div>
               <div style={{ flex: 1, background: 'rgba(15,23,42,0.4)', borderRadius: '10px', padding: '10px', textAlign: 'center' }}>
                  <Cpu size={18} color="#f472b6" style={{ margin: '0 auto 5px' }} />
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#e2e8f0' }}>{dashboardData?.system?.cpu || 0}%</div>
               </div>
               <div style={{ flex: 1, background: 'rgba(15,23,42,0.4)', borderRadius: '10px', padding: '10px', textAlign: 'center' }}>
                  <Wifi size={18} color="#60a5fa" style={{ margin: '0 auto 5px' }} />
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#e2e8f0' }}>{dashboardData?.system?.speed_down || 0}M</div>
               </div>
            </div>

            {/* Time Card */}
            <div className="glass-panel hover-glow" style={{ padding: '15px' }}>
               <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                <Clock size={32} color="#c084fc" />
                <div>
                  <div style={{ fontSize: '10px', color: '#94a3b8', letterSpacing: '1px' }}>TIME & DAY</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#fff', lineHeight: 1.1 }}>{timeString}</div>
                  <div style={{ color: '#cbd5e1', fontSize: '11px' }}>{dayString}, {dateString}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Center Column (Sivi Chat) */}
          <div className="dashboard-center">
            
            {/* Live Chat Bubbles below Sivi */}
            <div style={{ width: '100%', maxWidth: '400px', marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {inputTranscript && <div key={inputTranscript} className="chat-bubble-user chat-bubble-anim">You: "{inputTranscript}"</div>}
              {outputTranscript && <div key={outputTranscript} className="chat-bubble-ai chat-bubble-anim">Sivi: "{outputTranscript}"</div>}
            </div>
            
            {/* Realtime Controls & Text Input */}
            <div style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '10px', width: '100%', maxWidth: '400px' }}>
              {isConnected && (
                <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                  <button className="btn-secondary" onClick={toggleMute} style={{flex: 1, display:'flex', justifyContent:'center', alignItems:'center', gap:'8px'}}>
                    {isMuted ? <><Mic size={14} /> Unmute</> : <><MicOff size={14} /> Mute</>}
                  </button>
                  <button className="btn-secondary" onClick={interrupt} style={{flex: 1, display:'flex', justifyContent:'center', alignItems:'center', gap:'8px'}}>
                    <Hand size={14} /> Interrupt
                  </button>
                </div>
              )}
              <div style={{ display: 'flex', gap: '10px' }}>
                <input className="input-field" style={{flex: 1}} value={textInput} onChange={e => setTextInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && sendText()} placeholder="Type message to Sivi..." />
                <button className="btn-primary" onClick={sendText} disabled={!isConnected}>Send</button>
              </div>
            </div>
          </div>

          {/* Right Column (News & Schedule) */}
          <div className="dashboard-column" style={{ justifyContent: 'center' }}>
            
            {/* Schedule Card */}
            <div className="glass-panel hover-glow" style={{ padding: '15px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <Calendar size={16} color="#a78bfa" />
                <div>
                  <div style={{ fontSize: '11px', color: '#94a3b8', letterSpacing: '1px' }}>TODAY'S SCHEDULE</div>
                  <div style={{ color: '#fff', fontSize: '13px', fontWeight: 'bold' }}>{dateString.toUpperCase()}</div>
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '10px', maxHeight: '100px', overflowY: 'auto' }}>
                {Array.isArray(dashboardData?.calendar) && dashboardData.calendar.length > 0 ? (
                  <div style={{ fontSize: '12px', color: '#cbd5e1', whiteSpace: 'pre-wrap' }}>
                    {dashboardData.calendar.map(ev => `${ev.title} (${ev.time}${ev.location ? ' at ' + ev.location : ''})`).join('\n')}
                  </div>
                ) : (
                  <div style={{ fontSize: '12px', color: '#64748b', fontStyle: 'italic' }}>No events scheduled for today.</div>
                )}
              </div>
            </div>

            {/* News Card */}
            <div className="glass-panel hover-glow" style={{ padding: '15px', flex: 1, display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <div style={{ fontSize: '11px', color: '#94a3b8', letterSpacing: '1px', display: 'flex', alignItems: 'center', gap:'8px' }}>
                  <Newspaper size={14}/> IMPORTANT NEWS
                </div>
                <div style={{ background: 'linear-gradient(135deg, var(--theme-primary-start), var(--theme-primary-end))', padding: '2px 6px', borderRadius: '10px', fontSize: '9px', fontWeight: 'bold' }}>LIVE</div>
              </div>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto', maxHeight: '150px', paddingRight: '5px' }}>
                {Array.isArray(dashboardData?.news) && dashboardData.news.length > 0 ? (
                  dashboardData.news.map((headline, idx) => (
                    <div key={idx} style={{ background: 'rgba(15,23,42,0.4)', padding: '10px', borderRadius: '8px', fontSize: '12px', color: '#cbd5e1', borderLeft: `2px solid ${idx % 2 === 0 ? '#f87171' : '#60a5fa'}` }}>
                      {headline}
                    </div>
                  ))
                ) : (
                  <div style={{ fontSize: '12px', color: '#64748b', fontStyle: 'italic' }}>Fetching latest headlines...</div>
                )}
              </div>
            </div>
            
          </div>
        </div>

        {/* Bottom Bar Features */}
        <div className="bottom-bar-responsive" style={{ position: 'relative', zIndex: 1 }}>
          <div className="glass-panel" style={{ display: 'flex', alignItems: 'center', gap: '20px', padding: '10px 20px', borderRadius: '20px', background: 'rgba(20, 15, 40, 0.6)', border: '1px solid rgba(255,255,255,0.15)' }}>
            <div style={{ display: 'flex', gap: '20px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                <Mic size={16} color="#a78bfa" />
                <span style={{ fontSize: '10px', color: '#cbd5e1' }}>Voice Activated</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                <ShieldCheck size={16} color="#a78bfa" />
                <span style={{ fontSize: '10px', color: '#cbd5e1' }}>Secure</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                <Heart size={16} color="#a78bfa" />
                <span style={{ fontSize: '10px', color: '#cbd5e1' }}>For You</span>
              </div>
            </div>
          </div>
          
          {/* Main Action Button */}
          <div 
            onClick={isConnected ? stopVoice : startVoice}
            style={{ 
              display: 'flex', alignItems: 'center', gap: '12px', padding: '10px 20px', 
              borderRadius: '20px', cursor: 'pointer',
              background: isConnected ? 'rgba(239,68,68,0.2)' : 'rgba(167, 139, 250, 0.2)', 
              border: `1px solid ${isConnected ? '#ef4444' : '#a78bfa'}`,
              boxShadow: `0 0 15px ${isConnected ? 'rgba(239,68,68,0.3)' : 'rgba(167, 139, 250, 0.3)'}`,
              transition: 'all 0.3s ease'
            }}
          >
            <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: isConnected ? '#ef4444' : 'linear-gradient(135deg, var(--theme-primary-start), var(--theme-primary-end))', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {isConnected ? <Square size={14} color="#fff" /> : <Mic size={16} color="#fff" />}
            </div>
            <div>
              <div style={{ color: isConnected ? '#fca5a5' : '#e2e8f0', fontSize: '14px', fontWeight: 700 }}>
                {isConnected ? '"STOP SESSION"' : `"${greeting}, SIVI"`}
              </div>
              <div style={{ color: '#94a3b8', fontSize: '11px' }}>
                {isConnected ? 'Tap to disconnect.' : 'Tap to Start'}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const renderCommands = () => (
    <div className="glass-panel" style={{ flex:1, padding:'24px', display:'flex', flexDirection:'column' }}>
      <div style={{ fontWeight:700, fontSize:'18px', marginBottom:'16px' }}>Command Terminal</div>
      <div style={{ flex:1, overflowY:'auto', marginBottom:'16px' }}>
        {history.length === 0 && <div style={{ color:'#475569', textAlign:'center', padding:'60px' }}>No commands yet.</div>}
        {[...history].reverse().map((h, i) => (
          <div key={i} className="module-card">
            <div style={{ display:'flex', justifyContent:'space-between', marginBottom:'8px', flexWrap: 'wrap', gap: '8px' }}>
              <span style={{ fontFamily:'monospace', color:'#22d3ee', fontSize: '14px', wordBreak: 'break-word' }}>➤ {h.command}</span>
              <span style={{ fontSize:'12px', color:'#64748b', flexShrink: 0 }}>{new Date(h.timestamp).toLocaleTimeString()}</span>
            </div>
            <div style={{ color:'#cbd5e1', fontSize:'14px', fontFamily: 'monospace', background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '8px', wordBreak: 'break-word' }}>↪ {h.response}</div>
          </div>
        ))}
      </div>
      <div style={{ display:'flex', gap:'12px', flexWrap: 'wrap' }}>
        <input className="input-field" style={{flex: '1 1 200px'}} value={cmdInput} onChange={e => setCmdInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && sendCmd()} placeholder="Type a command (e.g. open notepad)..." />
        <button className="btn-primary" style={{flex: '0 0 auto'}} onClick={sendCmd} disabled={loading}>Run</button>
      </div>
    </div>
  );

  const renderModules = () => (
    <div className="glass-panel" style={{ flex:1, padding:'32px', overflowY:'auto' }}>
      <div style={{ fontWeight:700, fontSize:'22px', marginBottom:'8px', display:'flex', alignItems:'center', gap:'10px' }}>
        <Blocks size={24} color="#8b5cf6" /> Modules Core
      </div>
      <div style={{ color:'#94a3b8', fontSize:'14px', marginBottom:'24px' }}>
        {modules.length} capability plugins currently loaded in the AI core.
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '16px' }}>
        {modules.map((m, i) => {
          const isActive = m.status === 'active';
          const isWarning = m.status === 'no-key';
          const col = isActive ? '#4ade80' : isWarning ? '#facc15' : '#64748b';
          return (
            <div key={i} className="module-card" style={{ display:'flex', flexDirection:'column', gap: '12px' }}>
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
                <div style={{ display:'flex', alignItems:'center', gap:'10px' }}>
                  <div style={{ padding:'8px', background:'rgba(255,255,255,0.05)', borderRadius:'12px', display:'flex' }}>
                    <Blocks size={18} color={col} />
                  </div>
                  <div style={{ fontWeight:600, fontSize:'15px', color: '#f8fafc' }}>{m.name}</div>
                </div>
                <div style={{ display:'flex', alignItems:'center', gap:'6px', background: 'rgba(0,0,0,0.3)', padding: '4px 10px', borderRadius: '12px', border:`1px solid ${col}20` }}>
                  <div style={{ width:'8px', height:'8px', borderRadius:'50%', background:col, boxShadow: isActive || isWarning ? `0 0 10px ${col}` : 'none' }} />
                  <span style={{ fontSize:'10px', color:col, textTransform:'uppercase', fontWeight:700, letterSpacing:'0.5px' }}>{m.status}</span>
                </div>
              </div>
              <div style={{ color:'#64748b', fontSize:'12px', fontFamily:'monospace', background:'rgba(0,0,0,0.2)', padding:'6px 10px', borderRadius:'6px' }}>
                {m.file}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  const renderAgents = () => (
    <div className="glass-panel" style={{ flex:1, padding:'24px', overflowY:'auto' }}>
      <div style={{ fontWeight:700, fontSize:'18px', marginBottom:'16px' }}>Active Agents ({agentList.length})</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '15px' }}>
        {agentList.map((a, i) => {
          const col = a.status === 'active' ? '#4ade80' : '#ef4444';
          return (
            <div key={i} className="module-card" style={{ display:'flex', flexDirection:'column', gap: '8px' }}>
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                <div style={{ fontWeight:600, fontSize:'15px', color: '#f8fafc' }}>{a.name}</div>
                <div style={{ display:'flex', alignItems:'center', gap:'6px', background: 'rgba(0,0,0,0.2)', padding: '4px 8px', borderRadius: '12px' }}>
                  <div style={{ width:'8px', height:'8px', borderRadius:'50%', background:col, boxShadow: a.status==='active' ? `0 0 10px ${col}` : 'none' }} />
                  <span style={{ fontSize:'10px', color:col, textTransform:'uppercase', fontWeight:700 }}>{a.status}</span>
                </div>
              </div>
              <div style={{ color:'#a78bfa', fontSize:'11px', fontWeight:600, textTransform:'uppercase', letterSpacing:'1px' }}>{a.type}</div>
              <div style={{ color:'#94a3b8', fontSize:'13px', lineHeight:'1.4' }}>{a.description}</div>
            </div>
          );
        })}
      </div>
    </div>
  );

  const renderSettings = () => (
    <div className="glass-panel" style={{ flex:1, padding:'32px', overflowY:'auto' }}>
      <div style={{ fontWeight:700, fontSize:'22px', marginBottom:'24px', display:'flex', alignItems:'center', gap:'10px' }}>
        <Settings size={24} color="#3b82f6" /> System Preferences
      </div>

      <div style={{ display:'flex', flexDirection:'column', gap:'24px', maxWidth:'800px' }}>
        
        {/* Personalization Section */}
        <div style={{ background:'rgba(0,0,0,0.2)', padding:'24px', borderRadius:'16px', border:'1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ display:'flex', alignItems:'center', gap:'8px', marginBottom:'16px', color:'#f8fafc', fontWeight:600 }}>
            <Heart size={18} color="#ec4899" /> Personalization
          </div>
          
          <div>
            <label style={{ fontSize:'13px', color:'#94a3b8', display:'block', marginBottom:'8px', fontWeight: 500 }}>Your Name</label>
            <input className="input-field" type="text" value={settings.user_name || ''} placeholder="e.g. Rao Alok Yadav"
              onChange={e => { setSettings(p => ({ ...p, user_name: e.target.value })); setSettingsDirty(true); }}
              style={{ width:'100%', boxSizing:'border-box', background:'rgba(0,0,0,0.3)', border:'1px solid rgba(255,255,255,0.1)' }} />
          </div>
        </div>

        {/* AI Engine Section */}
        <div style={{ background:'rgba(0,0,0,0.2)', padding:'24px', borderRadius:'16px', border:'1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ display:'flex', alignItems:'center', gap:'8px', marginBottom:'16px', color:'#f8fafc', fontWeight:600 }}>
            <Zap size={18} color="#eab308" /> AI Engine Configuration
          </div>

          <div className="settings-grid" style={{ marginBottom:'20px' }}>
            <div>
              <label style={{ fontSize:'13px', color:'#94a3b8', display:'block', marginBottom:'8px', fontWeight: 500 }}>Gemini API Key</label>
              <input className="input-field" type="password" value={settings.api_key || ''} placeholder="AIza..."
                onChange={e => { setSettings(p => ({ ...p, api_key: e.target.value })); setSettingsDirty(true); }}
                style={{ width:'100%', boxSizing:'border-box', background:'rgba(0,0,0,0.3)', border:'1px solid rgba(255,255,255,0.1)' }} />
            </div>
            
            <div>
              <label style={{ fontSize:'13px', color:'#94a3b8', display:'block', marginBottom:'8px', fontWeight: 500 }}>AI Model</label>
              <select className="input-field" value={settings.gemini_model} onChange={e => { setSettings(p => ({ ...p, gemini_model: e.target.value })); setSettingsDirty(true); }}
                style={{ width:'100%', boxSizing:'border-box', background:'rgba(0,0,0,0.3)', border:'1px solid rgba(255,255,255,0.1)' }}>
                {models.map(m => <option key={m.id} value={m.id}>{m.label}</option>)}
              </select>
            </div>
          </div>

          <div className="settings-grid">
            <div>
              <label style={{ fontSize:'13px', color:'#94a3b8', display:'block', marginBottom:'8px', fontWeight: 500 }}>Voice Profile</label>
              <select className="input-field" value={settings.gemini_voice} onChange={e => { setSettings(p => ({ ...p, gemini_voice: e.target.value })); setSettingsDirty(true); }}
                style={{ width:'100%', boxSizing:'border-box', background:'rgba(0,0,0,0.3)', border:'1px solid rgba(255,255,255,0.1)' }}>
                {voices.map(v => <option key={v.id} value={v.id}>{v.label}</option>)}
              </select>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'8px' }}>
                <label style={{ fontSize:'13px', color:'#94a3b8', fontWeight: 500 }}>Temperature</label>
                <span style={{color:'#60a5fa', fontWeight:700, fontSize:'13px'}}>{settings.temperature}</span>
              </div>
              <input type="range" min="0" max="1" step="0.1" value={settings.temperature}
                onChange={e => { setSettings(p => ({ ...p, temperature: parseFloat(e.target.value) })); setSettingsDirty(true); }}
                style={{ width:'100%', cursor:'pointer', marginTop:'4px' }} />
            </div>
          </div>
        </div>
        
        {/* Actions */}
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginTop:'8px' }}>
          <div style={{ fontSize:'13px', color:'#64748b', display:'flex', alignItems:'center', gap:'6px' }}>
            <ShieldCheck size={16} /> Configuration persistently saved securely.
          </div>
          <button className="btn-primary" onClick={saveSettings} disabled={!settingsDirty} style={{ padding:'12px 32px', fontSize:'14px' }}>
            Save Changes
          </button>
        </div>

      </div>
    </div>
  );

  const navItems = [
    { id:'home', label:'Dashboard', icon: <LayoutDashboard size={18} /> },
    { id:'commands', label:'Commands', icon: <Terminal size={18} /> },
    { id:'modules', label:'Modules', icon: <Blocks size={18} /> },
    { id:'agents', label:'Agents', icon: <Activity size={18} /> },
    { id:'settings', label:'Settings', icon: <Settings size={18} /> },
  ];

  const activeCount = modules.filter(m => m.status === 'active').length;

  const getThemeVars = () => {
    return {
      '--theme-primary-start': '#3b82f6',
      '--theme-primary-end': '#06b6d4',
      '--theme-primary-rgb': '59, 130, 246',
      '--theme-secondary-rgb': '139, 92, 246',
      '--theme-bg-1': 'rgba(59, 130, 246, 0.15)',
      '--theme-bg-2': 'rgba(139, 92, 246, 0.15)',
    };
  };

  const currentEmoji = <Heart size={22} />;

  return (
    <div className="app-wrapper" style={{ display:'flex', padding:'24px', gap:'24px', height:'100vh', width:'100%', ...getThemeVars() }}>
      
      {/* Toast Notification */}
      {toast && (
        <div style={{
          position: 'fixed', top: '30px', left: '50%', transform: 'translateX(-50%)', zIndex: 1000,
          background: toast.type === 'error' ? 'rgba(239, 68, 68, 0.9)' : 'rgba(74, 222, 128, 0.9)',
          color: toast.type === 'error' ? '#fff' : '#064e3b',
          padding: '12px 24px', borderRadius: '30px', fontWeight: 600, fontSize: '14px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.3)', backdropFilter: 'blur(10px)',
          animation: 'slideDown 0.3s ease-out', border: '1px solid rgba(255,255,255,0.2)'
        }}>
          {toast.message}
        </div>
      )}

      {/* Main Content Area */}
      <main style={{ flex:1, display:'flex', flexDirection:'column', minHeight:0 }}>
        
        {/* Top Navbar */}
        <div className="glass-panel top-navbar">
          <div style={{ display:'flex', alignItems:'center', gap:'12px' }}>
            <div style={{ width:'32px', height:'32px', borderRadius:'10px', background:'linear-gradient(135deg, var(--theme-primary-start), var(--theme-primary-end))', display:'flex', alignItems:'center', justifyContent:'center', fontSize:'16px', color: '#fff', flexShrink: 0 }}>{currentEmoji}</div>
            <h1 style={{ fontSize:'20px', fontWeight:800, letterSpacing:'2px', background:'linear-gradient(135deg, var(--theme-primary-start), var(--theme-primary-end))', WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent', margin:0 }}>SIVI</h1>
          </div>
          
          <nav className="nav-scroll-container">
            {navItems.map(n => (
              <button key={n.id} onClick={() => setPage(n.id)} className={`nav-btn ${page === n.id ? 'active' : ''}`}>
                {n.icon}<span className="nav-label">{n.label}</span>
              </button>
            ))}
          </nav>
          
          <div style={{ display:'flex', alignItems:'center', gap:'15px', flexShrink: 0 }}>
             <div style={{ display:'flex', alignItems:'center', gap:'6px' }}>
               <div style={{ width:'8px', height:'8px', borderRadius:'50%', background: serverOnline ? '#4ade80' : '#ef4444', boxShadow: serverOnline ? '0 0 10px #4ade80' : '0 0 10px #ef4444' }} />
               <span style={{ fontSize:'12px', color:'#cbd5e1', fontWeight: 500 }}>{serverOnline ? 'Online' : 'Offline'}</span>
             </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '24px', flex: 1, height: '100%', overflow: 'hidden' }}>
          {{ home: renderHome, commands: renderCommands, modules: renderModules, settings: renderSettings, agents: renderAgents }[page]?.()}
        </div>
      </main>
    </div>
  );
}
