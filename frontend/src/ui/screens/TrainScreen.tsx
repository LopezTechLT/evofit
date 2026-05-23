import React from 'react'
import { motion } from 'framer-motion'
import { api, type RoutineDetail, type WeeklyProgressPoint } from '../../lib/api'
import { formatMMSS } from '../../lib/time'
import { GlassCard } from '../components/GlassCard'
import { ProgressBar } from '../components/ProgressBar'
import { Skeleton } from '../components/Skeleton'
import { Confetti } from '../components/Confetti'

type Phase = 'ready' | 'working' | 'rest' | 'done'

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
    if (!props.routineId || finished) return
    const t = window.setInterval(() => setTotalSeconds((v) => v + 1), 1000)
    return () => window.clearInterval(t)
  }, [props.routineId, finished])

  // Rest countdown
  React.useEffect(() => {
    if (phase !== 'rest' || finished) return
    if (restSecondsLeft <= 0) {
      setPhase('ready')
      return
    }
    const t = window.setInterval(() => setRestSecondsLeft((v) => v - 1), 1000)
    return () => window.clearInterval(t)
  }, [phase, restSecondsLeft, finished])

  // Persist state every 3s
  React.useEffect(() => {
    if (!routine || !sessionId || finished || finishing) return
    const t = window.setInterval(() => {
      saveState({ routineId: props.routineId!, sessionId, routine, idx, exercises, totalSeconds, phase, restSecondsLeft, startedAt: new Date().toISOString() })
    }, 3000)
    return () => window.clearInterval(t)
  }, [routine, sessionId, idx, exercises, totalSeconds, phase, restSecondsLeft, finished, finishing, props.routineId])

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

  function tapRep() {
    if (!currentEx || !exState || phase === 'rest') return
    setExercises((prev) => {
      const next = [...prev]
      const s = { ...next[idx] }
      if (s.repsDone < currentEx.reps) {
        s.repsDone += 1
      }
      if (s.repsDone >= currentEx.reps) {
        // Set completed
        if (s.currentSet + 1 >= currentEx.sets) {
          s.setsDone = true
          s.currentSet = currentEx.sets
          // Move to next exercise after brief delay
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
        s.repsDone = 0
      }
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
    } catch {
      setError('Error al finalizar. Intenta de nuevo.')
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
    const text = `🔥 Acabo de completar "${routine?.name ?? 'mi entrenamiento'}" en EVOFIT\n\n⏱ ${result.minutes} min · ${result.kcal} kcal\n⭐ +${result.xp} XP · Nivel ${result.level} · Racha ${result.streak} días\n\n¡Únete al reto!`
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
              <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.2, type: 'spring', stiffness: 200 }} className="text-5xl mb-3">⚠️</motion.div>
            ) : (
              <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.2, type: 'spring', stiffness: 200 }} className="text-5xl mb-3">💪</motion.div>
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
                <span className="font-semibold text-emerald-700">🔥 Nuevo récord personal!</span>
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

  // === MAIN WORKOUT SCREEN ===
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="text-lg font-semibold text-gray-900">{routine?.name ?? 'Entrenar'}</div>
        <div className="flex gap-2">
          <button onClick={() => setMuted((m) => !m)} className="rounded-2xl border border-gray-200 bg-white px-3 py-2 text-xs text-gray-600 hover:bg-gray-50 shadow-sm">
            Sonido: {muted ? 'Off' : 'On'}
          </button>
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
      <GlassCard className="p-4">
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
                <div className="text-sm font-semibold text-emerald-700">✅ Ejercicio completado</div>
                {!isLastExercise && (
                  <button onClick={nextExercise} className="mt-2 rounded-xl bg-gray-900 px-4 py-2 text-xs font-semibold text-white hover:bg-gray-800">
                    Siguiente ejercicio
                  </button>
                )}
              </div>
            ) : (
              /* Working - tap to count reps */
              <motion.button
                whileTap={{ scale: 0.95 }}
                onTap={tapRep}
                className="w-full rounded-2xl bg-gray-900 py-8 text-center text-white hover:bg-gray-800 active:bg-gray-700 select-none"
              >
                <div className="text-4xl font-bold tabular-nums">
                  {exState?.repsDone ?? 0}
                </div>
                <div className="mt-1 text-sm text-gray-300">
                  toca por cada repetición ({currentEx?.reps ?? 0})
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
              <div className="text-sm font-semibold text-emerald-700">🎉 Todos los ejercicios completados</div>
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
