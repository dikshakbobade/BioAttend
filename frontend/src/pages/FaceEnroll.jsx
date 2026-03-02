import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Camera, CheckCircle, XCircle, Loader2, ChevronRight,
  UserCheck, RefreshCw, AlertCircle, Info, AlertTriangle
} from 'lucide-react';
import api, { employeeApi } from '../services/api';

const ENROLL_STEPS = [
  { id: 'front', label: 'Front View',  instruction: 'Look directly at the camera with a neutral expression.' },
  { id: 'left',  label: 'Left Angle',  instruction: 'Turn your head slightly to the left (~30 degrees).'    },
  { id: 'right', label: 'Right Angle', instruction: 'Turn your head slightly to the right (~30 degrees).'   },
];

function FaceEnroll() {
  const { id: employeeId } = useParams();
  const navigate = useNavigate();

  const videoRef      = useRef(null);
  const canvasRef     = useRef(null);
  const streamRef     = useRef(null);
  const lastDetectRef = useRef(0);
  const detectingRef  = useRef(false);

  const [images, setImages]                 = useState({ front: null, left: null, right: null });
  const [currentStepIdx, setCurrentStepIdx] = useState(0);
  const [isReviewMode, setIsReviewMode]     = useState(false);
  const [loading, setLoading]               = useState(false);
  const [cameraError, setCameraError]       = useState('');
  const [submitError, setSubmitError]       = useState('');

  const [quality, setQuality] = useState({
    detected:   false,
    isCentered: false,
    brightness: 100,
    label:      'Checking…',
    faces:      [],
  });

  /* ── CAMERA INIT ──────────────────────────────────── */
  useEffect(() => {
    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
        });
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
      } catch (err) {
        console.error('Camera error:', err);
        setCameraError('Camera access denied or not available. Please allow camera permissions.');
      }
    };
    startCamera();
    return () => {
      if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
    };
  }, []);

  /* ── REAL-TIME QUALITY CHECK (advisory only) ──────── */
  const runDetection = useCallback(async () => {
    if (isReviewMode || images[ENROLL_STEPS[currentStepIdx].id] || !videoRef.current || detectingRef.current) return;
    const now = Date.now();
    if (now - lastDetectRef.current < 800) return;
    lastDetectRef.current = now;
    detectingRef.current  = true;

    try {
      const canvas = document.createElement('canvas');
      canvas.width = 320; canvas.height = 240;
      canvas.getContext('2d').drawImage(videoRef.current, 0, 0, 320, 240);
      const b64 = canvas.toDataURL('image/jpeg', 0.6).split(',')[1];

      // ✅ FIX 1: Only call /verification/detect — removed dead biometricApi.verifyFace call
      const res = await api.post('/verification/detect', { image_base64: b64 });
      const d   = res.data;

      setQuality({
        detected:   d.detected     ?? false,
        isCentered: d.is_centered  ?? false,
        brightness: d.brightness   ?? 100,
        label:      d.quality_label ?? (d.detected ? 'Good' : 'Poor'),
        faces:      d.faces        ?? [],
      });
    } catch (err) {
      console.warn('Detection skipped:', err?.response?.status ?? err.message);
    } finally {
      detectingRef.current = false;
    }
  }, [isReviewMode, currentStepIdx, images]);

  useEffect(() => {
    const interval = setInterval(runDetection, 800);
    return () => clearInterval(interval);
  }, [runDetection]);

  /* ── CAPTURE ──────────────────────────────────────── */
  const captureCurrentStep = () => {
    if (!videoRef.current || !canvasRef.current) return;

    // ✅ FIX 2: Quality is ADVISORY only — camera button ALWAYS works
    const canvas = canvasRef.current;
    canvas.width = 640; canvas.height = 480;
    canvas.getContext('2d').drawImage(videoRef.current, 0, 0);
    const b64 = canvas.toDataURL('image/jpeg', 0.85).split(',')[1];

    const stepId = ENROLL_STEPS[currentStepIdx].id;
    setImages(prev => ({ ...prev, [stepId]: b64 }));

    if (currentStepIdx < ENROLL_STEPS.length - 1) {
      setCurrentStepIdx(prev => prev + 1);
    } else {
      setIsReviewMode(true);
    }
  };

  const recapture = (stepIdx) => {
    setImages(prev => ({ ...prev, [ENROLL_STEPS[stepIdx].id]: null }));
    setCurrentStepIdx(stepIdx);
    setIsReviewMode(false);
    setSubmitError('');
  };

  /* ── SUBMIT ───────────────────────────────────────── */
  const submitProfile = async () => {
    if (loading) return;
    setLoading(true);
    setSubmitError('');
    try {
      await employeeApi.enrollFaceProfile(employeeId, {
        front_image: images.front,
        left_image:  images.left,
        right_image: images.right,
      });
      navigate(`/employees/${employeeId}`);
    } catch (err) {
      setSubmitError(
        err?.response?.data?.detail ||
        'Enrollment failed. Ensure the same person appears in all 3 shots with good lighting.'
      );
    } finally {
      setLoading(false);
    }
  };

  /* ── DERIVED ──────────────────────────────────────── */
  const currentStep = ENROLL_STEPS[currentStepIdx];
  const doneCount   = Object.values(images).filter(Boolean).length;
  const qualityGood = quality.label === 'Good';
  const hasWarnings = !quality.detected || quality.brightness < 40 || !quality.isCentered;

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">

      {/* Header */}
      <div className="flex justify-between items-end border-b border-gray-200 dark:border-slate-700 pb-6">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-800 dark:text-white tracking-tight">
            Enterprise Face Enrollment
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
            High-quality biometric template generation for Employee {employeeId}
          </p>
        </div>
        {!isReviewMode && (
          <div className="flex gap-4">
            {ENROLL_STEPS.map((s, idx) => (
              <div key={s.id} className="flex flex-col items-center gap-2">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold border-2 transition-all
                  ${images[s.id]
                    ? 'bg-green-500 border-green-500 text-white'
                    : idx === currentStepIdx
                      ? 'bg-blue-600 border-blue-600 text-white ring-4 ring-blue-100 dark:ring-blue-900'
                      : 'bg-slate-100 dark:bg-slate-700 border-slate-200 dark:border-slate-600 text-slate-400'}`}>
                  {images[s.id] ? <CheckCircle className="w-5 h-5" /> : idx + 1}
                </div>
                <span className={`text-[10px] font-bold uppercase tracking-wider
                  ${idx === currentStepIdx ? 'text-blue-600 dark:text-blue-400' : 'text-slate-400'}`}>
                  {s.label.split(' ')[0]}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="grid lg:grid-cols-12 gap-8">

        {/* ── Camera / Review ── */}
        <div className="lg:col-span-8 space-y-4">

          {cameraError && (
            <div className="flex items-center gap-3 px-4 py-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-xl text-red-600 dark:text-red-400 text-sm">
              <XCircle className="w-5 h-5 flex-shrink-0" /> {cameraError}
            </div>
          )}

          {!isReviewMode ? (
            <div className="relative aspect-video bg-slate-900 rounded-[32px] overflow-hidden shadow-2xl border-4 border-slate-800">
              <video ref={videoRef} autoPlay muted playsInline className="w-full h-full object-cover scale-x-[-1]" />

              {/* Face guide oval */}
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className={`w-64 h-80 border-4 border-dashed rounded-[120px] transition-all duration-300 mb-6
                  ${qualityGood ? 'border-green-400 bg-green-400/5 shadow-[0_0_40px_rgba(74,222,128,0.15)]' : 'border-white/30'}`}>
                  {currentStepIdx === 1 && (
                    <div className="absolute -left-16 top-1/2 -translate-y-1/2 flex flex-col items-center text-blue-400 animate-pulse">
                      <ChevronRight className="w-10 h-10 rotate-180" />
                      <span className="text-[9px] font-bold mt-1">TURN LEFT</span>
                    </div>
                  )}
                  {currentStepIdx === 2 && (
                    <div className="absolute -right-16 top-1/2 -translate-y-1/2 flex flex-col items-center text-blue-400 animate-pulse">
                      <ChevronRight className="w-10 h-10" />
                      <span className="text-[9px] font-bold mt-1">TURN RIGHT</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Quality badges */}
              <div className="absolute top-5 left-5 flex flex-col gap-2">
                <div className={`px-3 py-1.5 rounded-full text-xs font-black uppercase tracking-widest flex items-center gap-2 backdrop-blur-md border
                  ${qualityGood ? 'bg-green-500/80 text-white border-green-400' : 'bg-red-500/80 text-white border-red-400'}`}>
                  <div className={`w-2 h-2 rounded-full animate-pulse ${qualityGood ? 'bg-white' : 'bg-white/60'}`} />
                  Quality: {quality.label}
                </div>
                {quality.brightness < 40 && (
                  <div className="bg-amber-500/90 text-white px-3 py-1 rounded-full text-[10px] font-bold flex items-center gap-1.5 backdrop-blur-md border border-amber-400">
                    <AlertCircle className="w-3 h-3" /> LIGHT TOO DARK
                  </div>
                )}
                {!quality.isCentered && quality.detected && (
                  <div className="bg-slate-800/80 text-white px-3 py-1 rounded-full text-[10px] font-bold flex items-center gap-1.5 backdrop-blur-md border border-slate-600">
                    <RefreshCw className="w-3 h-3" /> CENTER YOUR FACE
                  </div>
                )}
                {!quality.detected && quality.label !== 'Checking…' && (
                  <div className="bg-orange-500/90 text-white px-3 py-1 rounded-full text-[10px] font-bold flex items-center gap-1.5 backdrop-blur-md border border-orange-400">
                    <AlertTriangle className="w-3 h-3" /> NO FACE DETECTED
                  </div>
                )}
              </div>

              {/* Bottom bar */}
              <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-black/80 via-black/40 to-transparent">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <span className="text-blue-400 text-xs font-bold uppercase tracking-widest">
                      Step {currentStepIdx + 1} of 3
                    </span>
                    <p className="text-white text-lg font-bold mt-0.5 leading-snug">{currentStep.instruction}</p>
                    {/* Advisory message only — never blocks capture */}
                    {hasWarnings && quality.label !== 'Checking…' && (
                      <p className="text-amber-300 text-xs mt-1 flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                        Poor quality detected — you can still capture, results may vary
                      </p>
                    )}
                  </div>

                  {/* ✅ Camera button ALWAYS enabled */}
                  <button
                    onClick={captureCurrentStep}
                    className={`h-16 w-16 rounded-full flex items-center justify-center transition-all shadow-xl flex-shrink-0
                      ${qualityGood
                        ? 'bg-blue-600 text-white hover:bg-blue-500 hover:scale-110 active:scale-95 ring-4 ring-blue-400/40'
                        : 'bg-amber-500 text-white hover:bg-amber-400 hover:scale-110 active:scale-95'}`}
                    title={qualityGood ? 'Capture photo' : 'Capture anyway (low quality)'}
                  >
                    <Camera className="w-7 h-7" />
                  </button>
                </div>
              </div>
            </div>

          ) : (
            /* Review grid */
            <div className="bg-slate-50 dark:bg-slate-900 rounded-[32px] p-8 border-2 border-dashed border-slate-200 dark:border-slate-700 min-h-[400px] flex flex-col items-center justify-center">
              <div className="text-center mb-8">
                <div className="inline-flex p-3 bg-blue-100 dark:bg-blue-900/40 rounded-2xl mb-3">
                  <UserCheck className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                </div>
                <h2 className="text-2xl font-black text-slate-800 dark:text-white">Profile Ready for Enrollment</h2>
                <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Review all 3 angles — hover to recapture any shot</p>
              </div>

              <div className="grid grid-cols-3 gap-5 w-full max-w-2xl">
                {ENROLL_STEPS.map((s, idx) => (
                  <div key={s.id} className="relative group">
                    <div className="aspect-[3/4] rounded-2xl overflow-hidden border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm">
                      {images[s.id] && (
                        <img src={`data:image/jpeg;base64,${images[s.id]}`} alt={s.label} className="w-full h-full object-cover" />
                      )}
                      <div className="absolute bottom-2 left-2 right-2 py-1 bg-black/50 backdrop-blur-sm rounded-lg text-[9px] text-white font-bold text-center uppercase tracking-widest">
                        {s.label}
                      </div>
                    </div>
                    <button
                      onClick={() => recapture(idx)}
                      className="absolute -top-3 -right-3 p-2 bg-slate-800 text-white rounded-xl opacity-0 group-hover:opacity-100 transition-all hover:bg-red-500 shadow-xl"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>

              {submitError && (
                <div className="mt-6 w-full max-w-2xl flex items-start gap-3 px-4 py-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-xl text-red-600 dark:text-red-400 text-sm">
                  <XCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold">Enrollment Failed</p>
                    <p className="mt-0.5 text-xs">{submitError}</p>
                    <p className="mt-1 text-xs opacity-75">Tip: Ensure good lighting and the same person in all 3 shots. Try recapturing.</p>
                  </div>
                </div>
              )}

              <div className="mt-8 flex gap-4">
                <button
                  onClick={submitProfile}
                  disabled={loading}
                  className="px-10 py-4 bg-green-600 hover:bg-green-500 text-white rounded-2xl font-black text-base shadow-xl shadow-green-600/20 flex items-center gap-3 disabled:opacity-60 transition-all"
                >
                  {loading ? <><Loader2 className="w-5 h-5 animate-spin" /> Enrolling…</> : <><CheckCircle className="w-5 h-5" /> Confirm Enrollment</>}
                </button>
                <button
                  onClick={() => { setIsReviewMode(false); setSubmitError(''); }}
                  className="px-8 py-4 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-2 border-slate-200 dark:border-slate-700 rounded-2xl font-bold hover:bg-slate-50 dark:hover:bg-slate-700 transition-all"
                >
                  Back to Camera
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ── Right panel ── */}
        <div className="lg:col-span-4 space-y-5">
          <div className="bg-white dark:bg-slate-800 rounded-2xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm">
            <h3 className="font-bold text-slate-800 dark:text-white flex items-center gap-2 mb-4">
              <Info className="w-4 h-4 text-blue-500" /> Tips for High Accuracy
            </h3>
            <div className="space-y-3">
              {[
                'Stand 2–3 feet away from camera',
                'Ensure face is neutral (no smiling)',
                'Avoid wearing hats or dark glasses',
                'Maintain consistent lighting for all 3 shots',
                'Camera button turns amber when quality is low — you can still capture',
              ].map((tip, i) => (
                <div key={i} className="flex gap-2.5 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                  <div className="mt-2 w-1.5 h-1.5 rounded-full bg-blue-300 dark:bg-blue-600 shrink-0" />
                  {tip}
                </div>
              ))}
            </div>
          </div>

          {/* Progress */}
          <div className="bg-slate-50 dark:bg-slate-800/50 rounded-2xl p-6 border border-slate-200 dark:border-slate-700">
            <div className="flex justify-between items-center mb-3">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Enrollment Status</span>
              <span className="text-xs font-black text-blue-600 dark:text-blue-400">{doneCount} / 3 DONE</span>
            </div>
            <div className="h-2.5 w-full bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <div className="h-full bg-blue-600 rounded-full transition-all duration-700 ease-out" style={{ width: `${(doneCount / 3) * 100}%` }} />
            </div>
            <div className="mt-4 space-y-2">
              {ENROLL_STEPS.map((s, i) => (
                <div key={s.id} className="flex items-center gap-2 text-xs">
                  {images[s.id]
                    ? <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
                    : i === currentStepIdx && !isReviewMode
                      ? <div className="w-4 h-4 rounded-full border-2 border-blue-500 flex items-center justify-center flex-shrink-0">
                          <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                        </div>
                      : <div className="w-4 h-4 rounded-full border-2 border-slate-300 dark:border-slate-600 flex-shrink-0" />
                  }
                  <span className={`font-medium ${images[s.id] ? 'text-green-600 dark:text-green-400' : i === currentStepIdx && !isReviewMode ? 'text-blue-600 dark:text-blue-400' : 'text-slate-400'}`}>
                    {s.label} {images[s.id] && '✓'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={() => navigate('/employees')}
            className="w-full py-3 text-slate-500 dark:text-slate-400 font-bold hover:text-slate-800 dark:hover:text-slate-100 transition-all border-2 border-transparent hover:border-slate-200 dark:hover:border-slate-700 rounded-xl text-sm"
          >
            Cancel Enrollment
          </button>
        </div>
      </div>

      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}

export default FaceEnroll;