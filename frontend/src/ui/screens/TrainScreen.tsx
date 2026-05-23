import React from 'react'
import { motion } from 'framer-motion'
import { api, type RoutineDetail, type WeeklyProgressPoint } from '../../lib/api'
import { formatMMSS } from '../../lib/time'
import { GlassCard } from '../components/GlassCard'
import { ProgressBar } from '../components/ProgressBar'
import { Skeleton } from '../components/Skeleton'
import { Confetti } from '../components/Confetti'

type Phase = 'exercise' | 'rest'

const STORAGE_KEY = 'evofit_workout_state'

type SavedState = {
  routineId: number
  sessionId: number
  routine: RoutineDetail
  phase: Phase
  idx: number
  secondsLeft: number
  totalSeconds: number
  seriesDone: number
  startedAt: string
}

function saveState(s: SavedState) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(s)) } catch {}
}

function loadState(): SavedState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

function clearState() {
  try { localStorage.removeItem(STORAGE_KEY) } catch {}
}

export function TrainScreen(props: { routineId: number | null; onFinish?: () => void }) {
  const [routine, setRoutine] = React.useState<RoutineDetail | null>(null)
  const [sessionId, setSessionId] = React.useState<number | null>(null)
  const [phase, setPhase] = React.useState<Phase>('exercise')
  const [idx, setIdx] = React.useState(0)
  const [secondsLeft, setSecondsLeft] = React.useState(45)
  const [totalSeconds, setTotalSeconds] = React.useState(0)
  const [seriesDone, setSeriesDone] = React.useState(0)
  const [muted, setMuted] = React.useState(true)
  const [finished, setFinished] = React.useState(false)
  const [finishing, setFinishing] = React.useState(false)
  const [result, setResult] = React.useState<{ xp: number; level: number; streak: number; title: string; kcal: number; minutes: number } | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [prevSession, setPrevSession] = React.useState<WeeklyProgressPoint | null>(null)
  const [hasResumed, setHasResumed] = React.useState(false)

  // Try to restore saved state
  React.useEffect(() => {
    const saved = loadState()
    if (saved && saved.routineId === props.routineId && !hasResumed) {
      setHasResumed(true)
      setRoutine(saved.routine)
      setSessionId(saved.sessionId)
      setPhase(saved.phase)
      setIdx(saved.idx)
      setSecondsLeft(saved.secondsLeft)
      setTotalSeconds(saved.totalSeconds)
      setSeriesDone(saved.seriesDone)
    }
  }, [props.routineId])

  React.useEffect(() => {
    if (!props.routineId || hasResumed) return
    let alive = true
    setError(null)
    setFinished(false)
    setResult(null)
    setFinishing(false)
    setSessionId(null)
    setTotalSeconds(0)
    api
      .routine(props.routineId)
      .then((r) => {
        if (!alive) return
        setRoutine(r)
        setIdx(0)
        setPhase('exercise')
        setSeriesDone(0)
        setSecondsLeft(45)
      })
      .catch(() => setRoutine(null))
    api
      .startWorkout(props.routineId)
      .then((s) => alive && setSessionId(s.sessionId))
      .catch(() => alive && setError('No se pudo iniciar la sesión. Intenta de nuevo.'))
    return () => { alive = false }
  }, [props.routineId, hasResumed])

  // Timer tick
  React.useEffect(() => {
    if (!props.routineId || finished) return
    const t = window.setInterval(() => {
      setTotalSeconds((v) => v + 1)
      setSecondsLeft((v) => (v > 0 ? v - 1 : 0))
    }, 1000)
    return () => window.clearInterval(t)
  }, [props.routineId, finished])

  // Persist state every 3s
  React.useEffect(() => {
    if (!routine || !sessionId || finished || finishing) return
    const t = window.setInterval(() => {
      saveState({ routineId: props.routineId!, sessionId, routine, phase, idx, secondsLeft, totalSeconds, seriesDone, startedAt: new Date().toISOString() })
    }, 3000)
    return () => window.clearInterval(t)
  }, [routine, sessionId, phase, idx, secondsLeft, totalSeconds, seriesDone, finished, finishing, props.routineId])

  // Phase transitions
  React.useEffect(() => {
    if (!routine || finished) return
    if (secondsLeft > 0) return
    const current = routine.exercises[idx]
    if (!current) return

    if (phase === 'exercise') {
      setPhase('rest')
      setSecondsLeft(current.restSeconds || 45)
      ping(muted)
      return
    }

    const next = idx + 1
    if (next < routine.exercises.length) {
      setIdx(next)
      setPhase('exercise')
      setSecondsLeft(45)
      setSeriesDone((s) => s + 1)
      ping(muted)
      return
    }
  }, [secondsLeft, phase, idx, routine, muted, finished])

  const current = routine?.exercises[idx]
  const progress = routine ? (idx + (phase === 'rest' ? 0.5 : 0)) / routine.exercises.length : 0

  // Fetch previous session for comparison
  React.useEffect(() => {
    if (!finished) return
    api.weeklyProgress().then((d) => {
      const items = d.items
      if (items.length > 1) setPrevSession(items[items.length - 2])
    }).catch(() => {})
  }, [finished])

  async function finish() {
    if (finishing) return
    if (!sessionId) return
    const kcal = Math.floor(totalSeconds / 60) * 6
    try {
      setFinishing(true)
      const res = await api.finishWorkout(sessionId, totalSeconds, kcal)
      clearState()
      setFinished(true)
      setResult({ xp: res.xpGained, level: res.level, streak: res.streakDays, title: res.title, kcal, minutes: Math.floor(totalSeconds / 60) })
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
    try {
      await navigator.clipboard.writeText(text)
    } catch {}
  }

  if (error) {
    return (
      <GlassCard className="p-4">
        <div className="text-sm text-gray-600">{error}</div>
        <button onClick={goBack} className="mt-3 rounded-2xl bg-gray-900 px-4 py-2 text-sm font-semibold text-white">Volver</button>
      </GlassCard>
    )
  }

  if (finished && result) {
    const betterKcal = prevSession && result.kcal > (prevSession.kcal || 0)
    const betterMinutes = prevSession && result.minutes > (prevSession.minutes || 0)
    return (
      <>
        <Confetti />
        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.4 }} className="space-y-4">
          <GlassCard className="p-6 text-center">
            <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.2, type: 'spring', stiffness: 200 }} className="text-5xl mb-3">
              💪
            </motion.div>
            <div className="text-xl font-bold text-gray-900">¡Entrenamiento completado!</div>
            <div className="mt-1 text-sm text-gray-500">{routine?.name}</div>

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

            {/* Comparación con sesión anterior */}
            {prevSession && (betterKcal || betterMinutes) && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="mt-3 rounded-2xl bg-emerald-50 border border-emerald-200 p-3 text-sm">
                <span className="font-semibold text-emerald-700">🔥 Nuevo récord personal!</span>
                <div className="text-emerald-600">
                  {betterMinutes && `+${result.minutes - (prevSession.minutes || 0)} min · `}
                  {betterKcal && `+${result.kcal - (prevSession.kcal || 0)} kcal`}
                  {!betterMinutes && !betterKcal ? 'Mejor que tu última sesión' : ''} vs última sesión
                </div>
              </motion.div>
            )}

            <div className="mt-5 flex gap-2">
              <button onClick={goBack} className="flex-1 rounded-2xl bg-gray-900 px-4 py-2 text-sm font-semibold text-white hover:bg-gray-800">
                Ver perfil
              </button>
              <button onClick={handleShare} className="rounded-2xl border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50">
                Compartir
              </button>
            </div>
          </GlassCard>
        </motion.div>
      </>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-lg font-semibold text-gray-900">Entrenar ahora</div>
        <button
          onClick={() => setMuted((m) => !m)}
          className="rounded-2xl border border-gray-200 bg-white px-3 py-2 text-xs text-gray-600 hover:bg-gray-50 shadow-sm"
        >
          Sonido: {muted ? 'Off' : 'On'}
        </button>
      </div>

      <GlassCard className="p-4">
        <div className="text-xs uppercase tracking-widest text-gray-400">{routine?.name ?? 'Selecciona una rutina'}</div>
        <div className="mt-2 flex items-end justify-between gap-3">
          <div>
            <div className="text-2xl font-semibold tracking-tight text-gray-900">{phase === 'exercise' ? 'Ejercicio' : 'Descanso'}</div>
            <div className="text-sm text-gray-500">{current?.name ?? <Skeleton className="h-4 w-40" />}</div>
          </div>
          <div className="text-right">
            <div className="text-xs text-gray-400">Tiempo</div>
            <div className="text-3xl font-semibold tabular-nums text-gray-900">{formatMMSS(secondsLeft)}</div>
          </div>
        </div>

        <div className="mt-4">
          <ProgressBar value={progress} />
          <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
            <span>{routine ? `${idx + 1}/${routine.exercises.length}` : '—'}</span>
            <span>Total: {formatMMSS(totalSeconds)}</span>
          </div>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <div className="rounded-2xl border border-gray-200 bg-gray-50 p-3">
            <div className="text-xs text-gray-500">Series / Reps</div>
            <div className="mt-1 text-sm font-semibold text-gray-900">
              {current ? `${current.sets} x ${current.reps}${current.notes === 'segundos' ? 's' : ''}` : '—'}
            </div>
            <div className="mt-2 text-xs text-gray-400">{current?.instructions ?? 'Mantén técnica y control.'}</div>
          </div>
          <div className="rounded-2xl border border-gray-200 bg-gray-50 p-3">
            <div className="text-xs text-gray-500">Series completadas</div>
            <div className="mt-1 text-sm font-semibold text-gray-900">{seriesDone}</div>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2">
          <button
            onClick={() => { if (idx === 0) return; setIdx((v) => Math.max(0, v - 1)); setPhase('exercise'); setSecondsLeft(45) }}
            className="rounded-2xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 shadow-sm"
            disabled={!routine || idx === 0}
          >
            Anterior
          </button>
          <button
            onClick={() => { if (!routine || idx + 1 >= routine.exercises.length) return; setIdx((v) => v + 1); setPhase('exercise'); setSecondsLeft(45); setSeriesDone((s) => s + 1) }}
            className="rounded-2xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 shadow-sm"
            disabled={!routine || idx + 1 >= (routine?.exercises.length ?? 0)}
          >
            Siguiente
          </button>
        </div>

        {routine ? (
          <motion.button
            whileTap={{ scale: 0.99 }}
            onClick={finish}
            disabled={!sessionId || finishing}
            className="mt-3 w-full rounded-2xl border border-gray-300 bg-gray-100 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {finishing ? 'Finalizando…' : 'Finalizar entrenamiento'}
          </motion.button>
        ) : null}
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
