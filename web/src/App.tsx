import { FormEvent, useEffect, useMemo, useState } from 'react'
import {
  Bell,
  CheckCircle2,
  Database,
  ExternalLink,
  FileSearch,
  LogOut,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Tags,
  Trash2,
  Upload,
  X,
} from 'lucide-react'
import { confirmSignUp, fetchAuthSession, signIn, signOut, signUp } from 'aws-amplify/auth'
import { API_BASE, Media, Species, api, apiErrorMessage, uploadFile } from './api'

type Tab = 'upload' | 'search' | 'manage' | 'notifications'
type Message = { kind: 'ok' | 'error' | 'info'; text: string }
type QueryMode = 'tags' | 'species' | 'thumbnail' | 'file'
type TagRow = { id: number; tag: string; count: string }

const acceptedMediaTypes = 'image/jpeg,image/png,video/mp4,video/quicktime'
const apiOrigin = API_BASE.replace('/api/v1', '')

function decodeToken(token: string): { sub?: string; email?: string } {
  try {
    const [, payload] = token.split('.')
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const decoded = JSON.parse(atob(normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=')))
    return { sub: decoded.sub, email: decoded.email }
  } catch {
    return {}
  }
}

function formatBytes(value: number): string {
  if (value >= 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`
  if (value >= 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${value} B`
}

function formatDate(value?: string): string {
  if (!value) return 'Unknown time'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function parseList(value: string): string[] {
  return value.split(/[\n,]+/).map(item => item.trim()).filter(Boolean)
}

async function validateVideoDuration(file: File) {
  if (!file.type.startsWith('video/')) return
  const url = URL.createObjectURL(file)
  try {
    const duration = await new Promise<number>((resolve, reject) => {
      const video = document.createElement('video')
      video.preload = 'metadata'
      video.onloadedmetadata = () => resolve(video.duration)
      video.onerror = () => reject(new Error('Could not read the selected video duration.'))
      video.src = url
    })
    if (Number.isFinite(duration) && duration > 60) {
      throw new Error('Videos must be 60 seconds or shorter.')
    }
  } finally {
    URL.revokeObjectURL(url)
  }
}

function Status({ kind, children }: { kind: 'ok' | 'error' | 'info'; children: string }) {
  return <div className={`status ${kind}`}>{children}</div>
}

function Login({ onLogin }: { onLogin: (token: string, email: string) => void }) {
  const cloudMode = Boolean(import.meta.env.VITE_COGNITO_USER_POOL_ID)
  const [email, setEmail] = useState(cloudMode ? '' : 'researcher@example.com')
  const [password, setPassword] = useState('')
  const [givenName, setGivenName] = useState('')
  const [familyName, setFamilyName] = useState('')
  const [confirmationCode, setConfirmationCode] = useState('')
  const [mode, setMode] = useState<'signIn' | 'signUp' | 'confirm'>('signIn')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setNotice('')
    try {
      if (cloudMode) {
        if (mode === 'signUp') {
          const result = await signUp({
            username: email,
            password,
            options: {
              userAttributes: { email, given_name: givenName, family_name: familyName },
            },
          })
          if (result.nextStep.signUpStep === 'CONFIRM_SIGN_UP') {
            setMode('confirm')
            setNotice('Check your email and enter the confirmation code.')
          } else {
            setMode('signIn')
            setNotice('Account created. You can now sign in.')
          }
        } else if (mode === 'confirm') {
          await confirmSignUp({ username: email, confirmationCode })
          setMode('signIn')
          setNotice('Email confirmed. You can now sign in.')
        } else {
          await signIn({ username: email, password })
          const session = await fetchAuthSession()
          const idToken = session.tokens?.idToken?.toString()
          if (!idToken) throw new Error('Cognito did not return an ID token')
          onLogin(idToken, email)
        }
      } else {
        const response = await fetch(`${API_BASE}/auth/dev-token`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, givenName: 'Local', familyName: 'Researcher' }),
        })
        if (!response.ok) throw new Error('Could not create local development session')
        onLogin((await response.json()).accessToken, email)
      }
    } catch (reason) {
      setError(apiErrorMessage(reason))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="login-shell">
      <section className="login-story">
        <div className="brand-mark"><Database size={28} /></div>
        <p className="eyebrow">Pacific BioArchive</p>
        <h1>Every observation.<br />Protected and discoverable.</h1>
        <p className="login-copy">
          A multi-cloud archive for wildlife researchers working across forests, coastlines,
          and desert habitats.
        </p>
        <div className="trust-row"><ShieldCheck size={18} /> Protected by AWS Cognito</div>
      </section>
      <form className="login-card" onSubmit={submit}>
        <p className="eyebrow">Researcher access</p>
        <h2>{mode === 'signUp' ? 'Create account' : mode === 'confirm' ? 'Verify email' : 'Welcome back'}</h2>
        <label>Email<input type="email" value={email} onChange={e => setEmail(e.target.value)} required /></label>
        {cloudMode && mode === 'signUp' && <>
          <label>Given name<input value={givenName} onChange={e => setGivenName(e.target.value)} required /></label>
          <label>Family name<input value={familyName} onChange={e => setFamilyName(e.target.value)} required /></label>
        </>}
        {cloudMode && mode !== 'confirm' && <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} required /></label>}
        {cloudMode && mode === 'confirm' && <label>Confirmation code<input inputMode="numeric" value={confirmationCode} onChange={e => setConfirmationCode(e.target.value)} required /></label>}
        {!cloudMode && <p className="local-note">Local prototype mode: a development JWT is issued by the API.</p>}
        {notice && <Status kind="info">{notice}</Status>}
        {error && <Status kind="error">{error}</Status>}
        <button className="primary" disabled={busy}>
          {busy ? 'Please wait...' : mode === 'signUp' ? 'Create account' : mode === 'confirm' ? 'Confirm email' : 'Sign in'}
        </button>
        {cloudMode && mode !== 'confirm' && <button type="button" onClick={() => setMode(mode === 'signIn' ? 'signUp' : 'signIn')}>
          {mode === 'signIn' ? 'Create a new account' : 'Back to sign in'}
        </button>}
      </form>
    </main>
  )
}

