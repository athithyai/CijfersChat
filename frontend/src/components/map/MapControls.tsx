/** Layer-level toggle buttons + selected region badge. */

import { useChatStore } from '../../store/chatStore'
import type { GeographyLevel } from '../../types'

const LEVELS: { value: GeographyLevel; label: string; sublabel: string }[] = [
  { value: 'gemeente', label: 'Gemeente', sublabel: 'municipalities' },
  { value: 'wijk',    label: 'Wijk',     sublabel: 'districts' },
  { value: 'buurt',   label: 'Buurt',    sublabel: 'neighbourhoods' },
]

export function MapControls() {
  const currentPlan    = useChatStore(s => s.currentPlan)
  const selectedRegion = useChatStore(s => s.selectedRegion)
  const isLayerLoading = useChatStore(s => s.isLayerLoading)
  const switchLayer    = useChatStore(s => s.switchLayer)
  const selectRegion   = useChatStore(s => s.selectRegion)

  const activeLevel = currentPlan?.geography_level ?? null

  return (
    <div className="absolute top-3 left-3 z-10 flex flex-col gap-2 pointer-events-auto">

      {/* Layer toggles */}
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-lg border
                      border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-3 py-1.5 border-b border-gray-100 dark:border-gray-800">
          <span className="text-[10px] font-semibold uppercase tracking-wider
                           text-gray-400 dark:text-gray-500">
            Geography layer
          </span>
        </div>
        <div className="flex flex-col">
          {LEVELS.map(({ value, label, sublabel }) => {
            const isActive = activeLevel === value
            const disabled = isLayerLoading

            return (
              <button
                key={value}
                onClick={() => !disabled && switchLayer(value)}
                disabled={disabled}
                className={[
                  'flex items-center gap-2.5 px-3 py-2 text-left transition-colors',
                  'border-b border-gray-100 dark:border-gray-800 last:border-0',
                  isActive
                    ? 'bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-300'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800',
                  disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer',
                ].join(' ')}
              >
                {/* Active indicator dot */}
                <span className={[
                  'w-1.5 h-1.5 rounded-full shrink-0 transition-colors',
                  isActive ? 'bg-brand-600 dark:bg-brand-400' : 'bg-gray-300 dark:bg-gray-600',
                ].join(' ')} />

                <span className="flex flex-col min-w-0">
                  <span className="text-xs font-medium leading-tight">{label}</span>
                  <span className="text-[10px] text-gray-400 dark:text-gray-500 leading-tight">
                    {sublabel}
                  </span>
                </span>

                {isActive && isLayerLoading && (
                  <span className="ml-auto w-3 h-3 border-2 border-brand-400 border-t-transparent
                                   rounded-full animate-spin shrink-0" />
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* Selected region badge */}
      {selectedRegion && (
        <div className="bg-white dark:bg-gray-900 rounded-xl shadow-lg border
                        border-brand-200 dark:border-brand-800 px-3 py-2
                        flex items-start gap-2 max-w-[180px]">
          <div className="flex-1 min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-wider
                          text-brand-500 dark:text-brand-400 mb-0.5">
              Selected
            </p>
            <p className="text-xs font-medium text-gray-800 dark:text-gray-200 truncate">
              {selectedRegion.statnaam}
            </p>
            <p className="text-[10px] text-gray-400 dark:text-gray-500">
              {selectedRegion.statcode}
            </p>
          </div>
          <button
            onClick={() => selectRegion(null)}
            className="shrink-0 mt-0.5 text-gray-400 hover:text-gray-600
                       dark:hover:text-gray-200 transition-colors"
            title="Deselect region"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5}
                d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}
    </div>
  )
}
