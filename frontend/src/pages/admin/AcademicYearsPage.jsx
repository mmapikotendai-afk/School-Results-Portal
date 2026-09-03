import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { Link } from 'react-router-dom'

import AcademicYearFormModal from '@/components/admin/AcademicYearFormModal'
import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import Toast from '@/components/common/Toast'
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmDialog,
  DataTable,
  RowAction,
} from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { academicService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'
import { formatDate } from '@/utils/format'

/**
 * Academic years.
 *
 * Exactly one year is current at a time. Enrollment and teacher assignment both
 * resolve against it, so making one current stands the previous one down -
 * without touching anything already recorded under it.
 */
export function AcademicYearsPage() {
  useDocumentTitle('Academic Years')

  const [formFor, setFormFor] = useState(null)
  const [activating, setActivating] = useState(null)
  const { toast, show, clear } = useToast()

  const years = useAsyncData(() => academicService.listYears(), [])
  const rows = years.data ?? []

  async function activate(row) {
    try {
      await academicService.activateYear(row.id)
      show(`${row.name} is now the current academic year.`)
      years.refresh()
    } catch (err) {
      show(getErrorMessage(err), 'danger')
      throw err
    }
  }

  const columns = [
    {
      key: 'name',
      header: 'Year',
      render: (row) => (
        <div className="flex items-center gap-2">
          <span className="text-ink-900 font-medium">{row.name}</span>
          {row.is_active && <Badge tone="success">Current</Badge>}
        </div>
      ),
    },
    {
      key: 'dates',
      header: 'Dates',
      render: (row) =>
        row.start_date || row.end_date ? (
          <span className="text-ink-600 whitespace-nowrap">
            {formatDate(row.start_date)} – {formatDate(row.end_date)}
          </span>
        ) : (
          <span className="text-ink-400">Not set</span>
        ),
    },
    {
      key: 'term_count',
      header: 'Terms',
      render: (row) => (
        <Link
          to="/admin/terms"
          className="text-brand-700 hover:text-brand-800 font-medium hover:underline"
        >
          {row.term_count}
        </Link>
      ),
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (row) => (
        <div className="flex items-center justify-end gap-0.5">
          {!row.is_active && (
            <RowAction
              icon="circle-check"
              label={`Make ${row.name} the current year`}
              tone="brand"
              onClick={() => setActivating(row)}
            />
          )}
          <RowAction
            icon="pen-to-square"
            label={`Edit ${row.name}`}
            onClick={() => setFormFor({ year: row })}
          />
        </div>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Academic Years"
        description="The calendar everything else hangs from. One year is current at a time."
        actions={
          <Button icon="plus" onClick={() => setFormFor({ year: null })}>
            Add year
          </Button>
        }
      />

      {years.error && (
        <Alert tone="danger" title="Could not load academic years" className="mb-5">
          {years.error}
        </Alert>
      )}

      {rows.length > 0 && !rows.some((y) => y.is_active) && (
        <Alert tone="warning" title="No current academic year" className="mb-5">
          Enrollment and teacher assignment both need a current year. Choose one with the
          tick beside it.
        </Alert>
      )}

      <Card>
        <DataTable
          columns={columns}
          rows={rows}
          loading={years.loading && !years.data}
          empty={
            <EmptyState
              icon="calendar-days"
              title="No academic years yet"
              description="Create a year before adding students, subjects or examinations."
              action={
                <Button icon="plus" onClick={() => setFormFor({ year: null })}>
                  Add academic year
                </Button>
              }
            />
          }
        />
      </Card>

      {formFor && (
        <AcademicYearFormModal
          open
          year={formFor.year}
          onClose={() => setFormFor(null)}
          onSaved={(message) => {
            setFormFor(null)
            show(message)
            years.refresh()
          }}
        />
      )}

      <ConfirmDialog
        open={Boolean(activating)}
        onClose={() => setActivating(null)}
        onConfirm={() => activate(activating)}
        title="Make this the current year?"
        message={`${activating?.name ?? ''} becomes the year that new enrollment and teacher assignment apply to. The year that is currently active will stand down.`}
        detail={
          <p className="text-ink-500 flex items-start gap-2 text-sm">
            <FontAwesomeIcon icon="circle-info" className="mt-0.5 shrink-0" aria-hidden="true" />
            Nothing already recorded changes. Past enrollment and results stay attached to
            the year they were created under.
          </p>
        }
        confirmLabel="Make current"
        icon="circle-check"
      />

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

export default AcademicYearsPage
