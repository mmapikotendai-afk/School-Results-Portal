/**
 * The auth context object and its shared constants.
 *
 * Kept apart from the provider component so the module exports no components:
 * that is what lets Fast Refresh reload the provider without tearing down the
 * whole tree, and it gives consumers something to import without pulling the
 * provider in with it.
 */

import { createContext } from 'react'

export const AuthContext = createContext(null)

/** Why a session ended, so the login page can explain itself. */
export const SIGN_OUT_REASON = {
  USER: 'user',
  EXPIRED: 'token_expired',
  REVOKED: 'token_revoked',
  INACTIVE: 'account_inactive',
  PASSWORD_CHANGED: 'password_changed',
}
