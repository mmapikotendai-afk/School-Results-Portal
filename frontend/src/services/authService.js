/**
 * Authentication calls.
 *
 * There is no register() here and there is no endpoint to call: accounts are
 * issued by administrators. Adding one would need a backend route that does
 * not exist.
 */

import apiClient from '@/services/apiClient'

export const authService = {
  /**
   * POST /auth/login
   * @param identifier username or email address
   * @returns { access_token, token_type, expires_in, user }
   */
  async login(identifier, password) {
    const { data } = await apiClient.post('/auth/login', { identifier, password })
    return data
  },

  /**
   * POST /auth/logout - revokes the token server-side.
   *
   * Never throws: the caller is signing out either way, and a failed request
   * must not leave them stuck in a session they asked to end.
   */
  async logout() {
    try {
      await apiClient.post('/auth/logout')
      return true
    } catch {
      return false
    }
  },

  /** GET /auth/me - restores a session after a page reload. */
  async me() {
    const { data } = await apiClient.get('/auth/me')
    return data
  },

  /**
   * POST /auth/change-password
   * On success the backend invalidates every session, so the caller must sign
   * the user out and send them back to /login.
   */
  async changePassword({ currentPassword, newPassword, confirmPassword }) {
    const { data } = await apiClient.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword,
    })
    return data
  },

  /** GET /auth/password-policy - the same rules the API enforces. */
  async passwordPolicy() {
    const { data } = await apiClient.get('/auth/password-policy')
    return data
  },
}

export default authService
