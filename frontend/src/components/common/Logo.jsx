import { cx } from '@/utils/format'
import { APP_NAME, SCHOOL } from '@/utils/constants'

/** School crest plus wordmark. Used in the masthead, sidebar and auth screens. */
export function Logo({ size = 'md', inverted = false, showText = true, className }) {
  // The crest is taller than it is wide, so it is sized by height and left to
  // find its own width. A square box would squash it.
  const crestSize =
    size === 'sm' ? 'h-8' : size === 'lg' ? 'h-14' : size === 'xl' ? 'h-40' : 'h-10'
  const titleSize = size === 'sm' ? 'text-sm' : size === 'lg' ? 'text-xl' : 'text-base'

  const crest = (
    <img
      src="/logo.png"
      alt=""
      aria-hidden="true"
      className={cx(crestSize, 'w-auto shrink-0')}
    />
  )

  return (
    <div className={cx('flex items-center gap-3', className)}>
      {/* The crest carries a navy body and black lettering, so on the dark
          chrome it sits on a light chip rather than disappearing into it. */}
      {inverted ? (
        <span className="flex shrink-0 items-center bg-white px-1.5 py-1">
          {crest}
        </span>
      ) : (
        crest
      )}
      {showText && (
        <div className="min-w-0 leading-tight">
          <p
            className={cx(
              'font-serif font-semibold tracking-tight',
              titleSize,
              inverted ? 'text-white' : 'text-brand-950',
            )}
          >
            {SCHOOL.shortName}
          </p>
          <p
            className={cx(
              'text-[10px] font-bold tracking-[0.16em] uppercase',
              inverted ? 'text-brand-200' : 'text-ink-500',
            )}
          >
            {APP_NAME}
          </p>
        </div>
      )}
    </div>
  )
}

export default Logo
