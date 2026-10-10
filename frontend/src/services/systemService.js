/** Calls against the backend's health/diagnostic endpoints. */

import apiClient from '@/services/apiClient'

export const systemService = {
  /** GET /health - reports API and MySQL status. */
  async health() {
    const { data } = await apiClient.get('/health', {
      // A degraded API is reachable and has a useful status payload.
      validateStatus: (status) => status === 200 || status === 503,
    })
    if (!['ok', 'degraded'].includes(data?.status)) {
      throw new Error('Unable to read the API health status.')
    }
    return data
  },

  /** GET /ping - cheap liveness probe that skips the database. */
  async ping() {
    const { data } = await apiClient.get('/ping')
    return data
  },
}

export default systemService
