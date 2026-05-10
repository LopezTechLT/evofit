import React from 'react'
import { motion } from 'framer-motion'
import { api, type RoutineDetail } from '../../lib/api'
import { formatMMSS } from '../../lib/time'
import { GlassCard } from '../components/GlassCard'
import { ProgressBar } from '../components/ProgressBar'
import { Skeleton } from '../components/Skeleton'

type Phase = 'exercise' | 'rest'

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
  const [result, setResult] = React.useState<{ xp: number; level: number; streak: number; title: string } | null>(null)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (!props.routineId) return
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
  }, [props.routineId])

  React.useEffect(() => {
    if (!props.routineId || finished) return
    const t = window.setInterval(() => {
      setTotalSeconds((v) => v + 1)
      setSecondsLeft((v) => (v > 0 ? v - 1 : 0))
    }, 1000)
    return () => window.clearInterval(t)
  }, [props.routineId, finished])

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

  async function finish() {
    if (finishing) return
    if (!sessionId) {
      setError('No hay sesión activa todavía. Espera un momento e inténtalo de nuevo.')
      return
    }
    const kcal = routine?.estimatedKcal ?? Math.floor(totalSeconds / 60) * 6
    try {
      setFinishing(true)
      const res = await api.finishWorkout(sessionId, totalSeconds, kcal)
      setFinished(true)
      setResult({ xp: res.xpGained, level: res.level, streak: res.streakDays, title: res.title })
    } catch {
      setError('Error al finalizar. Intenta de nuevo.')
    } finally {
      setFinishing(false)
    }
  }

  function goBack() {
    if (props.onFinish) props.onFinish()
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
    return (
      <GlassCard className="p-4 text-center">
        <div className="text-3xl mb-2">🎉</div>
        <div className="text-lg font-semibold text-gray-900">Entrenamiento completado</div>
        <div className="mt-3 space-y-1 text-sm text-gray-600">
          <p>🔥 +{result.xp} XP ganados</p>
          <p>Nivel {result.level} · Racha de {result.streak} días</p>
          <p className="text-xs text-gray-400">{result.title}</p>
        </div>
        <button onClick={goBack} className="mt-4 rounded-2xl bg-gray-900 px-6 py-2 text-sm font-semibold text-white">
          Ver perfil
        </button>
      </GlassCard>
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
            <span>
              {routine ? `${idx + 1}/${routine.exercises.length}` : '—'}
            </span>
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
            onClick={() => {
              if (idx === 0) return
              setIdx((v) => Math.max(0, v - 1))
              setPhase('exercise')
              setSecondsLeft(45)
            }}
            className="rounded-2xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 shadow-sm"
            disabled={!routine || idx === 0}
          >
            Anterior
          </button>
          <button
            onClick={() => {
              if (!routine || idx + 1 >= routine.exercises.length) return
              setIdx((v) => v + 1)
              setPhase('exercise')
              setSecondsLeft(45)
              setSeriesDone((s) => s + 1)
            }}
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
    setTimeout(() => {
      o.stop()
      ctx.close()
    }, 120)
  } catch {}
}
