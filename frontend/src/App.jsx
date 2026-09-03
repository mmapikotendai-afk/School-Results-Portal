import { Navigate, Route, Routes } from 'react-router-dom'

import ProtectedRoute from '@/components/routing/ProtectedRoute'
import PublicOnlyRoute from '@/components/routing/PublicOnlyRoute'
import AuthLayout from '@/layouts/AuthLayout'
import PortalLayout from '@/layouts/PortalLayout'
import LandingPage from '@/pages/LandingPage'
import LoginPage from '@/pages/LoginPage'
import NotFoundPage from '@/pages/NotFoundPage'
import SettingsPage from '@/pages/SettingsPage'
import AcademicYearsPage from '@/pages/admin/AcademicYearsPage'
import AdminDashboard from '@/pages/admin/AdminDashboard'
import ClassesPage from '@/pages/admin/ClassesPage'
import ExaminationsPage from '@/pages/admin/ExaminationsPage'
import ReportsPage from '@/pages/admin/ReportsPage'
import ResultSubmissionsPage from '@/pages/admin/ResultSubmissionsPage'
import ResultsPage from '@/pages/admin/ResultsPage'
import SchoolPage from '@/pages/admin/SchoolPage'
import StudentsPage from '@/pages/admin/StudentsPage'
import SubjectsPage from '@/pages/admin/SubjectsPage'
import TeachersPage from '@/pages/admin/TeachersPage'
import TermsPage from '@/pages/admin/TermsPage'
import PreviousResultsPage from '@/pages/student/PreviousResultsPage'
import StudentDashboard from '@/pages/student/StudentDashboard'
import StudentDownloadsPage from '@/pages/student/StudentDownloadsPage'
import StudentResultsPage from '@/pages/student/StudentResultsPage'
import DownloadsPage from '@/pages/teacher/DownloadsPage'
import MarkSheetPage from '@/pages/teacher/MarkSheetPage'
import MyResultsPage from '@/pages/teacher/MyResultsPage'
import SubmissionStatusPage from '@/pages/teacher/SubmissionStatusPage'
import TeacherDashboard from '@/pages/teacher/TeacherDashboard'
import UploadResultsPage from '@/pages/teacher/UploadResultsPage'
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
    <Routes>
      <Route path="/" element={<LandingPage />} />

      <Route element={<PublicOnlyRoute />}>
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allowedRoles={[ROLES.ADMIN]} />}>
        <Route path="/admin" element={<PortalLayout />}>
          <Route index element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="dashboard" element={<AdminDashboard />} />
          <Route path="students" element={<StudentsPage />} />
          <Route path="teachers" element={<TeachersPage />} />
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
    </Routes>
  )
}

export default App
