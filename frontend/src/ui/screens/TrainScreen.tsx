import React from 'react'
import { motion } from 'framer-motion'
import { Play, Pause } from 'lucide-react'
import { api, type RoutineDetail, type WeeklyProgressPoint } from '../../lib/api'
import { formatMMSS } from '../../lib/time'
import { GlassCard } from '../components/GlassCard'
import { ProgressBar } from '../components/ProgressBar'
import { Skeleton } from '../components/Skeleton'
import { Confetti } from '../components/Confetti'

type Phase = 'pregame' | 'ready' | 'working' | 'rest' | 'done'

type ExerciseState = {
  /** current set index (0-based) */
  currentSet: number
  /** reps completed in current set */
  repsDone: number
  /** all sets completed */
  setsDone: boolean
}

const STORAGE_KEY = 'evofit_workout_state'

type SavedState = {
  routineId: number
  sessionId: number
  routine: RoutineDetail
  idx: number
  exercises: ExerciseState[]
  totalSeconds: number
  phase: Phase
  restSecondsLeft: number
  startedAt: string
  paused: boolean
}

function saveState(s: SavedState) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(s)) } catch {}
}
function loadState(): SavedState | null {
  try { const r = localStorage.getItem(STORAGE_KEY); return r ? JSON.parse(r) : null } catch { return null }
}
function clearState() {
  try { localStorage.removeItem(STORAGE_KEY) } catch {}
}

function initExerciseStates(routine: RoutineDetail): ExerciseState[] {
  return routine.exercises.map(() => ({ currentSet: 0, repsDone: 0, setsDone: false }))
}

function allExercisesDone(states: ExerciseState[]): boolean {
  return states.every((s) => s.setsDone)
}

