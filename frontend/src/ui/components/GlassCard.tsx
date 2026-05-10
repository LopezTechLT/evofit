import React from 'react'

export function GlassCard(props: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={[
        'rounded-2xl border border-gray-200 bg-white shadow-sm',
        props.className ?? ''
      ].join(' ')}
    >
      {props.children}
    </div>
  )
}
