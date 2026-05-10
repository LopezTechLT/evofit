import React from 'react'
import { api, type RoutineCard as Routine } from '../../lib/api'
import { RoutineCard } from '../components/RoutineCard'
import { Skeleton } from '../components/Skeleton'

export function RoutinesScreen(props: { onOpenRoutine: (id: number) => void; onTrain: (id: number) => void }) {
  const [items, setItems] = React.useState<Routine[] | null>(null)

  React.useEffect(() => {
    let alive = true
    api
      .routines()
      .then((r) => alive && setItems(r.items))
      .catch(() => alive && setItems([]))
    return () => {
      alive = false
    }
  }, [])

  return (
    <div className="space-y-3">
      <div className="text-lg font-semibold text-gray-900">Rutinas</div>
      {!items ? (
        <div className="grid gap-3 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-2xl border border-gray-200 bg-white p-3 shadow-sm">
              <Skeleton className="h-24 w-full" />
              <div className="mt-3 space-y-2">
                <Skeleton className="h-4 w-2/3" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {items.map((r) => (
            <RoutineCard
              key={r.id}
              routine={r}
              onOpen={() => props.onOpenRoutine(r.id)}
              onTrain={() => props.onTrain(r.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
