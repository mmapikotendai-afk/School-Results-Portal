/** Calls against the backend's health/diagnostic endpoints. */

import apiClient from '@/services/apiClient'

export const systemService = {
  /** GET /health - reports API and MySQL status. */
  async health() {
    const { data } = await apiClient.get('/health')
    return data
  },

  /** GET /ping - cheap liveness probe that skips the database. */
  async ping() {
    const { data } = await apiClient.get('/ping')
    return data
  },
}

export default systemService
