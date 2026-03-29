/** CBS logo + CijfersChat wordmark */

/** Full wordmark: CBS logo + "Cijfers" + "Chat" */
export function LogoWordmark({ iconSize = 28 }: { iconSize?: number }) {
  return (
    <div className="flex items-center gap-2">
      <img
        src="/favicon.svg"
        width={iconSize * 3}
        height={iconSize}
        alt="CBS"
        style={{ objectFit: 'contain' }}
      />
      <span className="font-display font-medium text-sm tracking-tight leading-none">
        <span style={{ color: '#271D6C' }}>Cijfers</span><span style={{ color: '#00A1CD' }}>Chat</span>
      </span>
    </div>
  )
}
