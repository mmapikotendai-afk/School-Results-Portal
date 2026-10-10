import { lazy, Suspense } from 'react'
import { PageLoader } from '@/components/ui'
import { Navigate, Route, Routes } from 'react-router-dom'

import ProtectedRoute from '@/components/routing/ProtectedRoute'
import PublicOnlyRoute from '@/components/routing/PublicOnlyRoute'
import AuthLayout from '@/layouts/AuthLayout'
import PortalLayout from '@/layouts/PortalLayout'
const ForgotPasswordPage = lazy(() => import('@/pages/ForgotPasswordPage'))
const LandingPage = lazy(() => import('@/pages/LandingPage'))
const LoginPage = lazy(() => import('@/pages/LoginPage'))
const FirstPasswordChangePage = lazy(() => import('@/pages/FirstPasswordChangePage'))
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'))
const SettingsPage = lazy(() => import('@/pages/SettingsPage'))
const AcademicYearsPage = lazy(() => import('@/pages/admin/AcademicYearsPage'))
const AdminDashboard = lazy(() => import('@/pages/admin/AdminDashboard'))
const ClassesPage = lazy(() => import('@/pages/admin/ClassesPage'))
const ExaminationsPage = lazy(() => import('@/pages/admin/ExaminationsPage'))
const ReportsPage = lazy(() => import('@/pages/admin/ReportsPage'))
const ProgressionPage = lazy(() => import('@/pages/admin/ProgressionPage'))
const ResetRequestsPage = lazy(() => import('@/pages/admin/ResetRequestsPage'))
const ResultSubmissionsPage = lazy(() => import('@/pages/admin/ResultSubmissionsPage'))
const ResultsPage = lazy(() => import('@/pages/admin/ResultsPage'))
const SchoolPage = lazy(() => import('@/pages/admin/SchoolPage'))
const StudentImportPage = lazy(() => import('@/pages/admin/StudentImportPage'))
const StudentsPage = lazy(() => import('@/pages/admin/StudentsPage'))
const SubjectsPage = lazy(() => import('@/pages/admin/SubjectsPage'))
const TeachersPage = lazy(() => import('@/pages/admin/TeachersPage'))
const TermsPage = lazy(() => import('@/pages/admin/TermsPage'))
const PreviousResultsPage = lazy(() => import('@/pages/student/PreviousResultsPage'))
const StudentDashboard = lazy(() => import('@/pages/student/StudentDashboard'))
const StudentDownloadsPage = lazy(() => import('@/pages/student/StudentDownloadsPage'))
const StudentResultsPage = lazy(() => import('@/pages/student/StudentResultsPage'))
const DownloadsPage = lazy(() => import('@/pages/teacher/DownloadsPage'))
const MarkSheetPage = lazy(() => import('@/pages/teacher/MarkSheetPage'))
const MyResultsPage = lazy(() => import('@/pages/teacher/MyResultsPage'))
const SubmissionStatusPage = lazy(() => import('@/pages/teacher/SubmissionStatusPage'))
const TeacherDashboard = lazy(() => import('@/pages/teacher/TeacherDashboard'))
const UploadResultsPage = lazy(() => import('@/pages/teacher/UploadResultsPage'))
import { ROLES } from '@/utils/roles'

/**
 * Route table.
 *
 * Public:    /                    landing page
 *            /login               sign-in, redirects away if already signed in
 * Protected: /admin/*             ADMIN only
 *            /teacher/*           TEACHER only
 *            /student/*           STUDENT only
 *
 * There is no /register route, and no endpoint behind one.
 *
 * These guards decide what to *render*. They are not the security boundary:
 * every protected endpoint re-checks the token and the role on the server, so
 * bypassing a guard in the browser reveals nothing.
 */
export function App() {
  return (
    <Suspense fallback={<PageLoader label="Loading page" />}><Routes>
      <Route path="/" element={<LandingPage />} />

      <Route element={<PublicOnlyRoute />}>
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        </Route>
      </Route>

      <Route
        element={
          <ProtectedRoute
            allowedRoles={[ROLES.ADMIN, ROLES.TEACHER, ROLES.STUDENT]}
            allowPasswordChange
          />
        }
      >
        <Route element={<AuthLayout />}>
          <Route path="/change-password" element={<FirstPasswordChangePage />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allowedRoles={[ROLES.ADMIN]} />}>
        <Route path="/admin" element={<PortalLayout />}>
          <Route index element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="dashboard" element={<AdminDashboard />} />
          <Route path="students" element={<StudentsPage />} />
          <Route path="students/import" element={<StudentImportPage />} />
          <Route path="progression" element={<ProgressionPage />} />
          <Route path="teachers" element={<TeachersPage />} />
          <Route path="reset-requests" element={<ResetRequestsPage />} />
          <Route path="subjects" element={<SubjectsPage />} />
          <Route path="classes" element={<ClassesPage />} />
          <Route path="academic-years" element={<AcademicYearsPage />} />
          <Route path="terms" element={<TermsPage />} />
          <Route path="examinations" element={<ExaminationsPage />} />
          <Route path="submissions" element={<ResultSubmissionsPage />} />
          <Route path="results" element={<ResultsPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          {/* School information also lives as a Settings tab; this route is
              kept so existing links and bookmarks still resolve. */}
          <Route path="school" element={<SchoolPage />} />
          {/* The years and terms screens were once one page. */}
          <Route path="academic" element={<Navigate to="/admin/academic-years" replace />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allowedRoles={[ROLES.TEACHER]} />}>
        <Route path="/teacher" element={<PortalLayout />}>
          <Route index element={<Navigate to="/teacher/dashboard" replace />} />
          <Route path="dashboard" element={<TeacherDashboard />} />
          <Route path="results" element={<MyResultsPage />} />
          <Route path="upload" element={<UploadResultsPage />} />
          <Route path="submissions" element={<SubmissionStatusPage />} />
          <Route path="downloads" element={<DownloadsPage />} />
          <Route
            path="examinations/:examinationId/subjects/:subjectId"
            element={<MarkSheetPage />}
          />
          <Route path="settings" element={<SettingsPage />} />
          {/* The template page became the wider Downloads screen. */}
          <Route path="template" element={<Navigate to="/teacher/downloads" replace />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allowedRoles={[ROLES.STUDENT]} />}>
        <Route path="/student" element={<PortalLayout />}>
          <Route index element={<Navigate to="/student/dashboard" replace />} />
          <Route path="dashboard" element={<StudentDashboard />} />
          <Route path="results" element={<StudentResultsPage />} />
          <Route path="previous" element={<PreviousResultsPage />} />
          <Route path="downloads" element={<StudentDownloadsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes></Suspense>
  )
}

export default App
