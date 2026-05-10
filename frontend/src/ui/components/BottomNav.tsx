import React from 'react'
import { Dumbbell, Home, Trophy, User, Play } from 'lucide-react'

export type NavKey = 'home' | 'routines' | 'train' | 'ranking' | 'profile'

export function BottomNav(props: { value: NavKey; onChange: (v: NavKey) => void }) {
  const items: Array<{ key: NavKey; label: string; icon: React.ReactNode }> = [
    { key: 'home', label: 'Inicio', icon: <Home size={18} /> },
    { key: 'routines', label: 'Rutinas', icon: <Dumbbell size={18} /> },
    { key: 'train', label: 'Entrenar', icon: <Play size={18} /> },
    { key: 'ranking', label: 'Ranking', icon: <Trophy size={18} /> },
    { key: 'profile', label: 'Perfil', icon: <User size={18} /> },
  ]

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 border-t border-gray-200 bg-white">
      <div className="mx-auto max-w-[960px] px-4">
        <div className="grid grid-cols-5">
          {items.map((it) => {
            const active = it.key === props.value
            return (
              <button
                key={it.key}
                onClick={() => props.onChange(it.key)}
                className={[
                  'flex flex-col items-center gap-1 px-2 py-3 text-xs transition',
                  active ? 'text-gray-900' : 'text-gray-400 hover:text-gray-600',
                ].join(' ')}
              >
                <span className={active ? 'text-gray-900' : ''}>{it.icon}</span>
                <span>{it.label}</span>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
