/** CBS logo + CijfersChat wordmark */

interface Props {
  size?: number
  className?: string
}

/** CBS logo icon — used wherever the old 3×3 grid appeared */
export function LogoIcon({ size = 32, className }: Props) {
  return (
    <img
      src="/favicon.svg"
      width={size * 3}
      height={size}
      alt="CBS"
      className={className}
      style={{ objectFit: 'contain' }}
    />
  )
}

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
