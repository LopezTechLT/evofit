import React from 'react'

export function Skeleton(props: { className?: string }) {
  return <div className={['animate-pulse rounded-xl bg-gray-200', props.className ?? 'h-4 w-full'].join(' ')} />
}
