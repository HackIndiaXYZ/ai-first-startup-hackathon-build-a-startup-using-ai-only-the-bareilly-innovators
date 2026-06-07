import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { 
  LayoutDashboard, Terminal, Blocks, Settings, 
  Heart, Briefcase, Bot, Code, Play, Square, 
  Mic, MicOff, Hand, BatteryCharging, Activity,
  CloudRain, Newspaper, Battery, Calendar, Monitor, Clock, ShieldCheck, Zap, Sun
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

  const fetchSystemInfo = async () => {
    try {
      const r = await axios.get(`${API}/system-info`);
      setSysInfo(r.data);
    } catch (e) { console.error("fetchSystemInfo error:", e); }
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
    // Current time formatting
    const now = currentTime;
    const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const dateString = now.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
    const dayString = now.toLocaleDateString('en-GB', { weekday: 'long' });

    // Battery & CPU from sysInfo
    const battery = sysInfo?.battery_percent >= 0 ? sysInfo.battery_percent : 100;
    const isCharging = sysInfo?.battery_plugged || false;
    const cpuTemp = sysInfo?.cpu_percent ? Math.round(sysInfo.cpu_percent / 2 + 35) : 45; // Mock temp based on usage

    return (
      <div style={{ position: 'relative', flex:1, display: 'flex', flexDirection: 'column', overflowY: 'auto', overflowX: 'hidden' }}>
        <iframe ref={iframeRef} src="/particles.html" style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 'none', zIndex: 0, opacity: 0.6, pointerEvents: 'none' }} />
        
        {/* Top Header */}
        <div style={{ position: 'relative', zIndex: 1, textAlign: 'center', paddingTop: '5px' }}>
          <h1 style={{ fontSize: '2.2rem', fontWeight: 800, letterSpacing: '2px', background: 'linear-gradient(135deg, #e2e8f0, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', margin: 0 }}>SMART BRIEFINGS</h1>
          <p style={{ fontSize: '1rem', color: '#cbd5e1', letterSpacing: '3px', marginTop: '2px', textTransform: 'uppercase' }}>Ab on hote hi, Sivi batayegi sab kuch.</p>
        </div>

        {/* Dashboard Grid */}
        <div className="dashboard-grid" style={{ position: 'relative', zIndex: 1, flex: 1 }}>
          
          {/* Left Column */}
          <div className="dashboard-column" style={{ justifyContent: 'center' }}>
            {/* Weather Card */}
            <div className="glass-panel hover-glow" style={{ padding: '15px' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', letterSpacing: '1px', marginBottom: '8px' }}>WEATHER & TEMPERATURE</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                <Sun size={32} color="#fbbf24" />
                <div>
                  <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#fff', lineHeight: 1 }}>28°C</div>
                  <div style={{ color: '#cbd5e1', fontSize: '13px' }}>Partly Cloudy</div>
                </div>
              </div>
              <div style={{ marginTop: '10px', fontSize: '12px', color: '#64748b' }}>
                Feels like 31°C <br/> Humidity: 60%
              </div>
            </div>

            {/* News Card */}
            <div className="glass-panel hover-glow" style={{ padding: '15px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <div style={{ fontSize: '11px', color: '#94a3b8', letterSpacing: '1px', display: 'flex', alignItems: 'center', gap:'8px' }}>
                  <Newspaper size={12}/> IMPORTANT NEWS
                </div>
                <div style={{ background: 'linear-gradient(135deg, var(--theme-primary-start), var(--theme-primary-end))', padding: '2px 6px', borderRadius: '10px', fontSize: '9px', fontWeight: 'bold' }}>NEW</div>
              </div>
              <div style={{ color: '#fff', fontWeight: 600, fontSize: '13px', marginBottom: '8px' }}>Top Stories For You</div>
              <ul style={{ color: '#cbd5e1', fontSize: '12px', paddingLeft: '15px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <li>Global tech stocks rally</li>
                <li>New AI breakthrough by DeepMind</li>
                <li>Local metro expansion begins</li>
              </ul>
            </div>

            {/* Battery Card */}
            <div className="glass-panel hover-glow" style={{ padding: '15px' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', letterSpacing: '1px', marginBottom: '8px' }}>BATTERY STATUS</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                <Battery size={32} color={battery > 20 ? "#4ade80" : "#ef4444"} />
                <div>
                  <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#fff', lineHeight: 1 }}>{battery}%</div>
                  <div style={{ color: isCharging ? '#4ade80' : '#cbd5e1', fontSize: '12px', display:'flex', alignItems:'center', gap:'4px', marginTop:'2px' }}>
                    {isCharging ? <><Zap size={12}/> Charging</> : 'On Battery'}
                  </div>
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

          {/* Right Column */}
          <div className="dashboard-column" style={{ justifyContent: 'center' }}>
            
            {/* Start Your Day Smarter Text */}
            <div style={{ padding: '0 5px' }}>
              <div style={{ color: '#cbd5e1', fontSize: '12px', letterSpacing: '1px' }}>START YOUR DAY</div>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--theme-primary-start)', lineHeight: 1 }}>SMARTER</div>
              <div style={{ color: '#94a3b8', fontSize: '12px', marginTop: '6px' }}>The moment Sivi wakes up, she briefs you.</div>
              <div style={{ color: 'var(--theme-primary-end)', fontStyle: 'italic', fontSize: '16px', marginTop: '4px', textAlign: 'right', fontFamily: 'serif' }}>Just for You <Heart size={12} style={{display:'inline'}}/></div>
            </div>

            {/* Schedule Card */}
            <div className="glass-panel hover-glow" style={{ padding: '15px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <Calendar size={16} color="#a78bfa" />
                <div>
                  <div style={{ fontSize: '11px', color: '#94a3b8', letterSpacing: '1px' }}>TODAY'S SCHEDULE</div>
                  <div style={{ color: '#fff', fontSize: '13px', fontWeight: 'bold' }}>{dateString.toUpperCase()}</div>
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '10px' }}>
                <div style={{ display: 'flex', gap: '15px', fontSize: '12px' }}><span style={{color: '#cbd5e1', width: '55px'}}>10:00 AM</span> <span style={{color: '#fff'}}>Team Meeting</span></div>
                <div style={{ display: 'flex', gap: '15px', fontSize: '12px' }}><span style={{color: '#cbd5e1', width: '55px'}}>01:00 PM</span> <span style={{color: '#fff'}}>Client Call</span></div>
                <div style={{ display: 'flex', gap: '15px', fontSize: '12px' }}><span style={{color: '#cbd5e1', width: '55px'}}>04:30 PM</span> <span style={{color: '#fff'}}>Project Review</span></div>
              </div>
            </div>

            {/* System Info Card */}
            <div className="glass-panel hover-glow" style={{ padding: '15px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                <Monitor size={16} color="#60a5fa" />
                <div style={{ fontSize: '11px', color: '#94a3b8', letterSpacing: '1px' }}>SYSTEM INFORMATION</div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{color: '#cbd5e1'}}>CPU</span>
                  <span style={{color: '#fff'}}>{cpuTemp}°C <span style={{color: '#4ade80', marginLeft: '5px'}}>Normal</span></span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{color: '#cbd5e1'}}>RAM</span>
                  <span style={{color: '#fff'}}>{sysInfo?.ram_percent || 45}% <span style={{color: '#4ade80', marginLeft: '5px'}}>Normal</span></span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{color: '#cbd5e1'}}>Network</span>
                  <span style={{color: '#4ade80'}}>Connected</span>
                </div>
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
                {isConnected ? '"STOP SESSION"' : '"GOOD MORNING, SIVI"'}
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
          <div key={i} className="module-card" style={{ display:'flex', justifyContent:'space-between', alignItems:'center', flexWrap: 'wrap', gap: '10px' }}>
            <div style={{ minWidth: '150px' }}>
              <div style={{ fontWeight:600, fontSize:'15px', color: '#f8fafc', marginBottom: '4px', wordBreak: 'break-word' }}>{m.name}</div>
              <div style={{ color:'#64748b', fontSize:'12px', fontFamily:'monospace', wordBreak: 'break-all' }}>{m.file}</div>
            </div>
            <div style={{ display:'flex', alignItems:'center', gap:'8px', background: 'rgba(0,0,0,0.2)', padding: '6px 12px', borderRadius: '20px', flexShrink: 0 }}>
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
        <div className="glass-panel" style={{ display:'flex', justifyContent:'space-between', alignItems:'center', padding:'10px 24px', marginBottom:'20px', borderRadius:'20px', zIndex: 10, flexWrap: 'wrap', gap: '15px' }}>
          <div style={{ display:'flex', alignItems:'center', gap:'12px' }}>
            <div style={{ width:'32px', height:'32px', borderRadius:'10px', background:'linear-gradient(135deg, var(--theme-primary-start), var(--theme-primary-end))', display:'flex', alignItems:'center', justifyContent:'center', fontSize:'16px', color: '#fff', flexShrink: 0 }}>{currentEmoji}</div>
            <h1 style={{ fontSize:'20px', fontWeight:800, letterSpacing:'2px', background:'linear-gradient(135deg, var(--theme-primary-start), var(--theme-primary-end))', WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent', margin:0 }}>SIVI</h1>
          </div>
          
          <nav style={{ display:'flex', gap:'10px', overflowX: 'auto', flexWrap: 'wrap', justifyContent: 'center' }}>
            {navItems.map(n => (
              <button key={n.id} onClick={() => setPage(n.id)} className={`nav-btn ${page === n.id ? 'active' : ''}`} style={{ padding:'8px 16px', borderRadius:'12px', width:'auto', display:'flex', alignItems:'center', gap:'8px', flexShrink: 0 }}>
                {n.icon}<span>{n.label}</span>
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
          {{ home: renderHome, commands: renderCommands, modules: renderModules, settings: renderSettings }[page]?.()}
        </div>
      </main>
    </div>
  );
}