function UploadPanel({
  token,
  currentUserSub,
  onMedia,
  onManage,
}: {
  token: string
  currentUserSub?: string
  onMedia: (media: Media) => void
  onManage: (media: Media) => void
}) {
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<Message | null>(null)
  const [statusTrail, setStatusTrail] = useState<string[]>([])
  const [completed, setCompleted] = useState<Media | null>(null)

  async function submit() {
    if (!file) return
    setBusy(true)
    setMessage({ kind: 'info', text: 'Preparing upload.' })
    setStatusTrail([])
    try {
      await validateVideoDuration(file)
      const media = await uploadFile(file, token, stage => {
        setMessage({ kind: 'info', text: stage.label })
        if (stage.step === 'polling') {
          setStatusTrail(previous => [...previous.filter(item => item !== stage.media.status), stage.media.status])
        } else {
          setStatusTrail(previous => [...previous, stage.label])
        }
      })
      onMedia(media)
      setCompleted(media)
      setMessage(media.status === 'READY'
        ? { kind: 'ok', text: `Ready. Detected ${Object.keys(media.tags).length} species tag(s).` }
        : { kind: 'error', text: `${media.error ?? 'Processing failed.'} Please retry after checking the file type and cloud worker status.` })
    } catch (reason) {
      setMessage({ kind: 'error', text: apiErrorMessage(reason) })
    } finally {
      setBusy(false)
    }
  }

  return <section className="panel">
    <div className="panel-heading"><div><p className="eyebrow">Ingestion pipeline</p><h2>Upload an observation</h2></div><Upload /></div>
    <div className="drop-zone">
      <Upload size={32} />
      <strong>{file ? file.name : 'Choose an image or short video'}</strong>
      <span>JPG, JPEG and PNG up to 20 MB. MP4 and MOV up to 100 MB and 60 seconds.</span>
      <input aria-label="Media file" type="file" accept={acceptedMediaTypes} onChange={e => setFile(e.target.files?.[0] ?? null)} />
      {file && <small>{file.type || 'Unknown type'} - {formatBytes(file.size)}</small>}
    </div>
    <button className="primary" onClick={submit} disabled={!file || busy}>{busy ? 'Working...' : 'Upload and identify'}</button>
    {statusTrail.length > 0 && <ol className="status-steps">{statusTrail.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ol>}
    {message && <Status kind={message.kind}>{message.text}</Status>}
    {completed && <div className="single-result"><ResultCard media={completed} token={token} currentUserSub={currentUserSub} onManage={onManage} /></div>}
  </section>
}

function ResultCard({
  media,
  token,
  currentUserSub,
  onManage,
}: {
  media: Media
  token: string
  currentUserSub?: string
  onManage?: (media: Media) => void
}) {
  const [preview, setPreview] = useState<string>('')
  const isOwner = currentUserSub ? media.owner === currentUserSub : false
  useEffect(() => {
    const url = media.thumbnailUrl
    if (!url) return
    let current = ''
    const headers = url.startsWith(API_BASE) ? { Authorization: `Bearer ${token}` } : undefined
    fetch(url, { headers })
      .then(response => {
        if (!response.ok) throw new Error('Thumbnail unavailable')
        return response.blob()
      })
      .then(blob => { current = URL.createObjectURL(blob); setPreview(current) })
      .catch(() => setPreview(''))
    return () => { if (current) URL.revokeObjectURL(current) }
  }, [media.thumbnailUrl, token])
  return <article className="result-card">
    <div className="preview">{preview ? <img src={preview} alt={media.filename} /> : <FileSearch />}</div>
    <div className="result-body">
      <div className="card-title"><strong>{media.filename}</strong><span className={`pill ${media.status.toLowerCase()}`}>{media.status}</span></div>
      <span>{media.contentType} - {formatBytes(media.size)}</span>
      <span>Created {formatDate(media.createdAt)}</span>
      <span>Media ID: {media.mediaId}</span>
      {media.checksumSha256 && <span>SHA-256: {media.checksumSha256.slice(0, 12)}...</span>}
      <div className="tag-list">{Object.entries(media.tags).map(([tag, count]) => <span key={tag}>{tag} x {count}</span>)}</div>
      {media.modelVersion && <small>Model {media.modelVersion}</small>}
      {media.error && <Status kind="error">{media.error}</Status>}
      <div className="card-actions">
        {media.originalUrl && <a href={media.originalUrl} target="_blank" rel="noreferrer"><ExternalLink size={15} /> Open original</a>}
        {media.thumbnailUrl && <a href={media.thumbnailUrl} target="_blank" rel="noreferrer"><ExternalLink size={15} /> Open thumbnail</a>}
        {isOwner && onManage && <button onClick={() => onManage(media)}><Tags size={15} /> Manage</button>}
      </div>
    </div>
  </article>
}

function SearchPanel({
  token,
  currentUserSub,
  onManage,
}: {
  token: string
  currentUserSub?: string
  onManage: (media: Media) => void
}) {
  const [mode, setMode] = useState<QueryMode>('tags')
  const [tagRows, setTagRows] = useState<TagRow[]>([{ id: 1, tag: 'alectura_lathami', count: '1' }])
  const [species, setSpecies] = useState<Species[]>([])
  const [selectedSpecies, setSelectedSpecies] = useState('')
  const [thumbnailUrl, setThumbnailUrl] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [results, setResults] = useState<Media[]>([])
  const [message, setMessage] = useState<Message | null>(null)
  const [busy, setBusy] = useState(false)
  const [ran, setRan] = useState(false)

  useEffect(() => {
    api<Species[]>('/species', token)
      .then(items => {
        setSpecies(items)
        setSelectedSpecies(items[0]?.tag ?? '')
      })
      .catch(reason => setMessage({ kind: 'error', text: apiErrorMessage(reason) }))
  }, [token])

  const tagPayload = useMemo(() => {
    const payload: Record<string, number> = {}
    tagRows.forEach(row => {
      const tag = row.tag.trim()
      const count = Number(row.count)
      if (tag && Number.isInteger(count) && count >= 1) payload[tag] = count
    })
    return payload
  }, [tagRows])

  function updateTagRow(id: number, changes: Partial<TagRow>) {
    setTagRows(rows => rows.map(row => row.id === id ? { ...row, ...changes } : row))
  }

  async function uploadQueryFile(init: { uploadUrl: string; uploadMethod?: 'PUT' | 'POST'; uploadFields?: Record<string, string> }) {
    if (!file) return
    const directUpload = /^https?:\/\//.test(init.uploadUrl)
    if (init.uploadMethod === 'POST') {
      const form = new FormData()
      Object.entries(init.uploadFields ?? {}).forEach(([key, value]) => form.append(key, value))
      form.append('file', file)
      const response = await fetch(init.uploadUrl, { method: 'POST', body: form })
      if (!response.ok) throw new Error(await response.text())
      return
    }
    const target = directUpload ? init.uploadUrl : `${apiOrigin}${init.uploadUrl}`
    const response = await fetch(target, {
      method: 'PUT',
      headers: directUpload ? { 'Content-Type': file.type } : { Authorization: `Bearer ${token}` },
      body: file,
    })
    if (!response.ok) throw new Error(await response.text())
  }

  async function search() {
    setBusy(true)
    setRan(false)
    setMessage({ kind: 'info', text: mode === 'file' ? 'Uploading temporary query file.' : 'Running query.' })
    try {
      let nextResults: Media[] = []
      if (mode === 'tags') {
        if (Object.keys(tagPayload).length === 0) throw new Error('Add at least one tag with a count of 1 or higher.')
        nextResults = await api('/queries/tags', token, { method: 'POST', body: JSON.stringify({ tags: tagPayload }) })
      } else if (mode === 'species') {
        if (!selectedSpecies) throw new Error('No species are available from the API.')
        nextResults = await api('/queries/species', token, { method: 'POST', body: JSON.stringify({ species: selectedSpecies }) })
      } else if (mode === 'thumbnail') {
        if (!thumbnailUrl.trim()) throw new Error('Paste a thumbnail URL first.')
        const match = await api<{ mediaId: string; originalUrl?: string }>('/queries/thumbnail', token, {
          method: 'POST',
          body: JSON.stringify({ thumbnailUrl: thumbnailUrl.trim() }),
        })
        nextResults = [await api(`/media/${match.mediaId}`, token)]
      } else if (file) {
        setMessage({ kind: 'info', text: 'Temporary file upload reserved.' })
        const init = await api<{ queryId: string; uploadUrl: string; uploadMethod?: 'PUT' | 'POST'; uploadFields?: Record<string, string> }>('/queries/file/init', token, {
          method: 'POST',
          body: JSON.stringify({ filename: file.name, contentType: file.type, size: file.size }),
        })
        await uploadQueryFile(init)
        setMessage({ kind: 'info', text: 'Temporary file uploaded. Running recognition query.' })
        nextResults = await api(`/queries/file/${init.queryId}/execute`, token, { method: 'POST' })
      }
      setResults(nextResults)
      setMessage({ kind: 'ok', text: nextResults.length ? `${nextResults.length} matching observation(s).` : 'No matching observations found.' })
    } catch (reason) {
      setResults([])
      setMessage({ kind: 'error', text: apiErrorMessage(reason) })
    } finally {
      setRan(true)
      setBusy(false)
    }
  }

  return <section className="panel">
    <div className="panel-heading"><div><p className="eyebrow">Archive intelligence</p><h2>Search observations</h2></div><Search /></div>
    <div className="segmented" aria-label="Query type">
      {[
        ['tags', 'Tag count'],
        ['species', 'Species'],
        ['thumbnail', 'Thumbnail'],
        ['file', 'File'],
      ].map(([id, label]) => <button key={id} className={mode === id ? 'active' : ''} onClick={() => setMode(id as QueryMode)}>{label}</button>)}
    </div>
    {mode === 'tags' && <div className="tag-editor">
      {tagRows.map(row => <div className="tag-row" key={row.id}>
        <input value={row.tag} onChange={e => updateTagRow(row.id, { tag: e.target.value })} placeholder="tag" />
        <input type="number" min="1" value={row.count} onChange={e => updateTagRow(row.id, { count: e.target.value })} aria-label="Minimum count" />
        <button aria-label="Remove tag row" onClick={() => setTagRows(rows => rows.filter(item => item.id !== row.id))} disabled={tagRows.length === 1}><X size={16} /></button>
      </div>)}
      <button className="secondary" onClick={() => setTagRows(rows => [...rows, { id: Date.now(), tag: '', count: '1' }])}><Plus size={16} /> Add tag condition</button>
    </div>}
    {mode === 'species' && <label>Species from API<select value={selectedSpecies} onChange={e => setSelectedSpecies(e.target.value)}>
      {species.map(item => <option key={item.tag} value={item.tag}>{item.commonName} ({item.tag})</option>)}
    </select></label>}
    {mode === 'thumbnail' && <label>Thumbnail URL<input className="search-input" value={thumbnailUrl} onChange={e => setThumbnailUrl(e.target.value)} placeholder="https://..." /></label>}
    {mode === 'file' && <div className="drop-zone compact">
      <FileSearch size={28} />
      <strong>{file ? file.name : 'Choose a temporary query file'}</strong>
      <span>The query file is uploaded only for matching and is deleted after execution.</span>
      <input type="file" accept={acceptedMediaTypes} onChange={e => setFile(e.target.files?.[0] ?? null)} />
    </div>}
    <div className="button-row">
      <button className="primary" onClick={search} disabled={busy || (mode === 'file' && !file)}>{busy ? 'Searching...' : 'Run query'}</button>
      <button onClick={() => { setResults([]); setRan(false); setMessage(null) }}><RefreshCw size={16} /> Clear</button>
    </div>
    {message && <Status kind={message.kind}>{message.text}</Status>}
    {ran && !busy && results.length === 0 && <p className="empty-state">No media cards to display.</p>}
    <div className="results">{results.map(media => <ResultCard key={media.mediaId} media={media} token={token} currentUserSub={currentUserSub} onManage={onManage} />)}</div>
  </section>
}

function ManagePanel({
  token,
  latest,
  currentUserSub,
  onDeleted,
}: {
  token: string
  latest?: Media
  currentUserSub?: string
  onDeleted: (mediaId: string) => void
}) {
  const [urls, setUrls] = useState(latest?.originalUrl ?? latest?.mediaId ?? '')
  const [tags, setTags] = useState('reviewed')
  const [message, setMessage] = useState<Message | null>(null)
  const [busy, setBusy] = useState(false)
  const selectedIsOtherOwner = Boolean(latest && currentUserSub && latest.owner !== currentUserSub)

  useEffect(() => {
    if (latest?.originalUrl || latest?.mediaId) setUrls(latest.originalUrl ?? latest.mediaId)
  }, [latest])

  async function modify(operation: 0 | 1) {
    setBusy(true)
    setMessage(null)
    try {
      const targets = parseList(urls)
      const requestedTags = parseList(tags)
      if (!targets.length || !requestedTags.length) throw new Error('Provide at least one media URL or ID and one tag.')
      await api('/tags/bulk', token, { method: 'POST', body: JSON.stringify({ urls: targets, tags: requestedTags, operation }) })
      setMessage({ kind: 'ok', text: operation === 1 ? 'Tags added to owned media.' : 'Tags removed from owned media.' })
    } catch (reason) {
      setMessage({ kind: 'error', text: apiErrorMessage(reason) })
    } finally {
      setBusy(false)
    }
  }

  async function remove() {
    const targets = parseList(urls)
    if (!targets.length) return
    if (!window.confirm(`Delete ${targets.length} media item(s)? This also removes thumbnails and query indexes.`)) return
    setBusy(true)
    setMessage(null)
    try {
      const result = await api<{ deleted: string[] }>('/media', token, { method: 'DELETE', body: JSON.stringify({ urls: targets }) })
      result.deleted.forEach(onDeleted)
      setMessage({ kind: 'ok', text: `${result.deleted.length} media item(s) deleted.` })
    } catch (reason) {
      setMessage({ kind: 'error', text: apiErrorMessage(reason) })
    } finally {
      setBusy(false)
    }
  }

  return <section className="panel">
    <div className="panel-heading"><div><p className="eyebrow">Curatorial controls</p><h2>Manage archive records</h2></div><Tags /></div>
    {latest && <div className="selected-media">
      <CheckCircle2 size={18} />
      <span>{latest.filename}</span>
      <small>{selectedIsOtherOwner ? 'Viewed as non-owner' : 'Owned media selected'}</small>
    </div>}
    <label>Media URLs or IDs<textarea value={urls} onChange={e => setUrls(e.target.value)} rows={4} /></label>
    <label>Tags<textarea value={tags} onChange={e => setTags(e.target.value)} rows={3} /></label>
    <div className="button-row">
      {!selectedIsOtherOwner && <button className="primary" onClick={() => modify(1)} disabled={busy}>Add tags</button>}
      {!selectedIsOtherOwner && <button onClick={() => modify(0)} disabled={busy}>Remove tags</button>}
      {!selectedIsOtherOwner && <button className="danger" onClick={remove} disabled={busy}><Trash2 size={16} /> Delete media</button>}
    </div>
    {selectedIsOtherOwner && <Status kind="info">Owner-only controls are hidden for this selected media. A manual request should still receive 403 from the API.</Status>}
    {message && <Status kind={message.kind}>{message.text}</Status>}
  </section>
}

function NotificationPanel({ token, email }: { token: string; email: string }) {
  const [tag, setTag] = useState('casuarius_casuarius')
  const [message, setMessage] = useState<Message | null>(null)
  const [busy, setBusy] = useState(false)

  async function subscribe() {
    setBusy(true)
    setMessage(null)
    try {
      const result = await api<{ tag: string; email: string; status: string }>('/subscriptions', token, { method: 'POST', body: JSON.stringify({ tag, email }) })
      setMessage({ kind: 'ok', text: `${result.tag} subscription ${result.status}. SNS email subscriptions require confirmation from the mailbox.` })
    } catch (reason) {
      setMessage({ kind: 'error', text: apiErrorMessage(reason) })
    } finally {
      setBusy(false)
    }
  }

  async function unsubscribe() {
    setBusy(true)
    setMessage(null)
    try {
      await api(`/subscriptions/${encodeURIComponent(tag)}`, token, { method: 'DELETE' })
      setMessage({ kind: 'ok', text: `${tag} subscription removed.` })
    } catch (reason) {
      setMessage({ kind: 'error', text: apiErrorMessage(reason) })
    } finally {
      setBusy(false)
    }
  }

  return <section className="panel">
    <div className="panel-heading"><div><p className="eyebrow">Species watch</p><h2>Tag notifications</h2></div><Bell /></div>
    <p className="panel-copy">Receive email notifications when new or updated owned archive events match a watched species tag.</p>
    <label>Species tag<input value={tag} onChange={e => setTag(e.target.value)} /></label>
    <label>Email<input value={email} disabled /></label>
    <div className="button-row">
      <button className="primary" onClick={subscribe} disabled={busy}>Subscribe</button>
      <button onClick={unsubscribe} disabled={busy}>Unsubscribe</button>
    </div>
    {message && <Status kind={message.kind}>{message.text}</Status>}
  </section>
}

export default function App() {
  const cloudMode = Boolean(import.meta.env.VITE_COGNITO_USER_POOL_ID)
  const [token, setToken] = useState(() => sessionStorage.getItem('pba-token') ?? '')
  const [email, setEmail] = useState(() => sessionStorage.getItem('pba-email') ?? '')
  const [tab, setTab] = useState<Tab>('upload')
  const [latest, setLatest] = useState<Media>()
  const [booting, setBooting] = useState(cloudMode && !token)
  const currentUserSub = decodeToken(token).sub

  useEffect(() => {
    if (!cloudMode || token) return
    fetchAuthSession()
      .then(session => {
        const idToken = session.tokens?.idToken?.toString()
        if (!idToken) return
        const claims = decodeToken(idToken)
        sessionStorage.setItem('pba-token', idToken)
        sessionStorage.setItem('pba-email', claims.email ?? '')
        setToken(idToken)
        setEmail(claims.email ?? '')
      })
      .finally(() => setBooting(false))
  }, [cloudMode, token])

  async function refreshSession() {
    if (!cloudMode) return
    const session = await fetchAuthSession({ forceRefresh: true })
    const idToken = session.tokens?.idToken?.toString()
    if (!idToken) return
    const claims = decodeToken(idToken)
    sessionStorage.setItem('pba-token', idToken)
    sessionStorage.setItem('pba-email', claims.email ?? email)
    setToken(idToken)
    setEmail(claims.email ?? email)
  }

  async function logout() {
    if (cloudMode) await signOut()
    sessionStorage.clear()
    setToken('')
    setEmail('')
  }

  if (booting) return <main className="login-shell"><section className="login-story"><div className="brand-mark"><Database size={28} /></div><p className="eyebrow">Pacific BioArchive</p><h1>Restoring session.</h1></section></main>
  if (!token) return <Login onLogin={(next, nextEmail) => {
    sessionStorage.setItem('pba-token', next)
    sessionStorage.setItem('pba-email', nextEmail)
    setToken(next)
    setEmail(nextEmail)
  }} />

  const navigation: { id: Tab; label: string; icon: typeof Upload }[] = [
    { id: 'upload', label: 'Upload', icon: Upload },
    { id: 'search', label: 'Search', icon: Search },
    { id: 'manage', label: 'Manage', icon: Tags },
    { id: 'notifications', label: 'Notifications', icon: Bell },
  ]
  return <div className="app-shell">
    <aside>
      <div className="brand"><div className="brand-mark"><Database size={23} /></div><div><strong>Pacific</strong><span>BioArchive</span></div></div>
      <nav>{navigation.map(item => <button key={item.id} className={tab === item.id ? 'active' : ''} onClick={() => setTab(item.id)}><item.icon size={18} />{item.label}</button>)}</nav>
      <div className="account">
        <span>{email}</span>
        {cloudMode && <button onClick={refreshSession}><RefreshCw size={16} /> Refresh token</button>}
        <button onClick={logout}><LogOut size={16} /> Sign out</button>
      </div>
    </aside>
    <main className="workspace">
      <header><div><p className="eyebrow">Cross-habitat research platform</p><h1>{navigation.find(item => item.id === tab)?.label}</h1></div><div className="cloud-badge"><span>AWS</span><i /> <span>GCP</span></div></header>
      {tab === 'upload' && <UploadPanel token={token} currentUserSub={currentUserSub} onMedia={setLatest} onManage={media => { setLatest(media); setTab('manage') }} />}
      {tab === 'search' && <SearchPanel token={token} currentUserSub={currentUserSub} onManage={media => { setLatest(media); setTab('manage') }} />}
      {tab === 'manage' && <ManagePanel token={token} latest={latest} currentUserSub={currentUserSub} onDeleted={mediaId => {
        if (latest?.mediaId === mediaId) setLatest(undefined)
      }} />}
      {tab === 'notifications' && <NotificationPanel token={token} email={email} />}
    </main>
  </div>
}
