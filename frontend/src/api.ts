export interface SessionInfo {
  name: string | null
  total_pages: number
  completed_pages: number
  next_position: number | null
  finished: boolean
}

export interface SavedRating {
  score: number
  comment: string | null
}

export interface PageData {
  position: number
  total_pages: number
  sequence: string
  columns: { slot: string; url: string }[]
  ratings: Record<string, SavedRating>
}

export interface RatingBody {
  client_event_id: string
  position: number
  slot: string
  score: number
  comment: string | null
  viewer_state: Record<string, unknown> | null
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  if (!res.ok) {
    let detail = `Erro ${res.status}`
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      /* body was not JSON */
    }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

const base = (token: string) => `/api/session/${encodeURIComponent(token)}`

export const getSession = (token: string) => request<SessionInfo>(base(token))

export const getPage = (token: string, position: number) =>
  request<PageData>(`${base(token)}/page/${position}`)

export const postRating = (token: string, body: RatingBody) =>
  request<{ event_id: number }>(`${base(token)}/rating`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

// Volumes are sent with Cache-Control, so reading one to the end puts it in the browser cache
// and Niivue's own request for the same URL is answered from there.
export async function prefetchVolume(url: string): Promise<void> {
  try {
    const res = await fetch(url)
    if (res.ok) await res.arrayBuffer()
  } catch {
    /* prefetch is only an optimisation */
  }
}
