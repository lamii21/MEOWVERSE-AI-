export function Sparkle({ size = 14, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true" className={className}>
      <path
        d="M12 0c.9 5.5 3 8 8.5 9.5-5.5 1.5-7.6 4-8.5 9.5-.9-5.5-3-8-8.5-9.5C9 8 11.1 5.5 12 0Z"
        className="fill-peach-300 dark:fill-peach-400"
      />
    </svg>
  );
}
