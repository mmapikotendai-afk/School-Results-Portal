import assert from 'node:assert/strict'
import { createServer as createHttpServer } from 'node:http'
import { once } from 'node:events'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { createServer as createViteServer } from 'vite'
import configFactory from '../vite.config.js'

test('reject a cross-origin API URL that would break session and CSRF cookies', () => {
  const original = process.env.VITE_API_BASE_URL
  try {
    for (const base of ['https://backend.example/api/v1', '//backend.example/api/v1']) {
      process.env.VITE_API_BASE_URL = base
      assert.throws(() => configFactory({ mode: 'test' }), /same-origin path/)
    }
  } finally {
    if (original === undefined) delete process.env.VITE_API_BASE_URL
    else process.env.VITE_API_BASE_URL = original
  }
})

test('Vercel sends logos and API calls to the backend before the SPA fallback', async () => {
  const config = JSON.parse(await readFile(new URL('../vercel.json', import.meta.url)))
  const api = config.rewrites.findIndex((r) => r.source === '/api/:path*')
  const uploads = config.rewrites.findIndex((r) => r.source === '/uploads/:path*')
  const fallback = config.rewrites.findIndex((r) => r.destination === '/index.html')
  assert.ok(api >= 0 && uploads >= 0 && api < fallback && uploads < fallback)
  assert.equal(new URL(config.rewrites[uploads].destination).origin,
    new URL(config.rewrites[api].destination).origin)
  assert.equal(new URL(config.rewrites[uploads].destination).pathname, '/uploads/:path*')
})

test('development proxy forwards image bytes, session cookies, and CSRF headers', async () => {
  const image = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])
  let healthBody = { status: 'degraded', database: 'disconnected' }
  const backend = createHttpServer((req, res) => {
    if (req.url === '/api/v1/health') {
      res.writeHead(503, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify(healthBody))
    } else if (req.url === '/uploads/logos/crest.png') {
      res.writeHead(200, { 'Content-Type': 'image/png' })
      res.end(image)
    } else if (req.url === '/api/v1/auth/login') {
      res.writeHead(200, { 'Set-Cookie': 'srp_session=test; HttpOnly; Path=/; SameSite=Lax' })
      res.end('signed in')
    } else if (req.url === '/api/v1/auth/logout') {
      assert.equal(req.headers.cookie, 'srp_session=test; srp_csrf=proof')
      assert.equal(req.headers['x-csrf-token'], 'proof')
      res.end('signed out')
    } else {
      res.writeHead(404).end()
    }
  })
  backend.listen(0, '127.0.0.1')
  await once(backend, 'listening')
  let vite
  let frontend
  const original = process.env.VITE_API_PROXY_TARGET
  try {
    process.env.VITE_API_PROXY_TARGET = `http://127.0.0.1:${backend.address().port}`
    const config = configFactory({ mode: 'test' })
    vite = await createViteServer({
      ...config, configFile: false, plugins: [], appType: 'custom',
      server: { ...config.server, middlewareMode: true, hmr: false },
      optimizeDeps: { noDiscovery: true, include: [] },
    })
    frontend = createHttpServer(vite.middlewares)
    frontend.listen(0, '127.0.0.1')
    await once(frontend, 'listening')
    const origin = `http://127.0.0.1:${frontend.address().port}`
    const logo = await fetch(`${origin}/uploads/logos/crest.png`)
    assert.equal(logo.headers.get('content-type'), 'image/png')
    assert.deepEqual(Buffer.from(await logo.arrayBuffer()), image)
    const login = await fetch(`${origin}/api/v1/auth/login`, { method: 'POST' })
    assert.match(login.headers.get('set-cookie'), /srp_session=test; HttpOnly/)
    const logout = await fetch(`${origin}/api/v1/auth/logout`, {
      method: 'POST', headers: { Cookie: 'srp_session=test; srp_csrf=proof', 'X-CSRF-Token': 'proof' },
    })
    assert.equal(await logout.text(), 'signed out')

    // Exercise the real Axios response handling, including HTTP 503.
    const { default: apiClient } = await vite.ssrLoadModule('/src/services/apiClient.js')
    const { default: systemService } = await vite.ssrLoadModule('/src/services/systemService.js')
    apiClient.defaults.baseURL = `${origin}/api/v1`
    assert.deepEqual(await systemService.health(), healthBody)
    healthBody = { detail: 'Generic upstream outage' }
    await assert.rejects(() => systemService.health(), /Unable to read the API health status/)
  } finally {
    if (original === undefined) delete process.env.VITE_API_PROXY_TARGET
    else process.env.VITE_API_PROXY_TARGET = original
    if (frontend) await new Promise((resolve) => frontend.close(resolve))
    if (vite) await vite.close()
    await new Promise((resolve) => backend.close(resolve))
  }
})
