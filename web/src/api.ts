export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export type Media = {
  mediaId: string
  owner: string
  filename: string
  contentType: string
  size: number
  status: 'RESERVED' | 'UPLOADED' | 'PROCESSING' | 'READY' | 'FAILED' | 'DELETING'
  tags: Record<string, number>
  originalUrl?: string
  thumbnailUrl?: string
  modelVersion?: string
  error?: string
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

export async function api<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...init.headers,
    },
  })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const payload = await response.json()
      detail = typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail)
    } catch {
      // Keep the HTTP status text when the response is not JSON.
    }
    throw new ApiError(response.status, detail)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function sha256(file: File): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer())
  return [...new Uint8Array(digest)].map(value => value.toString(16).padStart(2, '0')).join('')
}

export async function uploadFile(file: File, token: string): Promise<Media> {
  const reservation = await api<{
    mediaId: string
    uploadUrl: string
    uploadMethod: 'PUT' | 'POST'
    uploadFields: Record<string, string>
  }>(
    '/uploads/init',
    token,
    {
      method: 'POST',
      body: JSON.stringify({
        filename: file.name,
        contentType: file.type,
        size: file.size,
        checksumSha256: await sha256(file),
      }),
    },
  )
  const directUpload = /^https?:\/\//.test(reservation.uploadUrl)
  let sent: Response
  if (reservation.uploadMethod === 'POST') {
    const form = new FormData()
    Object.entries(reservation.uploadFields).forEach(([key, value]) => form.append(key, value))
    form.append('file', file)
    sent = await fetch(reservation.uploadUrl, { method: 'POST', body: form })
  } else {
    const target = directUpload
      ? reservation.uploadUrl
      : `${API_BASE.replace('/api/v1', '')}${reservation.uploadUrl}`
    sent = await fetch(target, {
      method: 'PUT',
      headers: directUpload
        ? { 'Content-Type': file.type }
        : { Authorization: `Bearer ${token}` },
      body: file,
    })
  }
  if (!sent.ok) throw new ApiError(sent.status, await sent.text())
  for (let attempt = 0; attempt < 180; attempt += 1) {
    const media = await api<Media>(`/media/${reservation.mediaId}`, token)
    if (media.status === 'READY' || media.status === 'FAILED') return media
    await new Promise(resolve => setTimeout(resolve, 5000))
  }
  throw new Error('Processing did not finish within 15 minutes')
}
