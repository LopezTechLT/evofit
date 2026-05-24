import React from 'react'
import { motion } from 'framer-motion'
import { Flame, Trophy, Zap, Medal, TrendingUp, ArrowLeft } from 'lucide-react'
import { api } from '../../lib/api'
import { GlassCard } from '../components/GlassCard'
import { ProgressBar } from '../components/ProgressBar'
import { Skeleton } from '../components/Skeleton'
import { StatPill } from '../components/StatPill'

export function FitnessHome(props: { onQuickTrain: (routineId: number) => void }) {
  const [me, setMe] = React.useState<Awaited<ReturnType<typeof api.me>> | null>(null)
  const [dash, setDash] = React.useState<Awaited<ReturnType<typeof api.dashboard>> | null>(null)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    let alive = true
    Promise.all([api.me(), api.dashboard()])
      .then(([m, d]) => {
        if (!alive) return
        setMe(m)
        setDash(d)
      })
      .catch(() => setError('Inicia sesión para ver el dashboard.'))
    return () => { alive = false }
  }, [])

  if (error) {
    return (
      <GlassCard className="p-4">
        <div className="text-sm text-gray-600">{error}</div>
      </GlassCard>
    )
  }

  const username = me?.username ?? 'Atleta'
  const routine = dash?.routineOfDay
  const xpToNext = dash?.xpToNext ?? 0
  const xp = dash?.xp ?? 0
  const level = dash?.level ?? 1
  const title = me?.title ?? 'Principiante'
  const league = me?.league ?? 'Bronce'
  const leagueIcon = me?.leagueIcon ?? '[B]'
  const progress = xpToNext === 0 ? 1 : Math.max(0, Math.min(1, (xp % 250) / 250))

  return (
    <div className="space-y-4">
      {/* Greeting + Title */}
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm text-gray-500">{dash?.greeting ?? <Skeleton className="h-4 w-28" />}</div>
          <div className="mt-1 text-2xl font-semibold tracking-tight text-gray-900">
            {dash ? `Hola, ${username}` : <Skeleton className="h-7 w-52" />}
          </div>
          <div className="mt-1 flex items-center gap-2 text-sm">
            <span className="rounded-full bg-gray-900 px-2 py-0.5 text-xs font-semibold text-white">
              {title}
            </span>
            <span className="text-gray-500">{leagueIcon} {league}</span>
          </div>
        </div>
        <a
          href="http://127.0.0.1:5000"
          className="rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-500 shadow-sm hover:bg-gray-50 hover:text-gray-700 transition-all"
        >
          <ArrowLeft size={14} className="inline" /> Sitio
        </a>
      </div>

      {/* Streak banner */}
      {dash && dash.streakDays > 0 && (
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="flex items-center gap-3 rounded-2xl bg-gradient-to-r from-gray-100 to-gray-200 border border-gray-300 p-3"
        >
          <Flame size={24} className="text-gray-700" />
          <div>
            <div className="text-sm font-semibold text-gray-900">Racha de {dash.streakDays} dias</div>
            <div className="text-xs text-gray-500">¡Sigue así! Cada día cuenta.</div>
          </div>
        </motion.div>
      )}

      {/* Routine of the day */}
      <GlassCard className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs uppercase tracking-widest text-gray-400">Rutina de hoy</div>
            <div className="mt-1 text-lg font-semibold text-gray-900">{routine?.name ?? '—'}</div>
            <div className="text-sm text-gray-500">{routine?.focus ?? 'Selecciona una rutina'}</div>
          </div>
          {routine?.id ? (
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => props.onQuickTrain(routine.id)}
              className="rounded-2xl bg-gray-900 px-4 py-2 text-sm font-semibold text-white hover:bg-gray-800"
            >
              Empezar
            </motion.button>
          ) : null}
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          <StatPill label="Nivel" value={`Lv ${level}`} />
          <StatPill label="Racha" value={`${dash?.streakDays ?? 0} días`} />
          <StatPill label="Semana" value={`${dash?.weekly.minutes ?? 0} min`} />
          <StatPill label="Calorías" value={`${dash?.weekly.kcal ?? 0} kcal`} />
        </div>

        <div className="mt-4">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Zap size={12} className="text-gray-600" />
              Progreso a {title}
            </span>
            <span>{xpToNext} XP para subir</span>
          </div>
          <ProgressBar value={progress} className="mt-2" />
        </div>
      </GlassCard>

      {/* Weekly stats */}
      <GlassCard className="p-4">
        <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-gray-400">
          <TrendingUp size={14} />
          Resumen semanal
        </div>
        <div className="mt-3 grid grid-cols-3 gap-3">
          <MiniStat label="Entrenos" value={`${dash?.weekly.sessions ?? 0}`} icon={<Zap size={16} />} />
          <MiniStat label="Minutos" value={`${dash?.weekly.minutes ?? 0}`} icon={<Medal size={16} />} />
          <MiniStat label="Kcal" value={`${dash?.weekly.kcal ?? 0}`} icon={<Flame size={16} />} />
        </div>
      </GlassCard>
    </div>
  )
}

function MiniStat(props: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-3 text-center">
      <div className="flex justify-center text-gray-600">{props.icon}</div>
      <div className="mt-1 text-lg font-bold text-gray-900">{props.value}</div>
      <div className="text-[11px] text-gray-400">{props.label}</div>
    </div>
  )
}


