export type ApiMe = {
  id: number
  username: string
  role: string
  title: string
  league: string
  leagueIcon: string
  fitness: {
    xp: number
    level: number
    xpToNext: number
    streakDays: number
    weeklyMinutes: number
    weeklyCalories: number
  }
}

export type RoutineCard = {
  id: number
  name: string
  coverImage: string | null
  difficulty: string
  durationMinutes: number
  exercisesCount: number
  estimatedKcal: number
  focus: string
}

export type RoutineDetail = RoutineCard & {
  exercises: Array<{
    id: number
    name: string
    mediaUrl: string | null
    instructions: string | null
    muscles: string[]
    sets: number
    reps: number
    restSeconds: number
    notes: string | null
    order: number
  }>
}

export type FitnessDashboard = {
  greeting: string
  routineOfDay: RoutineCard | null
  weekly: { minutes: number; kcal: number; sessions: number }
  streakDays: number
  level: number
  xp: number
  xpToNext: number
}

export type WeeklyProgressPoint = {
  date: string
  minutes: number
  kcal: number
  weightKg: number | null
  imc: number | null
}

export type Achievement = {
  code: string
  name: string
  description: string | null
  icon: string | null
  unlocked: boolean
}

export type LeaderboardUser = {
  rank: number
  userId: number
  username: string
  xp: number
  kcal: number
  sessions: number
}

export type MyLeague = {
  league: { id: number; name: string; icon: string }
  myRank: number | null
  myXp: number
  memberCount: number
  items: Array<{ rank: number; userId: number; username: string; xp: number }>
}

export type SocialUser = {
  id: number
  username: string
  isFollowing: boolean
}

export type FriendList = {
  following: Array<{ id: number; username: string }>
  followers: Array<{ id: number; username: string }>
}

export type FeedPost = {
  id: number
  userId: number
  username: string
  type: string
  message: string
  metadata: Record<string, unknown> | null
  createdAt: string
}

export type Challenge = {
  id: number
  name: string
  description: string | null
  goalType: string
  goalValue: number
  xpReward: number
  endDate: string
  creator: string
  participantCount: number
}

export type MyChallenge = {
  id: number
  name: string
  progress: number
  goalValue: number
  goalType: string
  completed: boolean
  endDate: string
}

export type UserProfile = {
  id: number
  username: string
  level: number
  title: string
  xp: number
  streakDays: number
  league: string
  leagueIcon: string
  stats: { sessions: number; kcal: number }
  achievements: Array<{ code: string; name: string; icon: string | null; unlocked: boolean }>
  isFollowing: boolean
}

const baseUrl = ''

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${baseUrl}${path}`, { credentials: 'include' })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return (await res.json()) as T
}

async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${baseUrl}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
    credentials: 'include',
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return (await res.json()) as T
}

export const api = {
  me: () => getJson<ApiMe>('/api/me'),
  dashboard: () => getJson<FitnessDashboard>('/api/fitness/dashboard'),
  routines: () => getJson<{ items: RoutineCard[] }>('/api/fitness/routines'),
  routine: (id: number) => getJson<RoutineDetail>(`/api/fitness/routines/${id}`),
  startWorkout: (routineId?: number) => postJson<{ sessionId: number }>('/api/fitness/workouts/start', { routineId }),
  finishWorkout: (sessionId: number, totalSeconds: number, kcalBurned: number) =>
    postJson<{ ok: boolean; xpGained: number; level: number; streakDays: number; leveledUp: boolean; title: string }>(
      `/api/fitness/workouts/${sessionId}/finish`,
      { totalSeconds, kcalBurned },
    ),
  weeklyProgress: () => getJson<{ items: WeeklyProgressPoint[] }>('/api/fitness/progress/weekly'),
  achievements: () => getJson<{ items: Achievement[] }>('/api/fitness/achievements'),
  generateRoutine: (payload: {
    goal: string
    experience: string
    daysAvailable: number
    weight?: number
    height?: number
    sex?: string
  }) => postJson('/api/fitness/routines/generate', payload),

  // Leaderboard & Leagues
  leaderboard: (period: string = 'weekly') => getJson<{ period: string; items: LeaderboardUser[] }>(`/api/leaderboard?period=${period}`),
  myLeague: () => getJson<MyLeague>('/api/leagues/my'),
  promoteLeague: () => postJson<{ ok: boolean; promoted: boolean; league?: string; icon?: string }>('/api/leagues/promote'),

  // Social
  searchUsers: (q: string) => getJson<{ items: SocialUser[] }>(`/api/social/users?q=${encodeURIComponent(q)}`),
  followUser: (userId: number) => postJson<{ following: boolean }>('/api/social/follow', { userId }),
  friends: () => getJson<FriendList>('/api/social/friends'),
  feed: (page: number = 1) => getJson<{ items: FeedPost[] }>(`/api/feed?page=${page}`),

  // Challenges
  challenges: () => getJson<{ items: Challenge[] }>('/api/challenges'),
  createChallenge: (payload: {
    name: string
    description?: string
    goalType: string
    goalValue: number
    xpReward?: number
    endDate: string
  }) => postJson<{ ok: boolean; id: number }>('/api/challenges/create', payload),
  joinChallenge: (id: number) => postJson<{ ok: boolean }>(`/api/challenges/${id}/join`),
  myChallenges: () => getJson<{ items: MyChallenge[] }>('/api/challenges/mine'),

  // Profile
  profile: (userId: number) => getJson<UserProfile>(`/api/profile/${userId}`),
}
