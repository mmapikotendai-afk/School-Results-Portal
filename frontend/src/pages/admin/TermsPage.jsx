import { useMemo, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { Link } from 'react-router-dom'

import TermFormModal from '@/components/admin/TermFormModal'
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
  Select,
} from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { academicService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'
import { formatDate } from '@/utils/format'

/**
 * Terms.
 *
 * Examinations belong to a term, so this is the level the school actually works
 * at day to day. The year filter is client-side: the list is small, and
 * filtering locally keeps the control instant.
 */
export function TermsPage() {
  useDocumentTitle('Terms')

  const [formFor, setFormFor] = useState(null)
  const [activating, setActivating] = useState(null)
  const [yearFilter, setYearFilter] = useState('')
  const { toast, show, clear } = useToast()

  const years = useAsyncData(() => academicService.listYears(), [])
  const terms = useAsyncData(() => academicService.listTerms(), [])

  const yearList = useMemo(() => years.data ?? [], [years.data])
  const allTerms = useMemo(() => terms.data ?? [], [terms.data])

  const rows = useMemo(
    () =>
      yearFilter
        ? allTerms.filter((t) => String(t.academic_year_id) === String(yearFilter))
        : allTerms,
    [allTerms, yearFilter],
  )

  async function activate(row) {
    try {
      await academicService.activateTerm(row.id)
      show(`${row.name} is now the current term.`)
      terms.refresh()
    } catch (err) {
      show(getErrorMessage(err), 'danger')
      throw err
    }
  }

  const columns = [
    {
      key: 'name',
      header: 'Term',
      render: (row) => (
        <div className="flex items-center gap-2">
          <span className="text-ink-900 font-medium">{row.name}</span>
          {row.is_active && <Badge tone="success">Current</Badge>}
        </div>
      ),
    },
    {
      key: 'academic_year_name',
      header: 'Academic year',
      render: (row) => row.academic_year_name ?? '—',
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
      key: 'examination_count',
      header: 'Examinations',
      render: (row) => (
        <Link
          to="/admin/examinations"
          className="text-brand-700 hover:text-brand-800 font-medium hover:underline"
        >
          {row.examination_count}
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
              label={`Make ${row.name} the current term`}
              tone="brand"
              onClick={() => setActivating(row)}
            />
          )}
          <RowAction
            icon="pen-to-square"
            label={`Edit ${row.name}`}
            onClick={() => setFormFor({ term: row })}
          />
        </div>
      ),
    },
  ]

  const noYears = !years.loading && yearList.length === 0

  return (
    <div>
      <PageHeader
        title="Terms"
        description="Examinations belong to a term. One term is current at a time."
        actions={
          <Button
            icon="plus"
            onClick={() => setFormFor({ term: null })}
            disabled={noYears}
            title={noYears ? 'Create an academic year first' : undefined}
          >
            Add term
          </Button>
        }
      />

      {(years.error || terms.error) && (
        <Alert tone="danger" title="Could not load terms" className="mb-5">
          {years.error || terms.error}
        </Alert>
      )}

      {noYears && (
        <Alert tone="warning" title="Create an academic year first" className="mb-5">
          A term has to belong to a year.{' '}
          <Link to="/admin/academic-years" className="font-medium underline">
            Add an academic year
          </Link>{' '}
          and then come back.
        </Alert>
      )}

      <Card>
        {yearList.length > 1 && (
          <div className="border-ink-200 flex flex-wrap items-center gap-3 border-b px-5 py-3">
            <Select
              label=""
              aria-label="Filter by academic year"
              value={yearFilter}
              onChange={(e) => setYearFilter(e.target.value)}
              placeholder="All academic years"
              options={yearList.map((y) => ({ value: y.id, label: y.name }))}
              className="w-full sm:w-56"
            />
            {yearFilter && (
              <Button variant="ghost" size="sm" icon="xmark" onClick={() => setYearFilter('')}>
                Clear
              </Button>
            )}
            <span className="text-ink-500 ml-auto text-sm">
              {rows.length} {rows.length === 1 ? 'term' : 'terms'}
            </span>
          </div>
        )}

        <DataTable
          columns={columns}
          rows={rows}
          loading={terms.loading && !terms.data}
          empty={
            <EmptyState
              icon="calendar-day"
              title={
                yearFilter && allTerms.length
                  ? 'No terms in that year'
                  : 'No terms yet'
              }
              description={
                yearFilter && allTerms.length
                  ? 'Try a different academic year, or clear the filter.'
                  : yearList.length
                    ? 'Add a term to the academic year so examinations have somewhere to sit.'
                    : 'Create an academic year first.'
              }
              action={
                yearFilter && allTerms.length ? (
                  <Button variant="secondary" icon="xmark" onClick={() => setYearFilter('')}>
                    Clear filter
                  </Button>
                ) : (
                  yearList.length > 0 && (
                    <Button icon="plus" onClick={() => setFormFor({ term: null })}>
                      Add term
                    </Button>
                  )
                )
              }
            />
          }
        />
      </Card>

      {formFor && (
        <TermFormModal
          open
          term={formFor.term}
          years={yearList}
          onClose={() => setFormFor(null)}
          onSaved={(message) => {
            setFormFor(null)
            show(message)
            terms.refresh()
            years.refresh()
          }}
        />
      )}

      <ConfirmDialog
        open={Boolean(activating)}
        onClose={() => setActivating(null)}
        onConfirm={() => activate(activating)}
        title="Make this the current term?"
        message={`${activating?.name ?? ''} becomes the current term. The dashboard will report on its examinations.`}
        detail={
          <p className="text-ink-500 flex items-start gap-2 text-sm">
            <FontAwesomeIcon icon="circle-info" className="mt-0.5 shrink-0" aria-hidden="true" />
            Nothing already recorded changes. Past results stay attached to the term they
            were created under.
          </p>
        }
        confirmLabel="Make current"
        icon="circle-check"
      />

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

export default TermsPage
