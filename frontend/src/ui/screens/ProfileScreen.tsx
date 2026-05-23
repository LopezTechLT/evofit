import React from 'react'
import { motion } from 'framer-motion'
import { User, Users, Medal, Target, Trophy, LogOut, Plus, Search, X } from 'lucide-react'
import { api, type ApiMe, type FeedPost, type MyChallenge, type FriendList, type SocialUser } from '../../lib/api'
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
  const [searchQ, setSearchQ] = React.useState('')
  const [searchResults, setSearchResults] = React.useState<SocialUser[] | null>(null)
  const [searching, setSearching] = React.useState(false)

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

  React.useEffect(() => {
    if (subTab !== 'friends' || !searchQ.trim()) {
      setSearchResults(null)
      return
    }
    const t = setTimeout(() => {
      setSearching(true)
      api.searchUsers(searchQ.trim()).then((d) => setSearchResults(d.items)).catch(() => setSearchResults([])).finally(() => setSearching(false))
    }, 300)
    return () => clearTimeout(t)
  }, [searchQ, subTab])

  async function handleFollow(userId: number) {
    try {
      await api.followUser(userId)
      setSearchResults((prev) => prev?.map((u) => u.userId === userId ? { ...u, isFollowing: !u.isFollowing } : u) ?? null)
      api.friends().then((d) => setFriends(d)).catch(() => {})
    } catch {}
  }

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
          {/* Search bar */}
          <div className="relative mb-4">
            <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              placeholder="Buscar usuarios..."
              className="w-full rounded-2xl border border-gray-200 bg-gray-50 py-2 pl-9 pr-8 text-sm outline-none focus:border-gray-400"
            />
            {searchQ && (
              <button onClick={() => setSearchQ('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                <X size={16} />
              </button>
            )}
          </div>

          {/* Search results */}
          {searchQ.trim() && (
            <div className="mb-4">
              <div className="mb-2 text-xs font-semibold text-gray-500 uppercase tracking-widest">Resultados</div>
              {searching ? (
                <Skeleton className="h-10 w-full" />
              ) : searchResults && searchResults.length === 0 ? (
                <div className="text-sm text-gray-400">Sin resultados</div>
              ) : (
                <div className="space-y-2">
                  {searchResults?.map((u) => (
                    <div key={u.userId} className="flex items-center gap-3 rounded-2xl border border-gray-100 bg-white p-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-900 text-sm font-bold text-white">
                        {u.username[0].toUpperCase()}
                      </div>
                      <span className="flex-1 text-sm font-semibold text-gray-900">{u.username}</span>
                      <button
                        onClick={() => handleFollow(u.userId)}
                        className={[
                          'rounded-xl px-3 py-1.5 text-xs font-semibold transition',
                          u.isFollowing
                            ? 'border border-gray-300 bg-white text-gray-600 hover:bg-gray-100'
                            : 'bg-gray-900 text-white hover:bg-gray-800',
                        ].join(' ')}
                      >
                        {u.isFollowing ? 'Dejar' : 'Seguir'}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

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