export function TrainScreen(props: { routineId: number | null; onFinish?: () => void }) {
  const [routine, setRoutine] = React.useState<RoutineDetail | null>(null)
  const [sessionId, setSessionId] = React.useState<number | null>(null)
  const [idx, setIdx] = React.useState(0)
  const [exercises, setExercises] = React.useState<ExerciseState[]>([])
  const [phase, setPhase] = React.useState<Phase>('ready')
  const [restSecondsLeft, setRestSecondsLeft] = React.useState(0)
  const [totalSeconds, setTotalSeconds] = React.useState(0)
  const [muted, setMuted] = React.useState(true)
  const [finished, setFinished] = React.useState(false)
  const [finishing, setFinishing] = React.useState(false)
  const [result, setResult] = React.useState<{ xp: number; level: number; streak: number; title: string; kcal: number; minutes: number; incomplete: boolean } | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [prevSession, setPrevSession] = React.useState<WeeklyProgressPoint | null>(null)
  const [showExitConfirm, setShowExitConfirm] = React.useState(false)
  const [started, setStarted] = React.useState(false)
  const [paused, setPaused] = React.useState(false)

  // Restore saved state
  React.useEffect(() => {
    const saved = loadState()
    if (saved && saved.routineId === props.routineId && saved.sessionId) {
      setRoutine(saved.routine)
      setSessionId(saved.sessionId)
      setIdx(saved.idx)
      setExercises(saved.exercises)
      setTotalSeconds(saved.totalSeconds)
      setPhase(saved.phase)
      setRestSecondsLeft(saved.restSecondsLeft)
      setStarted(true)
      if (saved.paused) setPaused(true)
    }
  }, [props.routineId])

  // Init new workout
  React.useEffect(() => {
    if (!props.routineId) return
    const saved = loadState()
    if (saved && saved.routineId === props.routineId && saved.sessionId) return
    let alive = true
    setError(null)
    setFinished(false)
    setResult(null)
    setFinishing(false)
    setShowExitConfirm(false)
    setSessionId(null)
    setTotalSeconds(0)
    setPhase('ready')
    api
      .routine(props.routineId)
      .then((r) => {
        if (!alive) return
        setRoutine(r)
        setIdx(0)
        setExercises(initExerciseStates(r))
      })
      .catch(() => setRoutine(null))
    api
      .startWorkout(props.routineId)
      .then((s) => alive && setSessionId(s.sessionId))
      .catch(() => alive && setError('No se pudo iniciar la sesión.'))
    return () => { alive = false }
  }, [props.routineId])

  // Global timer
  React.useEffect(() => {
    if (!props.routineId || finished || !started || paused) return
    const t = window.setInterval(() => setTotalSeconds((v) => v + 1), 1000)
    return () => window.clearInterval(t)
  }, [props.routineId, finished, started, paused])

  // Rest countdown
  React.useEffect(() => {
    if (phase !== 'rest' || finished || paused) return
    if (restSecondsLeft <= 0) {
      setPhase('ready')
      return
    }
    const t = window.setInterval(() => setRestSecondsLeft((v) => v - 1), 1000)
    return () => window.clearInterval(t)
  }, [phase, restSecondsLeft, finished, paused])

  // Persist state every 3s
  React.useEffect(() => {
    if (!routine || !sessionId || finished || finishing) return
    const t = window.setInterval(() => {
      saveState({ routineId: props.routineId!, sessionId, routine, idx, exercises, totalSeconds, phase, restSecondsLeft, startedAt: new Date().toISOString(), paused })
    }, 3000)
    return () => window.clearInterval(t)
  }, [routine, sessionId, idx, exercises, totalSeconds, phase, restSecondsLeft, finished, finishing, props.routineId, paused])

  // Fetch prev session for comparison
  React.useEffect(() => {
    if (!finished) return
    api.weeklyProgress().then((d) => {
      const items = d.items
      if (items.length > 1) setPrevSession(items[items.length - 2])
    }).catch(() => {})
  }, [finished])

  const currentEx = routine?.exercises[idx]
  const exState = exercises[idx]
  const isLastExercise = routine && idx >= routine.exercises.length - 1
  const allDone = allExercisesDone(exercises)
  const overallProgress = routine ? exercises.reduce((sum, s, i) => {
    const totalSets = routine.exercises[i]?.sets ?? 1
    const doneSets = s.setsDone ? totalSets : s.currentSet
    return sum + doneSets
  }, 0) / routine.exercises.reduce((sum, e) => sum + e.sets, 0) : 0

  function completeSet() {
    if (!currentEx || !exState || phase === 'rest' || paused) return
    setExercises((prev) => {
      const next = [...prev]
      const s = { ...next[idx] }
      if (s.currentSet + 1 >= currentEx.sets) {
        s.setsDone = true
        s.currentSet = currentEx.sets
        if (isLastExercise) {
          setPhase('done')
        } else {
          setPhase('rest')
          setRestSecondsLeft(currentEx.restSeconds || 60)
        }
      } else {
        s.currentSet += 1
        setPhase('rest')
        setRestSecondsLeft(currentEx.restSeconds || 60)
      }
      ping(muted)
      next[idx] = s
      return next
    })
  }

  function skipRest() {
    setRestSecondsLeft(0)
    setPhase('ready')
  }

  function nextExercise() {
    if (!routine || idx >= routine.exercises.length - 1) return
    setIdx((v) => v + 1)
    setPhase('ready')
  }

  function prevExercise() {
    if (idx <= 0) return
    setIdx((v) => v - 1)
    setPhase('ready')
  }

  async function finish(incomplete = false) {
    if (finishing) return
    if (!sessionId) return
    const kcal = Math.floor(totalSeconds / 60) * 6
    const xpMultiplier = incomplete ? 0.5 : 1
    try {
      setFinishing(true)
      const res = await api.finishWorkout(sessionId, totalSeconds, kcal)
      clearState()
      setFinished(true)
      setResult({
        xp: Math.round(res.xpGained * xpMultiplier),
        level: res.level,
        streak: res.streakDays,
        title: res.title,
        kcal,
        minutes: Math.floor(totalSeconds / 60),
        incomplete,
      })
    } catch (e) {
      setError(`Error al finalizar: ${e instanceof Error ? e.message : 'desconocido'}`)
    } finally {
      setFinishing(false)
    }
  }

  function goBack() {
    clearState()
    if (props.onFinish) props.onFinish()
  }

  async function handleShare() {
    if (!result) return
    const text = `Acabo de completar "${routine?.name ?? 'mi entrenamiento'}" en EVOFIT\n\n${result.minutes} min · ${result.kcal} kcal\n+${result.xp} XP · Nivel ${result.level} · Racha ${result.streak} dias`
    try { await navigator.clipboard.writeText(text) } catch {}
  }

  if (error) {
    return (
      <GlassCard className="p-4">
        <div className="text-sm text-gray-600">{error}</div>
        <button onClick={goBack} className="mt-3 rounded-2xl bg-gray-900 px-4 py-2 text-sm font-semibold text-white">Volver</button>
      </GlassCard>
    )
  }

  // === SUMMARY SCREEN ===
  if (finished && result) {
    const betterKcal = prevSession && result.kcal > (prevSession.kcal || 0)
    const betterMinutes = prevSession && result.minutes > (prevSession.minutes || 0)
    return (
      <>
        {!result.incomplete && <Confetti />}
        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.4 }} className="space-y-4">
          <GlassCard className="p-6 text-center">
            {result.incomplete ? (
              <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.2, type: 'spring', stiffness: 200 }} className="text-5xl mb-3 text-amber-500">!</motion.div>
            ) : (
              <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.2, type: 'spring', stiffness: 200 }} className="text-5xl mb-3 text-emerald-500">+</motion.div>
            )}
            <div className="text-xl font-bold text-gray-900">{result.incomplete ? 'Rutina incompleta' : '¡Entrenamiento completado!'}</div>
            <div className="mt-1 text-sm text-gray-500">{routine?.name}</div>

            {result.incomplete && (
              <div className="mt-3 rounded-2xl bg-amber-50 border border-amber-200 p-3 text-sm text-amber-700">
                No completaste todos los ejercicios. Recibiste el <strong>50% del XP</strong>.
              </div>
            )}

            <div className="mt-5 grid grid-cols-3 gap-3">
              <StatBadge label="Duración" value={formatMMSS(totalSeconds)} />
              <StatBadge label="Calorías" value={`${result.kcal}`} />
              <StatBadge label="Ejercicios" value={`${routine?.exercises.length ?? 0}`} />
            </div>

            <div className="mt-4 rounded-2xl bg-gray-900 p-4 text-white">
              <div className="text-2xl font-bold">+{result.xp} XP</div>
              <div className="mt-1 text-xs text-gray-300">Nivel {result.level} · Racha {result.streak} días</div>
              <div className="text-xs text-gray-400">{result.title}</div>
            </div>

            {prevSession && (betterKcal || betterMinutes) && !result.incomplete && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="mt-3 rounded-2xl bg-emerald-50 border border-emerald-200 p-3 text-sm">
                <span className="font-semibold text-emerald-700">Nuevo record personal!</span>
                <div className="text-emerald-600">
                  {betterMinutes && `+${result.minutes - (prevSession.minutes || 0)} min · `}
                  {betterKcal && `+${result.kcal - (prevSession.kcal || 0)} kcal vs última sesión`}
                </div>
              </motion.div>
            )}

            <div className="mt-5 flex gap-2">
              <button onClick={goBack} className="flex-1 rounded-2xl bg-gray-900 px-4 py-2 text-sm font-semibold text-white hover:bg-gray-800">Ver perfil</button>
              <button onClick={handleShare} className="rounded-2xl border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50">Compartir</button>
            </div>
          </GlassCard>
        </motion.div>
      </>
    )
  }

  // === EXIT CONFIRMATION ===
  if (showExitConfirm) {
    const complete = allExercisesDone(exercises)
    return (
      <GlassCard className="p-4 text-center">
        <div className="text-lg font-semibold text-gray-900 mb-2">¿Finalizar entrenamiento?</div>
        {!complete && (
          <div className="text-sm text-amber-600 mb-3">
            No has completado todos los ejercicios. Recibirás <strong>la mitad del XP</strong>.
          </div>
        )}
        <div className="flex gap-2">
          <button onClick={() => setShowExitConfirm(false)} className="flex-1 rounded-2xl border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700">Seguir</button>
          <button onClick={() => finish(!complete)} disabled={finishing} className="flex-1 rounded-2xl bg-gray-900 px-4 py-2 text-sm font-semibold text-white hover:bg-gray-800 disabled:opacity-60">
            {finishing ? 'Finalizando…' : complete ? 'Finalizar' : 'Finalizar incompleto'}
          </button>
        </div>
      </GlassCard>
    )
  }

  // === PREGAME (start screen) ===
  if (!started && routine) {
    return (
      <div className="space-y-4">
        <GlassCard className="p-8 text-center">
          <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', stiffness: 200, delay: 0.1 }} className="text-5xl mb-4 text-gray-300">=</motion.div>
          <div className="text-2xl font-bold text-gray-900">{routine.name}</div>
          <div className="mt-2 text-sm text-gray-500">{routine.exercises.length} ejercicios · {routine.exercises.reduce((s, e) => s + e.sets, 0)} series totales</div>
          <div className="mt-6 space-y-2 text-sm text-gray-600">
            {routine.exercises.map((e, i) => (
              <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 + i * 0.05 }} className="flex justify-between rounded-2xl bg-gray-50 border border-gray-200 px-4 py-2.5">
                <span className="font-medium text-gray-800">{e.name}</span>
                <span className="text-gray-400 tabular-nums">{e.sets} × {e.reps}</span>
              </motion.div>
            ))}
          </div>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setStarted(true)}
            className="mt-6 w-full rounded-2xl bg-gray-900 py-3.5 text-base font-bold text-white hover:bg-gray-800 transition-all"
          >
            Comenzar
          </motion.button>
        </GlassCard>
      </div>
    )
  }

  // === MAIN WORKOUT SCREEN ===
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="text-lg font-semibold text-gray-900">{routine?.name ?? 'Entrenar'}</div>
        <div className="flex items-center gap-2">
          <motion.button
            layout
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setPaused((p) => !p)}
            className="rounded-full bg-white/80 backdrop-blur-sm border border-gray-200/80 px-4 py-2 text-xs font-semibold text-gray-700 shadow-lg shadow-black/5 hover:bg-white hover:shadow-xl hover:border-gray-300 transition-all flex items-center gap-1.5"
          >
            <span className="text-sm">{paused ? <Play size={16} /> : <Pause size={16} />}</span>
            <span>{paused ? 'Reanudar' : 'Pausar'}</span>
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setMuted((m) => !m)}
            className="rounded-full bg-white/80 backdrop-blur-sm border border-gray-200/80 px-3 py-2 text-xs shadow-lg shadow-black/5 hover:bg-white hover:shadow-xl hover:border-gray-300 transition-all"
          >
            {muted ? '[X]' : '[O]'}
          </motion.button>
        </div>
      </div>

      {/* Overall progress bar */}
      <GlassCard className="p-3">
        <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
          <span>Progreso general</span>
          <span>{Math.round(overallProgress * 100)}%</span>
        </div>
        <ProgressBar value={overallProgress} />
      </GlassCard>

      {/* Current exercise card */}
      {paused && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setPaused(false)}>
          <motion.div initial={{ scale: 0.85, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ type: 'spring', stiffness: 200 }} className="rounded-3xl bg-white px-10 py-8 text-center shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="text-5xl mb-3 text-gray-300"><Pause size={48} className="text-gray-300" /></div>
            <div className="text-xl font-bold text-gray-900">Entrenamiento pausado</div>
            <div className="mt-2 text-sm text-gray-500">Tiempo total: {formatMMSS(totalSeconds)}</div>
            <motion.button whileHover={{ scale: 1.02, boxShadow: '0 0 25px rgba(255,107,53,0.4)' }} whileTap={{ scale: 0.96 }} onClick={() => setPaused(false)} className="mt-5 w-full rounded-full bg-gradient-to-r from-orange-500 via-rose-500 to-pink-500 py-3.5 text-sm font-black text-white tracking-wide shadow-lg shadow-orange-500/30 transition-all duration-300 border border-white/20">
              <Play size={20} className="inline" />  REANUDAR
            </motion.button>
          </motion.div>
        </motion.div>
      )}
      <GlassCard className={`p-4 ${paused ? 'opacity-40 pointer-events-none' : ''}`}>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs uppercase tracking-widest text-gray-400">
              Ejercicio {idx + 1} de {routine?.exercises.length ?? 0}
            </div>
            <div className="mt-1 text-xl font-semibold text-gray-900">{currentEx?.name ?? <Skeleton className="h-6 w-40" />}</div>
            {currentEx?.muscles && currentEx.muscles.length > 0 && (
              <div className="mt-1 flex gap-1 flex-wrap">
                {currentEx.muscles.map((m) => <span key={m} className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] text-gray-600">{m}</span>)}
              </div>
            )}
          </div>
          <div className="text-right">
            <div className="text-xs text-gray-400">Total</div>
            <div className="text-2xl font-semibold tabular-nums text-gray-900">{formatMMSS(totalSeconds)}</div>
          </div>
        </div>

        {/* Target info */}
        {currentEx && exState && (
          <div className="mt-4 grid grid-cols-2 gap-3">
            <div className="rounded-2xl bg-gray-50 border border-gray-200 p-3 text-center">
              <div className="text-xs text-gray-500">Series</div>
              <div className="mt-1 text-lg font-bold text-gray-900">{exState.currentSet + (exState.setsDone ? 0 : 1)}/{currentEx.sets}</div>
            </div>
            <div className="rounded-2xl bg-gray-50 border border-gray-200 p-3 text-center">
              <div className="text-xs text-gray-500">Repes</div>
              <div className="mt-1 text-lg font-bold text-gray-900">{currentEx.reps}</div>
            </div>
          </div>
        )}

        {/* Sets tracker */}
        {currentEx && exState && (
          <div className="mt-3 flex justify-center gap-2">
            {Array.from({ length: currentEx.sets }).map((_, i) => (
              <div key={i} className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition ${
                i < exState.currentSet || (i === exState.currentSet && exState.setsDone)
                  ? 'bg-gray-900 text-white'
                  : i === exState.currentSet
                    ? 'border-2 border-gray-900 bg-white text-gray-900'
                    : 'border border-gray-300 bg-white text-gray-400'
              }`}>
                {i + 1}
              </div>
            ))}
          </div>
        )}

        {/* Phase: ready */}
        {phase === 'ready' && (
          <div className="mt-4">
            {exState?.setsDone ? (
              /* Exercise completed, prompt to move on */
              <div className="rounded-2xl bg-emerald-50 border border-emerald-200 p-4 text-center">
                <div className="text-sm font-semibold text-emerald-700">Ejercicio completado</div>
                {!isLastExercise && (
                  <button onClick={nextExercise} className="mt-2 rounded-xl bg-gray-900 px-4 py-2 text-xs font-semibold text-white hover:bg-gray-800">
                    Siguiente ejercicio
                  </button>
                )}
              </div>
            ) : (
              /* Working - complete set */
              <motion.button
                whileTap={{ scale: 0.95 }}
                onTap={completeSet}
                className="w-full rounded-2xl bg-gradient-to-b from-gray-800 to-gray-900 py-8 text-center text-white shadow-lg shadow-gray-900/30 hover:from-gray-900 hover:to-black active:from-black select-none border border-gray-700"
              >
                <div className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Toca al completar</div>
                <div className="mt-1 text-5xl font-black tabular-nums">
                  {exState?.currentSet !== undefined ? exState.currentSet + 1 : 1}/{currentEx?.sets ?? 0}
                </div>
                <div className="mt-1 text-sm text-gray-400">
                  serie · {currentEx?.reps ?? 0} reps
                </div>
              </motion.button>
            )}
          </div>
        )}

        {/* Phase: rest */}
        {phase === 'rest' && (
          <div className="mt-4">
            <div className="rounded-2xl bg-amber-50 border border-amber-200 p-4 text-center">
              <div className="text-xs text-amber-600 font-semibold">DESCANSO</div>
              <div className="mt-1 text-4xl font-bold tabular-nums text-amber-700">{formatMMSS(restSecondsLeft)}</div>
              <button onClick={skipRest} className="mt-2 text-xs text-amber-600 underline">Saltar descanso</button>
            </div>
          </div>
        )}

        {/* All exercises complete */}
        {allDone && (
          <div className="mt-4">
            <div className="rounded-2xl bg-emerald-50 border border-emerald-200 p-4 text-center">
              <div className="text-sm font-semibold text-emerald-700">Todos los ejercicios completados</div>
              <button onClick={() => finish(false)} disabled={finishing} className="mt-3 w-full rounded-2xl bg-gray-900 px-4 py-2 text-sm font-semibold text-white hover:bg-gray-800">
                {finishing ? 'Finalizando…' : 'Finalizar entrenamiento'}
              </button>
            </div>
          </div>
        )}

        {/* Instructions */}
        {currentEx?.instructions && (
          <div className="mt-3 text-xs text-gray-500 italic">{currentEx.instructions}</div>
        )}

        {/* Navigation + Finish */}
        <div className="mt-4 grid grid-cols-2 gap-2">
          <button onClick={prevExercise} disabled={idx === 0} className="rounded-2xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 shadow-sm disabled:opacity-40">
            Anterior
          </button>
          <button onClick={nextExercise} disabled={!routine || idx >= routine.exercises.length - 1} className="rounded-2xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 shadow-sm disabled:opacity-40">
            Siguiente
          </button>
        </div>

        <button onClick={() => setShowExitConfirm(true)} className="mt-2 w-full rounded-2xl border border-gray-300 bg-gray-100 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-200">
          Finalizar entrenamiento
        </button>
      </GlassCard>
    </div>
  )
}

function StatBadge(props: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-gray-100 p-3">
      <div className="text-lg font-bold text-gray-900">{props.value}</div>
      <div className="text-[11px] text-gray-500">{props.label}</div>
    </div>
  )
}

function ping(muted: boolean) {
  if (muted) return
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
    const o = ctx.createOscillator()
    const g = ctx.createGain()
    o.type = 'sine'
    o.frequency.value = 660
    g.gain.value = 0.035
    o.connect(g)
    g.connect(ctx.destination)
    o.start()
    setTimeout(() => { o.stop(); ctx.close() }, 120)
  } catch {}
}



