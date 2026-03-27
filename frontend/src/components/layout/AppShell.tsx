import { useCallback, useRef, useState } from 'react'
import { ChatPanel } from '../chat/ChatPanel'
import { MapPanel } from '../map/MapPanel'
import { ThemeToggle } from './ThemeToggle'

const MIN_CHAT_WIDTH = 300
const MAX_CHAT_WIDTH = 640
const DEFAULT_CHAT_WIDTH = 400

export function AppShell() {
  const [chatWidth, setChatWidth] = useState(DEFAULT_CHAT_WIDTH)
  const [dragging, setDragging] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const startDrag = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setDragging(true)

    const startX = e.clientX
    const startW = chatWidth

    const onMove = (ev: MouseEvent) => {
      const delta = ev.clientX - startX
      const next = Math.max(MIN_CHAT_WIDTH, Math.min(MAX_CHAT_WIDTH, startW + delta))
      setChatWidth(next)
    }

    const onUp = () => {
      setDragging(false)
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }

    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [chatWidth])

  return (
    <div className="h-screen w-screen flex flex-col bg-gray-50 dark:bg-gray-950 overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between px-4 h-12 bg-white dark:bg-gray-900
                         border-b border-gray-200 dark:border-gray-800 shrink-0 z-10 shadow-sm">
        <div className="flex items-center gap-2">
          {/* Logo mark */}
          <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5}
                d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0
                   13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0
                   00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
          </div>
          <span className="font-semibold text-gray-900 dark:text-gray-100 text-sm">
            CijfersChat
          </span>
          <span className="text-xs text-gray-400 hidden sm:block">
            Dutch Regional Statistics
          </span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-xs text-gray-400 mr-2 hidden sm:block">
            CBS StatLine × PDOK
          </span>
          <ThemeToggle />
        </div>
      </header>

      {/* Main content */}
      <div ref={containerRef} className="flex flex-1 min-h-0 overflow-hidden">
        {/* Chat panel */}
        <div
          style={{ width: chatWidth }}
          className="flex flex-col shrink-0 min-h-0 bg-white dark:bg-gray-900
                     border-r border-gray-200 dark:border-gray-800"
        >
          <ChatPanel />
        </div>

        {/* Resize handle */}
        <div
          onMouseDown={startDrag}
          className={`resize-handle w-1 shrink-0 bg-gray-200 dark:bg-gray-800
                      ${dragging ? 'dragging' : ''}`}
        />

        {/* Map panel */}
        <div className="flex-1 min-w-0 relative">
          <MapPanel />
        </div>
      </div>
    </div>
  )
}
