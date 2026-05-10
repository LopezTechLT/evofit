import React from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { BottomNav, NavKey } from './components/BottomNav'
import { FitnessHome } from './screens/FitnessHome'
import { RoutinesScreen } from './screens/RoutinesScreen'
import { TrainScreen } from './screens/TrainScreen'
import { RankingScreen } from './screens/RankingScreen'
import { ProfileScreen } from './screens/ProfileScreen'

export function App() {
  const [tab, setTab] = React.useState<NavKey>('home')
  const [activeRoutineId, setActiveRoutineId] = React.useState<number | null>(null)

  return (
    <div className="min-h-full bg-gray-100 text-gray-900">
      <div className="mx-auto flex min-h-full w-full max-w-[960px] flex-col px-4 pb-24 pt-4">
        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.25, ease: 'easeOut' }}
            className="flex-1"
          >
            {tab === 'home' && (
              <FitnessHome onQuickTrain={(id) => { setActiveRoutineId(id); setTab('train') }} />
            )}
            {tab === 'routines' && (
              <RoutinesScreen
                onOpenRoutine={(id) => setActiveRoutineId(id)}
                onTrain={(id) => { setActiveRoutineId(id); setTab('train') }}
              />
            )}
            {tab === 'train' && <TrainScreen routineId={activeRoutineId} onFinish={() => setTab('profile')} />}
            {tab === 'ranking' && <RankingScreen />}
            {tab === 'profile' && <ProfileScreen />}
          </motion.div>
        </AnimatePresence>
      </div>
      <BottomNav value={tab} onChange={setTab} />
    </div>
  )
}
