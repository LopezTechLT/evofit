import React from 'react'
import { motion } from 'framer-motion'
import { Flame, Timer, BarChart3 } from 'lucide-react'
import type { RoutineCard as Routine } from '../../lib/api'
import { GlassCard } from './GlassCard'

export function RoutineCard(props: { routine: Routine; onTrain?: () => void; onOpen?: () => void }) {
  const r = props.routine
  return (
    <motion.div whileHover={{ y: -4 }} whileTap={{ scale: 0.99 }} transition={{ duration: 0.2 }}>
      <GlassCard className="overflow-hidden">
        <button onClick={props.onOpen} className="block w-full text-left">
          <div className="relative h-28 w-full bg-gradient-to-br from-gray-700 to-gray-900">
            <div className="absolute bottom-3 left-3">
              <div className="text-sm font-semibold text-white">{r.name}</div>
              <div className="text-xs text-gray-300">{r.focus}</div>
            </div>
            <div className="absolute bottom-3 right-3 rounded-full border border-white/20 bg-white/10 px-2 py-1 text-[11px] text-gray-200">
              {r.difficulty}
            </div>
          </div>
        </button>
        <div className="p-3">
          <div className="grid grid-cols-3 gap-2 text-xs text-gray-600">
            <div className="flex items-center gap-2 rounded-xl border border-gray-200 bg-gray-50 px-2 py-2">
              <Timer size={14} className="text-gray-500" /> {r.durationMinutes} min
            </div>
            <div className="flex items-center gap-2 rounded-xl border border-gray-200 bg-gray-50 px-2 py-2">
              <BarChart3 size={14} className="text-gray-400" /> {r.exercisesCount} ex
            </div>
            <div className="flex items-center gap-2 rounded-xl border border-gray-200 bg-gray-50 px-2 py-2">
              <Flame size={14} className="text-gray-500" /> {r.estimatedKcal} kcal
            </div>
          </div>
          <div className="mt-3">
            <button
              onClick={props.onTrain}
              className="w-full rounded-2xl bg-gray-900 px-4 py-2 text-sm font-semibold text-white hover:bg-gray-800"
            >
              Entrenar ahora
            </button>
          </div>
        </div>
      </GlassCard>
    </motion.div>
  )
}
