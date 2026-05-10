import React from 'react'
import { motion } from 'framer-motion'

export function ProgressBar(props: { value: number; className?: string }) {
  const clamped = Math.max(0, Math.min(1, props.value))
  return (
    <div className={['h-2 w-full rounded-full bg-gray-200', props.className ?? ''].join(' ')}>
      <motion.div
        className="h-2 rounded-full bg-gray-900"
        initial={{ width: 0 }}
        animate={{ width: `${clamped * 100}%` }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
      />
    </div>
  )
}
