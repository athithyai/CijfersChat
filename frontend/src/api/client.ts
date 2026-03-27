/** Typed fetch wrapper for the CijfersChat backend API. */

import type { ChatRequest, ChatResponse, MapPlan, PlanRequest } from '../types'

const BASE = '/api'

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function post<TReq, TRes>(path: string, body: TReq): Promise<TRes> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const json = await res.json()
      detail = json.detail ?? detail
    } catch { /* ignore */ }
    throw new ApiError(res.status, detail)
  }

  return res.json() as Promise<TRes>
}

async function get<TRes>(path: string): Promise<TRes> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    throw new ApiError(res.status, `HTTP ${res.status}`)
  }
  return res.json() as Promise<TRes>
}

// ── Public API ────────────────────────────────────────────────────────────────

export const api = {
  chat: (req: ChatRequest) =>
    post<ChatRequest, ChatResponse>('/chat', req),

  plan: (req: { message: string; history: ChatRequest['history'] }) =>
    post<typeof req, MapPlan>('/plan', req),

  mapData: (plan: MapPlan) =>
    post<{ plan: MapPlan }, { geojson: import('../types').ChoroplethFeatureCollection; message: string; warnings: string[] }>(
      '/map-data', { plan }
    ),

  boundaries: (level: import('../types').GeographyLevel, scope?: string | null) => {
    const params = new URLSearchParams({ level })
    if (scope) params.set('scope', scope)
    return get<import('../types').ChoroplethFeatureCollection>(`/boundaries?${params}`)
  },

  health: () => get<{ status: string }>('/health'),
}

export { ApiError }
