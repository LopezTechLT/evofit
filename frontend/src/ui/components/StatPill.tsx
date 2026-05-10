import React from 'react'

export function StatPill(props: { label: string; value: string; tone?: 'ember' | 'rouge' | 'neutral' }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white px-3 py-2 text-gray-700">
      <div className="text-[11px] text-gray-400">{props.label}</div>
      <div className="text-sm font-semibold tracking-tight text-gray-900">{props.value}</div>
    </div>
  )
}
