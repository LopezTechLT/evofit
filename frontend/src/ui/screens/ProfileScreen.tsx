import React from 'react'
import { motion } from 'framer-motion'
import { User, Users, Medal, Target, Trophy, LogOut } from 'lucide-react'
import { api, type ApiMe, type FeedPost, type MyChallenge, type FriendList } from '../../lib/api'
import { GlassCard } from '../components/GlassCard'
import { Skeleton } from '../components/Skeleton'
import { ProgressBar } from '../components/ProgressBar'

type SubTab = 'stats' | 'feed' | 'friends' | 'challenges'

export function ProfileScreen() {
  const [me, setMe] = React.useState<ApiMe | null>(null)
  const [subTab, setSubTab] = React.useState<SubTab>('stats')
  const [feed, setFeed] = React.useState<FeedPost[] | null>(null)
  const [myChallenges, setMyChallenges] = React.useState<MyChallenge[] | null>(null)
  const [friends, setFriends] = React.useState<FriendList | null>(null)

  React.useEffect(() => {
    let alive = true
    api.me().then((m) => alive && setMe(m)).catch(() => {})
    return () => { alive = false }
  }, [])

  React.useEffect(() => {
    let alive = true
    if (subTab === 'feed') {
      api.feed().then((d) => alive && setFeed(d.items)).catch(() => {})
    } else if (subTab === 'challenges') {
      api.myChallenges().then((d) => alive && setMyChallenges(d.items)).catch(() => {})
    } else if (subTab === 'friends') {
      api.friends().then((d) => alive && setFriends(d)).catch(() => {})
    }
    return () => { alive = false }
  }, [subTab])

  const subtabs: Array<{ key: SubTab; label: string; icon: React.ReactNode }> = [
    { key: 'stats', label: 'Estadísticas', icon: <User size={14} /> },
    { key: 'feed', label: 'Feed', icon: <Target size={14} /> },
    { key: 'friends', label: 'Amigos', icon: <Users size={14} /> },
    { key: 'challenges', label: 'Retos', icon: <Trophy size={14} /> },
  ]

  return (
    <div className="space-y-4">
      {/* Header */}
      <GlassCard className="p-4">
        {!me ? (
          <Skeleton className="h-20 w-full" />
        ) : (
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gray-900 text-xl font-bold text-white">
              {me.username[0].toUpperCase()}
            </div>
            <div className="flex-1">
              <div className="text-lg font-semibold text-gray-900">{me.username}</div>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <span>{me.leagueIcon} {me.league}</span>
                <span>·</span>
                <span>{me.title}</span>
                <span>·</span>
                <span>Lv {me.fitness.level}</span>
              </div>
              <div className="mt-2 flex items-center gap-4 text-xs text-gray-400">
                <span className="flex items-center gap-1"><Medal size={12} /> {me.fitness.xp} XP</span>
                <span className="flex items-center gap-1"><Target size={12} /> {me.fitness.streakDays} días</span>
              </div>
              <div className="mt-2">
                <ProgressBar value={me.fitness.xpToNext === 0 ? 1 : ((me.fitness.xp % 250) / 250)} />
              </div>
            </div>
          </div>
        )}
      </GlassCard>

      {/* Sub-tabs */}
      <div className="flex gap-1 rounded-2xl border border-gray-200 bg-gray-100 p-1">
        {subtabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setSubTab(t.key)}
            className={[
              'flex items-center gap-1 rounded-xl px-3 py-2 text-xs font-semibold transition',
              subTab === t.key ? 'bg-gray-900 text-white' : 'text-gray-500 hover:text-gray-700',
            ].join(' ')}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* Stats */}
      {subTab === 'stats' && me && (
        <GlassCard className="p-4">
          <div className="grid grid-cols-2 gap-3">
            <StatBox label="Nivel" value={`Lv ${me.fitness.level}`} sub={me.title} />
            <StatBox label="XP total" value={`${me.fitness.xp}`} sub={`Faltan ${me.fitness.xpToNext} XP`} />
            <StatBox label="Racha" value={`${me.fitness.streakDays} días`} sub="Sigue así 🔥" />
            <StatBox label="Liga" value={me.league} sub={me.leagueIcon} />
          </div>
        </GlassCard>
      )}

      {/* Feed */}
      {subTab === 'feed' && (
        <GlassCard className="p-4">
          <div className="space-y-3">
            {!feed
              ? Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)
              : feed.length === 0
                ? <div className="text-center text-sm text-gray-400 py-4">Aún no hay actividad en el feed</div>
                : feed.map((p) => (
                    <motion.div
                      key={p.id}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="rounded-2xl border border-gray-100 bg-white p-3"
                    >
                      <div className="flex items-start gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-900 text-sm font-bold text-white">
                          {p.username[0].toUpperCase()}
                        </div>
                        <div>
                          <div className="text-sm">
                            <span className="font-semibold text-gray-900">{p.username}</span>{' '}
                            <span className="text-gray-600">{p.message}</span>
                          </div>
                          <div className="mt-1 text-[11px] text-gray-400">
                            {new Date(p.createdAt).toLocaleDateString('es-ES', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  ))}
          </div>
        </GlassCard>
      )}

      {/* Friends */}
      {subTab === 'friends' && (
        <GlassCard className="p-4">
          {!friends ? (
            <Skeleton className="h-20 w-full" />
          ) : (
            <div className="space-y-4">
              <div>
                <div className="mb-2 text-xs font-semibold text-gray-500 uppercase tracking-widest">
                  Siguiendo ({friends.following.length})
                </div>
                {friends.following.length === 0 ? (
                  <div className="text-sm text-gray-400">No sigues a nadie todavía</div>
                ) : (
                  <div className="space-y-2">
                    {friends.following.map((f) => (
                      <div key={f.id} className="flex items-center gap-3 rounded-2xl border border-gray-100 bg-white p-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-900 text-sm font-bold text-white">
                          {f.username[0].toUpperCase()}
                        </div>
                        <span className="text-sm font-semibold text-gray-900">{f.username}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div>
                <div className="mb-2 text-xs font-semibold text-gray-500 uppercase tracking-widest">
                  Seguidores ({friends.followers.length})
                </div>
                {friends.followers.length === 0 ? (
                  <div className="text-sm text-gray-400">Sin seguidores todavía</div>
                ) : (
                  <div className="space-y-2">
                    {friends.followers.map((f) => (
                      <div key={f.id} className="flex items-center gap-3 rounded-2xl border border-gray-100 bg-white p-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-900 text-sm font-bold text-white">
                          {f.username[0].toUpperCase()}
                        </div>
                        <span className="text-sm font-semibold text-gray-900">{f.username}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </GlassCard>
      )}

      {/* Challenges */}
      {subTab === 'challenges' && (
        <GlassCard className="p-4">
          {!myChallenges ? (
            <Skeleton className="h-20 w-full" />
          ) : myChallenges.length === 0 ? (
            <div className="text-center text-sm text-gray-400 py-4">
              No tienes retos activos. ¡Busca retos en el feed y únete!
            </div>
          ) : (
            <div className="space-y-3">
              {myChallenges.map((c) => {
                const pct = c.goalValue > 0 ? Math.min(1, c.progress / c.goalValue) : 0
                return (
                  <div key={c.id} className="rounded-2xl border border-gray-200 bg-white p-3">
                    <div className="flex items-center justify-between">
                      <div className="text-sm font-semibold text-gray-900">{c.name}</div>
                      {c.completed ? (
                        <span className="rounded-full bg-emerald-100 px-2 py-1 text-[11px] text-emerald-700">
                          Completado ✓
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">
                          {c.progress}/{c.goalValue}
                        </span>
                      )}
                    </div>
                    <div className="mt-2">
                      <ProgressBar value={pct} />
                    </div>
                    <div className="mt-1 text-[11px] text-gray-400">
                      Vence: {new Date(c.endDate).toLocaleDateString('es-ES')}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </GlassCard>
      )}
    </div>
  )
}

function StatBox(props: { label: string; value: string; sub: string }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-gray-50 p-3">
      <div className="text-[11px] text-gray-400">{props.label}</div>
      <div className="mt-1 text-base font-semibold text-gray-900">{props.value}</div>
      <div className="text-[11px] text-gray-400">{props.sub}</div>
    </div>
  )
}
