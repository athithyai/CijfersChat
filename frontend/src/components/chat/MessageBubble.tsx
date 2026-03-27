import clsx from 'clsx'
import { PlanCard } from './PlanCard'
import type { Message } from '../../types'
import { LoadingDots } from './LoadingDots'

interface Props {
  message: Message
  isStreaming?: boolean
  onRetry?: () => void
}

function formatTime(ts: number) {
  return new Intl.DateTimeFormat('nl-NL', { hour: '2-digit', minute: '2-digit' }).format(new Date(ts))
}

export function MessageBubble({ message, isStreaming, onRetry }: Props) {
  const isUser   = message.role === 'user'
  const isError  = message.role === 'error'
  const isSystem = message.role === 'system'

  // ── System notification (region selected, etc.) ───────────────────────────
  if (isSystem) {
    return (
      <div className="flex justify-center my-1 animate-[slideUp_0.2s_ease-out]">
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full
                        bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800
                        text-amber-700 dark:text-amber-300 text-xs">
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div
      className={clsx(
        'flex gap-3 animate-[slideUp_0.25s_ease-out] message-enter',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div
        className={clsx(
          'w-7 h-7 rounded-full shrink-0 flex items-center justify-center text-xs font-bold',
          isUser
            ? 'bg-brand-600 text-white'
            : isError
            ? 'bg-red-500 text-white'
            : 'bg-gradient-to-br from-emerald-400 to-cyan-500 text-white'
        )}
      >
        {isUser ? 'U' : isError ? '!' : 'AI'}
      </div>

      {/* Bubble */}
      <div className={clsx('flex flex-col max-w-[85%]', isUser ? 'items-end' : 'items-start')}>
        <div
          className={clsx(
            'px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed',
            isUser
              ? 'bg-brand-600 text-white rounded-tr-sm'
              : isError
              ? 'bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800 rounded-tl-sm'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-tl-sm'
          )}
        >
          {isStreaming ? (
            <LoadingDots />
          ) : isError ? (
            <div className="space-y-2">
              <p className="whitespace-pre-wrap">{message.content}</p>
              {onRetry && (
                <button
                  onClick={onRetry}
                  className="text-xs font-medium px-2.5 py-1 rounded-md
                             bg-red-100 dark:bg-red-900 hover:bg-red-200 dark:hover:bg-red-800
                             text-red-700 dark:text-red-300 border border-red-200 dark:border-red-700
                             transition-colors"
                >
                  ↺ Try again
                </button>
              )}
            </div>
          ) : (
            <p className="whitespace-pre-wrap">{message.content}</p>
          )}
        </div>

        {/* Plan card (assistant only) */}
        {!isStreaming && message.plan && (
          <div className="w-full mt-1">
            <PlanCard plan={message.plan} />
          </div>
        )}

        {/* Warnings */}
        {message.warnings && message.warnings.length > 0 && (
          <div className="mt-1 space-y-1">
            {message.warnings.map((w, i) => (
              <p key={i} className="text-xs text-amber-600 dark:text-amber-400 flex items-start gap-1">
                <span>⚠</span>
                <span>{w}</span>
              </p>
            ))}
          </div>
        )}

        {/* Timestamp */}
        <span className="text-[10px] text-gray-400 dark:text-gray-600 mt-1 px-1">
          {formatTime(message.timestamp)}
        </span>
      </div>
    </div>
  )
}
