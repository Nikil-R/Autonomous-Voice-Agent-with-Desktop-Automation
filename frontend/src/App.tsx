import React, { useState, useEffect, useRef } from 'react';
import { 
  Mic, 
  MicOff, 
  Volume2, 
  Cpu, 
  Sparkles, 
  Command, 
  ChevronDown, 
  ChevronUp, 
  Radio 
} from 'lucide-react';
import './App.css';

const API_BASE = 'http://127.0.0.1:8000';

interface VitalsData {
  cpu: number;
  ram: number;
  disk: number;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
}

export default function App(): React.JSX.Element {
  const [isListening, setIsListening] = useState<boolean>(false);
  const [continuousMode, setContinuousMode] = useState<boolean>(true);
  const [status, setStatus] = useState<'idle' | 'listening' | 'thinking' | 'speaking'>('idle');
  const [interimText, setInterimText] = useState<string>('');
  const [lastResponse, setLastResponse] = useState<string>('');
  const [expanded, setExpanded] = useState<boolean>(false);
  const [vitals, setVitals] = useState<VitalsData>({ cpu: 0, ram: 0, disk: 0 });
  const [history, setHistory] = useState<ChatMessage[]>([
    { role: 'assistant', text: 'Jarvis Voice Notch is online. Press Spacebar or click to speak.' }
  ]);

  const recognitionRef = useRef<any>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const silenceTimerRef = useRef<any>(null);
  const speechBufferRef = useRef<string>('');
  const wsRef = useRef<WebSocket | null>(null);
  const audioQueueRef = useRef<Blob[]>([]);
  const isPlayingQueueRef = useRef<boolean>(false);

  // Stop currently playing audio immediately (Instant Barge-In)
  const stopAudio = (): void => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current.currentTime = 0;
      currentAudioRef.current = null;
    }
    audioQueueRef.current = [];
    isPlayingQueueRef.current = false;
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'interrupt' }));
    }
  };

  // Play next audio chunk from WebSocket streaming queue
  const playNextInQueue = () => {
    if (audioQueueRef.current.length === 0) {
      isPlayingQueueRef.current = false;
      setStatus(isListening ? 'listening' : 'idle');
      return;
    }
    isPlayingQueueRef.current = true;
    setStatus('speaking');
    const chunkBlob = audioQueueRef.current.shift()!;
    const audioUrl = URL.createObjectURL(chunkBlob);
    const audio = new Audio(audioUrl);
    currentAudioRef.current = audio;
    audio.onended = () => {
      URL.revokeObjectURL(audioUrl);
      playNextInQueue();
    };
    audio.onerror = () => {
      URL.revokeObjectURL(audioUrl);
      playNextInQueue();
    };
    audio.play().catch(() => playNextInQueue());
  };

  // Initialize persistent streaming WebSocket
  useEffect(() => {
    const wsUrl = API_BASE.replace('http', 'ws') + '/ws/stream';
    const connectWs = () => {
      try {
        const ws = new WebSocket(wsUrl);
        ws.binaryType = 'blob';

        ws.onopen = () => {
          console.log('⚡ Connected to ApexCore binary audio WebSocket');
        };

        ws.onmessage = (event) => {
          if (event.data instanceof Blob) {
            // Received binary MP3 audio chunk!
            audioQueueRef.current.push(event.data);
            if (!isPlayingQueueRef.current) {
              playNextInQueue();
            }
          } else {
            try {
              const msg = JSON.parse(event.data);
              if (msg.type === 'token') {
                setLastResponse((prev) => prev + msg.content);
              } else if (msg.type === 'done') {
                if (msg.full_response) {
                  setLastResponse(msg.full_response);
                  setHistory((prev) => [...prev, { role: 'assistant', text: msg.full_response }]);
                }
              }
            } catch (e) {}
          }
        };

        ws.onclose = () => {
          setTimeout(connectWs, 2000);
        };
        wsRef.current = ws;
      } catch (err) {
        console.warn('WebSocket connection error:', err);
      }
    };

    connectWs();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [isListening]);

  // Fetch real-time vitals
  useEffect(() => {
    const fetchVitals = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/tools/vitals`);
        const data = await res.json();
        setVitals({
          cpu: data.cpu_usage_percent || 0,
          ram: data.ram_percent || 0,
          disk: data.disk_c_free_gb || 0
        });
      } catch (e) {
        // Backend offline or reloading
      }
    };
    fetchVitals();
    const interval = setInterval(fetchVitals, 3000);
    return () => clearInterval(interval);
  }, []);

  // Web Speech Recognition Setup
  useEffect(() => {
    const windowAny = window as any;
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRec = windowAny.SpeechRecognition || windowAny.webkitSpeechRecognition;
      const rec = new SpeechRec();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = 'en-US';

      rec.onstart = () => {
        setIsListening(true);
        setStatus('listening');
      };

      rec.onresult = (event: any) => {
        let interim = '';
        let final = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            final += event.results[i][0].transcript;
          } else {
            interim += event.results[i][0].transcript;
          }
        }

        // Instant Barge-In: Kill speech audio immediately when user vocalizes
        if (interim.trim().length > 0 || final.trim().length > 0) {
          if (currentAudioRef.current && !currentAudioRef.current.paused) {
            console.log('🚨 Instant Barge-in interrupt triggered!');
            stopAudio();
            setStatus('listening');
          }
        }

        setInterimText(interim || final);

        if (final.trim().length > 0) {
          speechBufferRef.current += ' ' + final.trim();
        }

        // Dynamic silence debounce:
        // If final transcript is detected, dispatch quickly in 450ms; if only interim, give 800ms
        clearTimeout(silenceTimerRef.current);
        const debounceTime = final.trim().length > 0 ? 450 : 800;
        silenceTimerRef.current = setTimeout(() => {
          const userPrompt = (speechBufferRef.current + ' ' + interim).trim();
          if (userPrompt.length > 0) {
            speechBufferRef.current = '';
            setInterimText('');
            sendUserMessage(userPrompt);
          }
        }, debounceTime);
      };

      rec.onend = () => {
        if (continuousMode && isListening) {
          try {
            rec.start();
          } catch (e) {}
        } else {
          setIsListening(false);
          setStatus('idle');
        }
      };

      rec.onerror = (err: any) => {
        if (err.error !== 'no-speech') {
          console.warn('Speech error:', err.error);
        }
      };

      recognitionRef.current = rec;
    }
  }, [continuousMode, isListening]);

  // Send message to FastAPI Backend
  const sendUserMessage = async (prompt: string): Promise<void> => {
    stopAudio();
    setStatus('thinking');
    setHistory((prev) => [...prev, { role: 'user', text: prompt }]);
    setLastResponse('');

    // If streaming WebSocket is connected, dispatch over WebSocket for sub-300ms streaming audio!
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ prompt }));
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      });
      const data = await res.json();

      setLastResponse(data.response);
      setHistory((prev) => [...prev, { role: 'assistant', text: data.response }]);

      if (data.audio_base64) {
        setStatus('speaking');
        stopAudio();
        const audio = new Audio('data:audio/mp3;base64,' + data.audio_base64);
        currentAudioRef.current = audio;
        audio.onended = () => {
          setStatus(isListening ? 'listening' : 'idle');
          currentAudioRef.current = null;
        };
        audio.play();
      } else {
        setStatus(isListening ? 'listening' : 'idle');
      }
    } catch (err) {
      console.error('API Error:', err);
      setStatus('idle');
      setHistory((prev) => [...prev, { role: 'assistant', text: 'Error connecting to Jarvis backend.' }]);
    }
  };

  // Toggle voice recognition
  const toggleVoice = (): void => {
    if (!recognitionRef.current) return;
    if (isListening) {
      setContinuousMode(false);
      setIsListening(false);
      stopAudio();
      recognitionRef.current.stop();
      setStatus('idle');
    } else {
      setContinuousMode(true);
      setIsListening(true);
      stopAudio();
      try {
        recognitionRef.current.start();
      } catch (e) {}
    }
  };

  // Global Hotkey (Spacebar) to toggle continuous listening
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
      if (tag === 'input' || tag === 'textarea') return;

      if (e.code === 'Space') {
        e.preventDefault();
        toggleVoice();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  });

  return (
    <div className="hud-container">
      {/* 🚀 Dynamic On-Screen Notch / Island */}
      <div 
        className={`notch-island interactive ${status} ${expanded ? 'notch-expanded' : ''}`}
        onClick={() => !expanded && toggleVoice()}
      >
        <div className="notch-content">
          {/* Status Indicator Icon */}
          <div className={`status-indicator ${status}`}>
            {status === 'listening' ? (
              <div className="wave-bars">
                <span className="bar bar-1"></span>
                <span className="bar bar-2"></span>
                <span className="bar bar-3"></span>
              </div>
            ) : status === 'speaking' ? (
              <Volume2 className="icon-pulse" size={18} />
            ) : status === 'thinking' ? (
              <Sparkles className="icon-pulse" size={18} />
            ) : (
              <Radio size={16} />
            )}
          </div>

          {/* Notch Text State */}
          <div className="notch-text-wrapper">
            <span className="notch-brand">JARVIS</span>
            <span className="notch-state-desc">
              {status === 'listening'
                ? interimText ? `"${interimText}"` : 'Listening... (Speak naturally)'
                : status === 'speaking'
                ? lastResponse || 'Speaking...'
                : status === 'thinking'
                ? 'Executing...'
                : 'Press Space to Activate'}
            </span>
          </div>

          {/* Quick Stats Pill */}
          <div className="notch-vitals">
            <Cpu size={14} className="vital-icon" />
            <span className="vital-tag">{vitals.cpu}%</span>
          </div>

          {/* Expand HUD Toggle */}
          <button 
            className="expand-btn interactive"
            onClick={(e: React.MouseEvent) => {
              e.stopPropagation();
              setExpanded(!expanded);
            }}
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>

        {/* 📋 Expanded HUD Tray when clicked */}
        {expanded && (
          <div className="hud-expanded-tray interactive" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
            <div className="hud-tray-header">
              <div className="hud-vitals-row">
                <div className="hud-metric">
                  <span className="metric-label">CPU</span>
                  <span className="metric-val">{vitals.cpu}%</span>
                </div>
                <div className="hud-metric">
                  <span className="metric-label">RAM</span>
                  <span className="metric-val">{vitals.ram}%</span>
                </div>
                <div className="hud-metric">
                  <span className="metric-label">Disk C</span>
                  <span className="metric-val">{vitals.disk} GB</span>
                </div>
              </div>
              <div className="tray-controls">
                <button className="pill-btn" onClick={toggleVoice}>
                  {isListening ? <MicOff size={14} /> : <Mic size={14} />}
                  {isListening ? 'Mute' : 'Listen'}
                </button>
              </div>
            </div>

            {/* Conversation Stream */}
            <div className="hud-chat-history">
              {history.map((msg, i) => (
                <div key={i} className={`hud-bubble ${msg.role}`}>
                  <span className="hud-bubble-role">{msg.role === 'user' ? 'You' : 'Jarvis'}</span>
                  <p>{msg.text}</p>
                </div>
              ))}
            </div>

            {/* Manual Command Input */}
            <form 
              className="hud-input-row"
              onSubmit={(e: React.FormEvent<HTMLFormElement>) => {
                e.preventDefault();
                const form = e.currentTarget;
                const input = form.elements.namedItem('cmd') as HTMLInputElement;
                if (input && input.value.trim()) {
                  sendUserMessage(input.value.trim());
                  input.value = '';
                }
              }}
            >
              <input 
                name="cmd" 
                placeholder="Type a command or press Spacebar to speak..." 
                autoComplete="off"
              />
              <button type="submit" className="send-action-btn">
                <Command size={14} />
              </button>
            </form>
          </div>
        )}
      </div>

      {/* Floating Hotkey Instruction Pill */}
      {!expanded && (
        <div className="hotkey-pill interactive" onClick={toggleVoice}>
          <kbd>SPACE</kbd>
          <span>{isListening ? 'Mute Jarvis' : 'Voice Activate'}</span>
        </div>
      )}
    </div>
  );
}
