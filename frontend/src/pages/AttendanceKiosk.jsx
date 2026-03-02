import { useState, useRef, useEffect, useCallback } from 'react';
import api from '../services/api';

/* -------------------------------------------------------
   CONSTANTS
------------------------------------------------------- */
const DETECT_INTERVAL_MS = 350;    // Face detection polling cadence
const DETECT_THROTTLE_MS = 800;    // Min gap between backend detect calls
const DETECT_CONF_GATE = 0.70;   // Skip frames where confidence < 70%
const MOTION_THRESHOLD = 25;     // Pixel-diff to wake kiosk
const ERROR_AUTO_CLEAR_MS = 3000;   // Auto-clear error/liveness toast

const FRAME_W = 640;                // Fixed capture resolution
const FRAME_H = 480;

export default function AttendanceKiosk() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const motionRef = useRef(null);   // previous grey frame for motion
  const detectTimer = useRef(null);
  const lastDetectRef = useRef(0);      // timestamp of last backend detect call
  const errorTimerRef = useRef(null);   // auto-clear error timer

  const [isStreaming, setIsStreaming] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDetecting, setIsDetecting] = useState(false); // subtle bbox spinner
  const [processingStage, setProcessingStage] = useState('');
  const [capturedImage, setCapturedImage] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [todayLogs, setTodayLogs] = useState([]);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [faceBox, setFaceBox] = useState(null); // {x,y,w,h,confidence}
  const [isMotionActive, setIsMotionActive] = useState(true);

  /* ------- Auto-clear error after 3 s ------- */
  const setErrorWithAutoClear = useCallback((msg) => {
    setError(msg);
    if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
    if (msg) {
      errorTimerRef.current = setTimeout(() => setError(null), ERROR_AUTO_CLEAR_MS);
    }
  }, []);

  /* ------- Clock ------- */
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  /* ------- Camera + Logs on mount ------- */
  useEffect(() => {
    startCamera();
    fetchTodayLogs();
    return () => { stopCamera(); stopDetection(); };
  }, []);

  /* ------- Start face detection loop once camera is streaming ------- */
  useEffect(() => {
    if (isStreaming && !isProcessing) {
      startDetection();
    } else {
      stopDetection();
    }
    return () => stopDetection();
  }, [isStreaming, isProcessing]);

  /* ===================================
     CAMERA
  =================================== */
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        // Fixed 640×480 — sufficient for recognition, faster processing
        video: { width: { ideal: FRAME_W }, height: { ideal: FRAME_H }, facingMode: 'user' },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setIsStreaming(true);
        setError(null);
      }
    } catch {
      setError('Camera access denied.');
    }
  };

  const stopCamera = () => {
    if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
    if (videoRef.current) videoRef.current.srcObject = null;
    setIsStreaming(false);
  };

  /* ===================================
     FRAME CAPTURE
  =================================== */
  const captureFrame = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return null;
    const v = videoRef.current, c = canvasRef.current;
    // Always draw at 640×480 regardless of CSS display size
    c.width = FRAME_W;
    c.height = FRAME_H;
    c.getContext('2d').drawImage(v, 0, 0, FRAME_W, FRAME_H);
    return c.toDataURL('image/jpeg', 0.82).split(',')[1];
  }, []);

  const captureMultipleFrames = useCallback(
    () =>
      new Promise(resolve => {
        const frames = [];
        let count = 0;
        const iv = setInterval(() => {
          const frame = captureFrame();
          if (frame) frames.push(frame);
          count++;
          if (count >= 10) { clearInterval(iv); resolve(frames); }
        }, 200);
      }),
    [captureFrame],
  );

  /* ===================================
     REAL-TIME FACE DETECTION (bounding box)
     — throttled to 800ms, gated on confidence > 70%
  =================================== */
  const startDetection = () => {
    stopDetection();
    detectTimer.current = setInterval(async () => {
      if (isProcessing) return;

      // Throttle: skip if last call was < DETECT_THROTTLE_MS ago
      const now = Date.now();
      if (now - lastDetectRef.current < DETECT_THROTTLE_MS) return;

      const frame = captureFrame();
      if (!frame) return;

      lastDetectRef.current = now;
      setIsDetecting(true);

      try {
        const r = await api.post('/verification/detect', { image_base64: frame });
        if (r.data.detected && r.data.faces?.length > 0) {
          const face = r.data.faces[0];
          // Gate: only update bounding box if confidence > 70%
          if ((face.confidence ?? 1) >= DETECT_CONF_GATE) {
            setFaceBox(face);
            setIsMotionActive(true);
          } else {
            setFaceBox(null);
          }
        } else {
          setFaceBox(null);
        }
      } catch {
        // Detection endpoint not available — silent fail
        setFaceBox(null);
      } finally {
        setIsDetecting(false);
      }
    }, DETECT_INTERVAL_MS);
  };

  const stopDetection = () => {
    if (detectTimer.current) {
      clearInterval(detectTimer.current);
      detectTimer.current = null;
    }
    setFaceBox(null);
    setIsDetecting(false);
  };

  /* ===================================
     MOTION DETECTION (auto-wake)
  =================================== */
  const checkMotion = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return;
    const v = videoRef.current, c = canvasRef.current;
    c.width = 160; c.height = 120;
    const ctx = c.getContext('2d');
    ctx.drawImage(v, 0, 0, 160, 120);
    const frame = ctx.getImageData(0, 0, 160, 120);

    if (motionRef.current) {
      let diff = 0;
      for (let i = 0; i < frame.data.length; i += 16) {
        diff += Math.abs(frame.data[i] - motionRef.current.data[i]);
      }
      diff /= (frame.data.length / 16);
      if (diff > MOTION_THRESHOLD) setIsMotionActive(true);
    }
    motionRef.current = frame;
  }, []);

  useEffect(() => {
    if (!isStreaming) return;
    const iv = setInterval(checkMotion, 1000);
    return () => clearInterval(iv);
  }, [isStreaming, checkMotion]);

  /* ===================================
     LOGS
  =================================== */
  const fetchTodayLogs = async () => {
    setLoadingLogs(true);
    try {
      const r = await api.get('/verification/today');
      setTodayLogs(r.data || []);
    } catch (e) {
      console.error('Logs error:', e);
    } finally {
      setLoadingLogs(false);
    }
  };

  /* ===================================
     ATTENDANCE ACTION
  =================================== */
  const handleAttendance = async (action) => {
    if (isProcessing) return;
    setIsProcessing(true);
    setProcessingStage('capturing');
    setResult(null);
    setError(null);

    try {
      const frames = await captureMultipleFrames();
      if (frames.length === 0) {
        setErrorWithAutoClear('Failed to capture. Check camera.');
        setIsProcessing(false);
        return;
      }

      const mainFrame = frames[frames.length - 1];
      const livenessFrames = frames.slice(0, frames.length - 1);
      setCapturedImage('data:image/jpeg;base64,' + mainFrame);

      setProcessingStage('verifying');

      const response = await api.post('/verification/face', {
        image_base64: mainFrame,
        action,
        liveness_frames: livenessFrames,
      });

      const data = response.data;
      if (data.success) {
        setResult({
          type: 'success',
          action: data.action,
          employee_name: data.employee_name,
          employee_code: data.employee_code,
          confidence: data.confidence_score,
          liveness: data.liveness_score,
          liveness_details: data.liveness_details,
          timestamp: data.timestamp,
          message: data.message,
        });
        fetchTodayLogs();
      } else {
        setResult({
          type: 'error',
          message: data.message,
          liveness: data.liveness_score,
          liveness_details: data.liveness_details,
          confidence: data.confidence_score,
        });
      }
    } catch (err) {
      console.error('Attendance error:', err);
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        'Server error. Check backend terminal.';
      setErrorWithAutoClear(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsProcessing(false);
      setProcessingStage('');
      setTimeout(() => setCapturedImage(null), 3000);
    }
  };

  const resetState = () => { setResult(null); setError(null); setCapturedImage(null); };

  const fmt = (d) => {
    if (!d) return '\u2014';
    return new Date(d).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
  };

  const checkedInCount = todayLogs.filter(l => l.checked_in).length;
  const checkedOutCount = todayLogs.filter(l => l.checked_out).length;

  /* ===================================
     RENDER HELPERS
  =================================== */
  const renderBoundingBox = () => {
    if (!faceBox || isProcessing || capturedImage) return null;
    const { x, y, w, h, confidence } = faceBox;
    const mirroredX = 1 - x - w;
    const color = confidence > 0.85 ? '#10b981' : confidence > 0.6 ? '#f59e0b' : '#ef4444';
    const cornerLen = '14px';
    const cornerBorder = `2.5px solid ${color}`;

    return (
      <div
        className="absolute pointer-events-none transition-all duration-200 ease-out"
        style={{
          left: `${mirroredX * 100}%`,
          top: `${y * 100}%`,
          width: `${w * 100}%`,
          height: `${h * 100}%`,
        }}
      >
        {/* Glow shadow */}
        <div className="absolute inset-0 rounded-lg" style={{ boxShadow: `0 0 20px 2px ${color}40` }} />

        {/* Corner brackets */}
        <div className="absolute top-0 left-0" style={{ width: cornerLen, height: cornerLen, borderTop: cornerBorder, borderLeft: cornerBorder, borderRadius: '4px 0 0 0' }} />
        <div className="absolute top-0 right-0" style={{ width: cornerLen, height: cornerLen, borderTop: cornerBorder, borderRight: cornerBorder, borderRadius: '0 4px 0 0' }} />
        <div className="absolute bottom-0 left-0" style={{ width: cornerLen, height: cornerLen, borderBottom: cornerBorder, borderLeft: cornerBorder, borderRadius: '0 0 0 4px' }} />
        <div className="absolute bottom-0 right-0" style={{ width: cornerLen, height: cornerLen, borderBottom: cornerBorder, borderRight: cornerBorder, borderRadius: '0 0 4px 0' }} />

        {/* Confidence badge */}
        <div
          className="absolute -top-6 left-1/2 -translate-x-1/2 flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold tracking-wider whitespace-nowrap"
          style={{ backgroundColor: `${color}30`, color, border: `1px solid ${color}50`, backdropFilter: 'blur(4px)' }}
        >
          <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: color }} />
          {(confidence * 100).toFixed(0)}% DETECTED
        </div>

        {/* Subtle "Processing…" spinner while waiting for backend (non-blocking) */}
        {isDetecting && (
          <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-1 text-[9px] text-gray-400 whitespace-nowrap">
            <span className="inline-block w-2.5 h-2.5 border border-gray-500 border-t-transparent rounded-full animate-spin" />
            Processing…
          </div>
        )}
      </div>
    );
  };

  /* ===================================
     MAIN RENDER
  =================================== */
  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">BioAttend Kiosk</h1>
              <p className="text-xs text-gray-400">Face Recognition Attendance</p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-mono font-bold tabular-nums tracking-wider">
              {currentTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true })}
            </div>
            <div className="text-xs text-gray-400">
              {currentTime.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* LEFT — Camera + Buttons */}
          <div className="lg:col-span-2 space-y-5">
            <div className="bg-gray-900 rounded-2xl border border-gray-800 overflow-hidden">
              <div className="relative aspect-video bg-black flex items-center justify-center">
                <video
                  ref={videoRef}
                  autoPlay playsInline muted
                  className={`w-full h-full object-cover ${capturedImage ? 'hidden' : ''}`}
                  style={{ transform: 'scaleX(-1)' }}
                />
                {capturedImage && <img src={capturedImage} alt="Captured" className="w-full h-full object-cover" />}
                <canvas ref={canvasRef} className="hidden" />

                {/* Real-time bounding box */}
                {renderBoundingBox()}

                {/* Face guide frame (static brackets when no face) */}
                {isStreaming && !isProcessing && !capturedImage && !faceBox && (
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className="w-[45%] aspect-[3/4] relative">
                      <div className="absolute top-0 left-0 w-6 h-6 border-t-2 border-l-2 border-gray-500/40 rounded-tl-lg" />
                      <div className="absolute top-0 right-0 w-6 h-6 border-t-2 border-r-2 border-gray-500/40 rounded-tr-lg" />
                      <div className="absolute bottom-0 left-0 w-6 h-6 border-b-2 border-l-2 border-gray-500/40 rounded-bl-lg" />
                      <div className="absolute bottom-0 right-0 w-6 h-6 border-b-2 border-r-2 border-gray-500/40 rounded-br-lg" />
                      <div className="absolute -bottom-7 left-1/2 -translate-x-1/2 text-[10px] text-gray-500 font-medium tracking-wide whitespace-nowrap">
                        Position your face here
                      </div>
                    </div>
                  </div>
                )}

                {/* Camera off */}
                {!isStreaming && !capturedImage && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-500">
                    <svg className="w-16 h-16 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <button onClick={startCamera} className="mt-3 px-4 py-2 bg-blue-600 rounded-lg text-sm hover:bg-blue-500">Retry</button>
                  </div>
                )}

                {/* Processing overlay */}
                {isProcessing && (
                  <div className="absolute inset-0 bg-black/60 flex flex-col items-center justify-center text-center p-6">
                    <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-6" />
                    {processingStage === 'capturing' ? (
                      <div className="animate-pulse">
                        <p className="text-2xl font-black text-yellow-400 mb-2 tracking-tighter">PLEASE BLINK YOUR EYES</p>
                        <p className="text-sm text-white/80 font-medium">Capturing facial micro-movements...</p>
                      </div>
                    ) : (
                      <p className="text-lg text-blue-300 font-bold">Verifying identity...</p>
                    )}
                  </div>
                )}

                {/* LIVE badge + Security badge */}
                {isStreaming && !isProcessing && !capturedImage && (
                  <>
                    <div className="absolute top-4 left-4 flex items-center gap-2 bg-black/50 backdrop-blur-sm rounded-full px-3 py-1.5">
                      <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                      <span className="text-xs font-medium">LIVE</span>
                    </div>
                    <div className="absolute top-4 right-4 flex items-center gap-1.5 bg-black/50 backdrop-blur-sm rounded-full px-3 py-1.5 border border-emerald-500/30">
                      <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                      </svg>
                      <span className="text-xs text-emerald-400 font-medium tracking-tight">Enterprise Active Liveness</span>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Buttons */}
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => handleAttendance('CHECK_IN')}
                disabled={isProcessing || !isStreaming}
                className="py-5 rounded-2xl font-bold text-lg transition-all bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-800 disabled:text-gray-500 disabled:cursor-not-allowed shadow-lg shadow-emerald-600/20"
              >
                <div className="flex items-center justify-center gap-3">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
                  </svg>
                  CHECK IN
                </div>
              </button>
              <button
                onClick={() => handleAttendance('CHECK_OUT')}
                disabled={isProcessing || !isStreaming}
                className="py-5 rounded-2xl font-bold text-lg transition-all bg-orange-600 hover:bg-orange-500 disabled:bg-gray-800 disabled:text-gray-500 disabled:cursor-not-allowed shadow-lg shadow-orange-600/20"
              >
                <div className="flex items-center justify-center gap-3">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  CHECK OUT
                </div>
              </button>
            </div>

            {/* Result */}
            {result && (
              <div className={`rounded-2xl p-5 border ${result.type === 'success' ? 'bg-emerald-950/50 border-emerald-700/50' : 'bg-red-950/50 border-red-700/50'}`}>
                <div className="flex items-start gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${result.type === 'success' ? 'bg-emerald-600' : 'bg-red-600'}`}>
                    {result.type === 'success' ? (
                      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                    ) : (
                      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <p className="font-bold text-lg">{result.message}</p>
                      <button onClick={resetState} className="text-gray-500 hover:text-white transition-colors">
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                      </button>
                    </div>

                    <div className="mt-2 flex flex-wrap gap-2 text-sm text-gray-300">
                      {result.type === 'success' && (
                        <>
                          <span className="bg-gray-800/80 px-3 py-1 rounded-lg border border-gray-700/50">{result.employee_code}</span>
                          <span className="bg-gray-800/80 px-3 py-1 rounded-lg border border-gray-700/50">
                            {result.action === 'CHECK_IN' ? '🟢 In' : '🟠 Out'}
                          </span>
                        </>
                      )}
                      {result.confidence != null && (
                        <span className="bg-blue-900/30 text-blue-300 border border-blue-500/30 px-3 py-1 rounded-lg">
                          Similarity: {(result.confidence * 100).toFixed(1)}%
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {error && (
              <div className="rounded-2xl p-4 bg-red-950/50 border border-red-700/50 flex items-center gap-3">
                <svg className="w-5 h-5 text-red-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <p className="text-red-300 text-sm">{error}</p>
              </div>
            )}
          </div>

          {/* RIGHT — Stats + Activity */}
          <div className="space-y-5">
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-blue-400">{todayLogs.length}</div>
                <div className="text-xs text-gray-500 mt-1">Total</div>
              </div>
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-emerald-400">{checkedInCount}</div>
                <div className="text-xs text-gray-500 mt-1">In</div>
              </div>
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-orange-400">{checkedOutCount}</div>
                <div className="text-xs text-gray-500 mt-1">Out</div>
              </div>
            </div>

            <div className="bg-gray-900 border border-gray-800 rounded-2xl">
              <div className="p-4 border-b border-gray-800 flex items-center justify-between">
                <h3 className="font-semibold text-sm">Today's Activity</h3>
                <button onClick={fetchTodayLogs} className="text-xs text-blue-400 hover:text-blue-300">Refresh</button>
              </div>
              <div className="max-h-[500px] overflow-y-auto">
                {loadingLogs ? (
                  <div className="p-8 text-center text-gray-500 text-sm">Loading...</div>
                ) : todayLogs.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    <p className="text-sm">No attendance today</p>
                  </div>
                ) : (
                  <div className="divide-y divide-gray-800/50">
                    {todayLogs.map((log, i) => (
                      <div key={i} className="px-4 py-3 hover:bg-gray-800/30">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-gray-800 flex items-center justify-center text-xs font-bold text-gray-400">
                              {log.employee_name?.charAt(0)?.toUpperCase() || '?'}
                            </div>
                            <div>
                              <p className="text-sm font-medium">{log.employee_name}</p>
                              <p className="text-xs text-gray-500">{log.employee_code}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            {log.checked_in && (
                              <div className="flex items-center gap-1.5 text-xs">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                                <span className="text-gray-400">In:</span>
                                <span className="text-emerald-400 font-mono">{fmt(log.check_in_time)}</span>
                              </div>
                            )}
                            {log.checked_out && (
                              <div className="flex items-center gap-1.5 text-xs mt-0.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-orange-500" />
                                <span className="text-gray-400">Out:</span>
                                <span className="text-orange-400 font-mono">{fmt(log.check_out_time)}</span>
                              </div>
                            )}
                            {!log.checked_in && !log.checked_out && <span className="text-xs text-gray-600">Absent</span>}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="bg-gray-900/50 border border-gray-800/50 rounded-2xl p-4">
              <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">How to use</h4>
              <div className="space-y-2 text-xs text-gray-500">
                <div className="flex gap-2"><span className="text-blue-400 font-bold">1.</span><span>Look at the camera</span></div>
                <div className="flex gap-2"><span className="text-blue-400 font-bold">2.</span><span>Click <span className="text-emerald-400">CHECK IN</span> when arriving</span></div>
                <div className="flex gap-2"><span className="text-blue-400 font-bold">3.</span><span>Click <span className="text-orange-400">CHECK OUT</span> when leaving</span></div>
                <div className="flex gap-2"><span className="text-blue-400 font-bold">4.</span><span>System verifies face + <span className="text-blue-400">blink/nod/smile</span></span></div>
              </div>
              <div className="mt-3 pt-3 border-t border-gray-800/50">
                <div className="flex items-center gap-2 text-xs text-emerald-400/70">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  <span>Multi-factor Liveness: Active + Passive checks enabled</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
