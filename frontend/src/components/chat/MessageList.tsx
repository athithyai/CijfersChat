import { useEffect, useRef } from 'react'
import { useChatStore } from '../../store/chatStore'
import { MessageBubble } from './MessageBubble'
import { LoadingDots } from './LoadingDots'

const EXAMPLE_QUERIES = [
  'Toon bevolkingsdichtheid per gemeente in Nederland',
  'Show average WOZ house value by wijk in Utrecht',
  'Zoom into Amsterdam at buurt level — population',
  'Compare income per person across gemeenten in Noord-Holland',
]

export function MessageList() {
  const messages = useChatStore(s => s.messages)
  const isLoading = useChatStore(s => s.isLoading)
  const sendMessage = useChatStore(s => s.sendMessage)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 gap-6
                      text-center custom-scrollbar overflow-y-auto">
        {/* Welcome */}
        <div>
          <div className="w-14 h-14 rounded-2xl bg-brand-600 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9
                   7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1
                   1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
            CijfersChat
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 max-w-xs">
            Ask about Dutch regional statistics and see the data on the map instantly.
          </p>
        </div>

        {/* Example queries */}
        <div className="w-full space-y-2">
          <p className="text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wider">
            Try asking
          </p>
          {EXAMPLE_QUERIES.map(q => (
            <button
              key={q}
              onClick={() => sendMessage(q)}
              className="w-full text-left text-sm px-3.5 py-2.5 rounded-xl
                         bg-gray-50 dark:bg-gray-800 hover:bg-brand-50 dark:hover:bg-gray-700
                         text-gray-700 dark:text-gray-300 hover:text-brand-700
                         dark:hover:text-brand-300 border border-gray-200 dark:border-gray-700
                         hover:border-brand-300 dark:hover:border-brand-600
                         transition-all duration-150"
            >
              {q}
            </button>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4 min-h-0">
      {messages.map((msg, index) => {
        let onRetry: (() => void) | undefined
        if (msg.role === 'error') {
          const prevUser = [...messages].slice(0, index).reverse().find(m => m.role === 'user')
          if (prevUser) onRetry = () => sendMessage(prevUser.content)
        }
        return <MessageBubble key={msg.id} message={msg} onRetry={onRetry} />
      })}

      {/* Loading bubble */}
      {isLoading && (
        <div className="flex gap-3">
          <div className="w-7 h-7 rounded-full shrink-0 flex items-center justify-center text-xs font-bold
                          bg-gradient-to-br from-emerald-400 to-cyan-500 text-white">
            AI
          </div>
          <div className="px-3.5 py-2.5 rounded-2xl rounded-tl-sm
                          bg-gray-100 dark:bg-gray-800">
            <LoadingDots />
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
