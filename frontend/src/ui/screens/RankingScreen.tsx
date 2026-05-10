import React from 'react'
import { motion } from 'framer-motion'
import { Trophy, Medal, Flame, TrendingUp, Users } from 'lucide-react'
import { api, type MyLeague, type LeaderboardUser } from '../../lib/api'
import { GlassCard } from '../components/GlassCard'
import { Skeleton } from '../components/Skeleton'

type Tab = 'league' | 'weekly' | 'monthly' | 'all'

export function RankingScreen() {
  const [tab, setTab] = React.useState<Tab>('league')
  const [league, setLeague] = React.useState<MyLeague | null>(null)
  const [lb, setLb] = React.useState<{ period: string; items: LeaderboardUser[] } | null>(null)

  React.useEffect(() => {
    let alive = true
    if (tab === 'league') {
      api.myLeague().then((d) => alive && setLeague(d)).catch(() => alive && setLeague(null))
    } else {
      api.leaderboard(tab).then((d) => alive && setLb(d)).catch(() => alive && setLb(null))
    }
    return () => { alive = false }
  }, [tab])

  const tabs: Array<{ key: Tab; label: string }> = [
    { key: 'league', label: 'Mi liga' },
    { key: 'weekly', label: 'Semanal' },
    { key: 'monthly', label: 'Mensual' },
    { key: 'all', label: 'Global' },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Trophy size={20} className="text-gray-700" />
        <span className="text-lg font-semibold text-gray-900">Ranking</span>
      </div>

      {/* Tab selector */}
      <div className="flex gap-1 rounded-2xl border border-gray-200 bg-gray-100 p-1">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={[
              'flex-1 rounded-xl px-3 py-2 text-xs font-semibold transition',
              tab === t.key ? 'bg-gray-900 text-white' : 'text-gray-500 hover:text-gray-700',
            ].join(' ')}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* League header */}
      {tab === 'league' && league && (
        <GlassCard className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl">{league.league.icon}</span>
              <div>
                <div className="text-xs text-gray-500">{league.league.name}</div>
                <div className="text-sm font-semibold text-gray-900">
                  {league.memberCount} miembros
                </div>
              </div>
            </div>
            {league.myRank != null && (
              <div className="text-right">
                <div className="text-xs text-gray-500">Tu puesto</div>
                <div className="text-xl font-bold text-gray-900">#{league.myRank}</div>
              </div>
            )}
          </div>
          <div className="mt-3 rounded-2xl border border-gray-200 bg-gray-50 p-3">
            <div className="flex items-center gap-2">
              <Medal size={16} className="text-gray-600" />
              <span className="text-xs text-gray-500">Tu XP en liga: {league.myXp}</span>
            </div>
          </div>
        </GlassCard>
      )}

      {/* Leaderboard list */}
      <GlassCard className="p-4">
        <div className="space-y-2">
          {tab === 'league' && !league && <Skeleton className="h-10 w-full" />}
          {tab !== 'league' && !lb && <Skeleton className="h-10 w-full" />}

          {tab === 'league' &&
            league?.items.map((u, i) => <LeaderboardRow key={u.userId} rank={u.rank} username={u.username} xp={u.xp} />)}

          {tab !== 'league' &&
            lb?.items.map((u, i) => (
              <LeaderboardRow key={u.userId} rank={u.rank} username={u.username} xp={u.xp} kcal={u.kcal} sessions={u.sessions} />
            ))}
        </div>
      </GlassCard>
    </div>
  )
}

function LeaderboardRow(props: { rank: number; username: string; xp: number; kcal?: number; sessions?: number }) {
  const colors = ['text-gray-900', 'text-gray-500', 'text-gray-600']
  const icons = ['🥇', '🥈', '🥉']
  const isPodium = props.rank <= 3
  const colorClass = isPodium ? colors[props.rank - 1] : 'text-gray-400'

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2, delay: props.rank * 0.03 }}
      className="flex items-center gap-3 rounded-2xl border border-gray-100 bg-white p-3 hover:bg-gray-50"
    >
      <div className={`flex h-8 w-8 items-center justify-center text-sm font-bold ${colorClass}`}>
        {isPodium ? <span className="text-lg">{icons[props.rank - 1]}</span> : `#${props.rank}`}
      </div>
      <div className="flex-1">
        <div className="text-sm font-semibold text-gray-900">{props.username}</div>
        <div className="flex gap-2 text-[11px] text-gray-400">
          <span className="flex items-center gap-1"><Flame size={12} /> {props.xp} XP</span>
          {props.kcal != null && <span>{props.kcal} kcal</span>}
          {props.sessions != null && <span>{props.sessions} sesiones</span>}
        </div>
      </div>
      <div className="text-sm font-bold text-gray-900">{props.xp} XP</div>
    </motion.div>
  )
}
