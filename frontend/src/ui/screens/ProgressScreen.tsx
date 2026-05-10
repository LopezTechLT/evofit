import React from 'react'
import { api } from '../../lib/api'
import { GlassCard } from '../components/GlassCard'
import { Skeleton } from '../components/Skeleton'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export function ProgressScreen() {
  const [data, setData] = React.useState<Awaited<ReturnType<typeof api.weeklyProgress>> | null>(null)

  React.useEffect(() => {
    let alive = true
    api
      .weeklyProgress()
      .then((d) => alive && setData(d))
      .catch(() => alive && setData({ items: [] }))
    return () => {
      alive = false
    }
  }, [])

  return (
    <div className="space-y-4">
      <div className="text-lg font-semibold">Progreso</div>
      <GlassCard className="p-4">
        <div className="text-xs uppercase tracking-widest text-white/50">Semana</div>
        <div className="mt-3 h-48">
          {!data ? (
            <Skeleton className="h-48 w-full" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.items}>
                <XAxis dataKey="date" tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 11 }} />
                <YAxis tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#11111A', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12 }} />
                <Line type="monotone" dataKey="minutes" stroke="#f97316" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="kcal" stroke="#ef4444" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
        <div className="mt-2 text-xs text-white/50">Minutos (naranja) / kcal (rojo)</div>
      </GlassCard>
    </div>
  )
}

