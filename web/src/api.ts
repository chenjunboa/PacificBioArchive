export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export type Media = {
  mediaId: string
  owner: string
  filename: string
  contentType: string
  size: number
  checksumSha256: string
  status: 'RESERVED' | 'UPLOADED' | 'PROCESSING' | 'READY' | 'FAILED' | 'DELETING'
  tags: Record<string, number>
  originalUrl?: string
  thumbnailUrl?: string
  modelVersion?: string
  error?: string
  createdAt: string
}

export type Species = {
  tag: string
  commonName: string
}

export type UploadStage =
  | { step: 'hashing'; label: string }
  | { step: 'reserved'; label: string; mediaId: string }
  | { step: 'uploading'; label: string; mediaId: string }
  | { step: 'polling'; label: string; media: Media }

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

export function apiErrorMessage(reason: unknown): string {
  if (reason instanceof ApiError) {
    if (reason.status === 401) return 'Session expired. Please sign in again.'
    if (reason.status === 403) return `You do not have permission to modify this media. ${reason.message}`
    if (reason.status === 409) return `File content already exists. ${reason.message}`
    if (reason.status === 413) return 'The selected file exceeds the upload size limit.'
    if (reason.status === 422) return `The request is invalid: ${reason.message}`
    if (reason.status >= 500) return 'The cloud service is still starting or temporarily unavailable. Please retry shortly.'
    return reason.message
  }
  if (reason instanceof TypeError) {
    return 'Network request failed. The API may be starting up; please retry shortly.'
  }
  return reason instanceof Error ? reason.message : 'Request failed'
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

function assertSupportedFile(file: File) {
  const imageLimit = 20 * 1024 * 1024
  const videoLimit = 100 * 1024 * 1024
  if (['image/jpeg', 'image/png'].includes(file.type) && file.size > imageLimit) {
    throw new ApiError(413, 'Images must be 20 MB or smaller.')
  }
  if (['video/mp4', 'video/quicktime'].includes(file.type) && file.size > videoLimit) {
    throw new ApiError(413, 'Videos must be 100 MB or smaller.')
  }
  if (!['image/jpeg', 'image/png', 'video/mp4', 'video/quicktime'].includes(file.type)) {
    throw new ApiError(422, 'Supported types are JPG, JPEG, PNG, MP4 and MOV.')
  }
}

export async function uploadFile(
  file: File,
  token: string,
  onStage?: (stage: UploadStage) => void,
): Promise<Media> {
  assertSupportedFile(file)
  onStage?.({ step: 'hashing', label: 'Calculating SHA-256 checksum...' })
  const checksumSha256 = await sha256(file)
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
        checksumSha256,
      }),
    },
  )
  onStage?.({ step: 'reserved', label: 'Upload reservation created.', mediaId: reservation.mediaId })
  const directUpload = /^https?:\/\//.test(reservation.uploadUrl)
  let sent: Response
  onStage?.({ step: 'uploading', label: 'Uploading media bytes...', mediaId: reservation.mediaId })
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
    onStage?.({ step: 'polling', label: `Backend status: ${media.status}`, media })
    if (media.status === 'READY' || media.status === 'FAILED') return media
    await new Promise(resolve => setTimeout(resolve, 5000))
  }
  throw new Error('Processing did not finish within 15 minutes')
}
