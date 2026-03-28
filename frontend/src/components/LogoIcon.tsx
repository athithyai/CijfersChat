/** CijfersChat logo mark — 3×3 choropleth grid.
 *  Dark navy (#091D23) top-left → light cyan (#b3e6f5) bottom-right.
 */

interface Props {
  size?: number
  className?: string
}

export function LogoIcon({ size = 32, className }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="CijfersChat"
    >
      {/* 3×3 choropleth grid — dark navy top-left → light cyan bottom-right */}
      <rect x="2"  y="2"  width="8" height="8" rx="1.5" fill="#091D23" />
      <rect x="12" y="2"  width="8" height="8" rx="1.5" fill="#271D6C" />
      <rect x="22" y="2"  width="8" height="8" rx="1.5" fill="#3d3b8a" />

      <rect x="2"  y="12" width="8" height="8" rx="1.5" fill="#271D6C" />
      <rect x="12" y="12" width="8" height="8" rx="1.5" fill="#00A1CD" />
      <rect x="22" y="12" width="8" height="8" rx="1.5" fill="#40bfda" />

      <rect x="2"  y="22" width="8" height="8" rx="1.5" fill="#3d3b8a" />
      <rect x="12" y="22" width="8" height="8" rx="1.5" fill="#40bfda" />
      <rect x="22" y="22" width="8" height="8" rx="1.5" fill="#b3e6f5" />
    </svg>
  )
}

/** Full wordmark: logo icon + "Cijfers" + "Chat" */
export function LogoWordmark({ iconSize = 28 }: { iconSize?: number }) {
  return (
    <div className="flex items-center gap-2">
      <LogoIcon size={iconSize} />
      <span className="font-display font-medium text-sm tracking-tight leading-none">
        <span style={{ color: '#271D6C' }}>Cijfers</span><span style={{ color: '#00A1CD' }}>Chat</span>
      </span>
    </div>
  )
}
