const CBS_ICON = 'https://cdn.cbs.nl/cdn/images/favicon.ico'

interface Props {
  size?: number
  className?: string
}

export function LogoIcon({ size = 32, className }: Props) {
  return (
    <img
      src={CBS_ICON}
      width={size}
      height={size}
      alt="CBS"
      className={className}
    />
  )
}

export function LogoWordmark({ iconSize = 28 }: { iconSize?: number }) {
  return (
    <div className="flex items-center gap-2">
      <img src={CBS_ICON} width={iconSize} height={iconSize} alt="CBS" />
      <span className="font-display font-medium text-sm tracking-tight leading-none">
        <span style={{ color: '#271D6C' }}>Cijfers</span><span style={{ color: '#00A1CD' }}>Chat</span>
      </span>
    </div>
  )
}
