import { cx } from '@/utils/format'
import { APP_NAME, SCHOOL } from '@/utils/constants'

/** School crest plus wordmark. Used in the masthead, sidebar and auth screens. */
export function Logo({ size = 'md', inverted = false, showText = true, className }) {
  const crestSize = size === 'sm' ? 'size-8' : size === 'lg' ? 'size-14' : 'size-10'
  const titleSize = size === 'sm' ? 'text-sm' : size === 'lg' ? 'text-xl' : 'text-base'

  return (
    <div className={cx('flex items-center gap-3', className)}>
      <img src="/crest.svg" alt="" aria-hidden="true" className={cx(crestSize, 'shrink-0')} />
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
              'text-xs font-medium tracking-wide uppercase',
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
