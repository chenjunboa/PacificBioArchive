import { FormEvent, useEffect, useState } from 'react'
import {
  Bell,
  Database,
  FileSearch,
  LogOut,
  Search,
  ShieldCheck,
  Tags,
  Trash2,
  Upload,
} from 'lucide-react'
import { fetchAuthSession, signIn, signOut } from 'aws-amplify/auth'
import { API_BASE, ApiError, Media, api, uploadFile } from './api'

type Tab = 'upload' | 'search' | 'manage' | 'notifications'

function Login({ onLogin }: { onLogin: (token: string, email: string) => void }) {
  const [email, setEmail] = useState('researcher@example.com')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const cloudMode = Boolean(import.meta.env.VITE_COGNITO_USER_POOL_ID)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (cloudMode) {
        await signIn({ username: email, password })
        const session = await fetchAuthSession()
        onLogin(session.tokens?.idToken?.toString() ?? '', email)
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
      setError(reason instanceof Error ? reason.message : 'Sign-in failed')
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
        <h2>Welcome back</h2>
        <label>Email<input type="email" value={email} onChange={e => setEmail(e.target.value)} required /></label>
        {cloudMode && <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} required /></label>}
        {!cloudMode && <p className="local-note">Local prototype mode — no real account is created.</p>}
        {error && <p className="error">{error}</p>}
        <button className="primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
      </form>
    </main>
  )
}

function Status({ kind, children }: { kind: 'ok' | 'error' | 'info'; children: string }) {
  return <div className={`status ${kind}`}>{children}</div>
}

function UploadPanel({ token, onMedia }: { token: string; onMedia: (media: Media) => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<{ kind: 'ok' | 'error' | 'info'; text: string } | null>(null)

  async function submit() {
    if (!file) return
    setBusy(true)
    setMessage({ kind: 'info', text: 'Hashing, uploading and identifying wildlife…' })
    try {
      const media = await uploadFile(file, token)
      onMedia(media)
      setMessage(media.status === 'READY'
        ? { kind: 'ok', text: `Ready — detected ${Object.keys(media.tags).length} species tag(s).` }
        : { kind: 'error', text: media.error ?? 'Processing failed.' })
    } catch (reason) {
      const text = reason instanceof ApiError && reason.status === 409
        ? `Duplicate prevented: ${reason.message}`
        : reason instanceof Error ? reason.message : 'Upload failed'
      setMessage({ kind: 'error', text })
    } finally {
      setBusy(false)
    }
  }

  return <section className="panel">
    <div className="panel-heading"><div><p className="eyebrow">Ingestion pipeline</p><h2>Upload an observation</h2></div><Upload /></div>
    <div className="drop-zone">
      <Upload size={32} />
      <strong>{file ? file.name : 'Choose an image or short video'}</strong>
      <span>JPG, PNG up to 20 MB · MP4, MOV up to 100 MB / 60 seconds</span>
      <input aria-label="Media file" type="file" accept="image/jpeg,image/png,video/mp4,video/quicktime" onChange={e => setFile(e.target.files?.[0] ?? null)} />
    </div>
    <button className="primary" onClick={submit} disabled={!file || busy}>{busy ? 'Processing…' : 'Upload and identify'}</button>
    {message && <Status kind={message.kind}>{message.text}</Status>}
  </section>
}

function ResultCard({ media, token }: { media: Media; token: string }) {
  const [preview, setPreview] = useState<string>('')
  useEffect(() => {
    const url = media.thumbnailUrl
    if (!url) return
    let current = ''
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then(response => response.blob())
      .then(blob => { current = URL.createObjectURL(blob); setPreview(current) })
    return () => { if (current) URL.revokeObjectURL(current) }
  }, [media.thumbnailUrl, token])
  return <article className="result-card">
    <div className="preview">{preview ? <img src={preview} alt={media.filename} /> : <FileSearch />}</div>
    <div className="result-body"><strong>{media.filename}</strong><span>{media.contentType}</span>
      <div className="tag-list">{Object.entries(media.tags).map(([tag, count]) => <span key={tag}>{tag} × {count}</span>)}</div>
      <small>{media.modelVersion}</small>
    </div>
  </article>
}

function SearchPanel({ token }: { token: string }) {
  const [mode, setMode] = useState<'tags' | 'species' | 'thumbnail' | 'file'>('tags')
  const [value, setValue] = useState('alectura_lathami:1')
  const [file, setFile] = useState<File | null>(null)
  const [results, setResults] = useState<Media[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function search() {
    setBusy(true); setError('')
    try {
      if (mode === 'tags') {
        const tags = Object.fromEntries(value.split(',').map(part => {
          const [tag, count = '1'] = part.trim().split(':')
          return [tag, Number(count)]
        }))
        setResults(await api('/queries/tags', token, { method: 'POST', body: JSON.stringify({ tags }) }))
      } else if (mode === 'species') {
        setResults(await api('/queries/species', token, { method: 'POST', body: JSON.stringify({ species: value }) }))
      } else if (mode === 'thumbnail') {
        const match = await api<{ mediaId: string }>('/queries/thumbnail', token, { method: 'POST', body: JSON.stringify({ thumbnailUrl: value }) })
        setResults([await api(`/media/${match.mediaId}`, token)])
      } else if (file) {
        const init = await api<{ queryId: string; uploadUrl: string }>('/queries/file/init', token, {
          method: 'POST', body: JSON.stringify({ filename: file.name, contentType: file.type, size: file.size }),
        })
        await fetch(`${API_BASE.replace('/api/v1', '')}${init.uploadUrl}`, { method: 'PUT', headers: { Authorization: `Bearer ${token}` }, body: file })
        setResults(await api(`/queries/file/${init.queryId}/execute`, token, { method: 'POST' }))
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Query failed') }
    finally { setBusy(false) }
  }

  return <section className="panel">
    <div className="panel-heading"><div><p className="eyebrow">Archive intelligence</p><h2>Search observations</h2></div><Search /></div>
    <div className="segmented">
      {(['tags', 'species', 'thumbnail', 'file'] as const).map(item => <button key={item} className={mode === item ? 'active' : ''} onClick={() => setMode(item)}>{item}</button>)}
    </div>
    {mode === 'file'
      ? <input type="file" onChange={e => setFile(e.target.files?.[0] ?? null)} />
      : <input className="search-input" value={value} onChange={e => setValue(e.target.value)} placeholder={mode === 'tags' ? 'wombat:2, magpie:1' : 'Species or URL'} />}
    <button className="primary" onClick={search} disabled={busy || (mode === 'file' && !file)}>{busy ? 'Searching…' : 'Run query'}</button>
    {error && <Status kind="error">{error}</Status>}
    <p className="result-count">{results.length} matching observation(s)</p>
    <div className="results">{results.map(media => <ResultCard key={media.mediaId} media={media} token={token} />)}</div>
  </section>
}

function ManagePanel({ token, latest }: { token: string; latest?: Media }) {
  const [url, setUrl] = useState(latest?.originalUrl ?? '')
  const [tags, setTags] = useState('reviewed')
  const [message, setMessage] = useState('')
  useEffect(() => { if (latest?.originalUrl) setUrl(latest.originalUrl) }, [latest])
  async function modify(operation: 0 | 1) {
    try {
      await api('/tags/bulk', token, { method: 'POST', body: JSON.stringify({ urls: [url], tags: tags.split(','), operation }) })
      setMessage(operation ? 'Tags added.' : 'Tags removed.')
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : 'Operation failed') }
  }
  async function remove() {
    try {
      await api('/media', token, { method: 'DELETE', body: JSON.stringify({ urls: [url] }) })
      setMessage('Media and thumbnail deleted.')
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : 'Delete failed') }
  }
  return <section className="panel">
    <div className="panel-heading"><div><p className="eyebrow">Curatorial controls</p><h2>Manage archive records</h2></div><Tags /></div>
    <label>Media URL or ID<input value={url} onChange={e => setUrl(e.target.value)} /></label>
    <label>Comma-separated tags<input value={tags} onChange={e => setTags(e.target.value)} /></label>
    <div className="button-row"><button className="primary" onClick={() => modify(1)}>Add tags</button><button onClick={() => modify(0)}>Remove tags</button><button className="danger" onClick={remove}><Trash2 size={16} /> Delete media</button></div>
    {message && <Status kind={message.includes('failed') ? 'error' : 'ok'}>{message}</Status>}
  </section>
}

function NotificationPanel({ token, email }: { token: string; email: string }) {
  const [tag, setTag] = useState('casuarius_casuarius')
  const [message, setMessage] = useState('')
  async function subscribe() {
    try {
      await api('/subscriptions', token, { method: 'POST', body: JSON.stringify({ tag, email }) })
      setMessage('Local subscription confirmed. Cloud deployment sends an SNS confirmation email.')
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : 'Subscription failed') }
  }
  return <section className="panel">
    <div className="panel-heading"><div><p className="eyebrow">Species watch</p><h2>Tag notifications</h2></div><Bell /></div>
    <p>Receive an email when new or updated media contains a watched species.</p>
    <label>Species tag<input value={tag} onChange={e => setTag(e.target.value)} /></label>
    <label>Email<input value={email} disabled /></label>
    <button className="primary" onClick={subscribe}>Subscribe</button>
    {message && <Status kind="ok">{message}</Status>}
  </section>
}

export default function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem('pba-token') ?? '')
  const [email, setEmail] = useState(() => sessionStorage.getItem('pba-email') ?? '')
  const [tab, setTab] = useState<Tab>('upload')
  const [latest, setLatest] = useState<Media>()
  if (!token) return <Login onLogin={(next, nextEmail) => {
    sessionStorage.setItem('pba-token', next); sessionStorage.setItem('pba-email', nextEmail)
    setToken(next); setEmail(nextEmail)
  }} />
  async function logout() {
    if (import.meta.env.VITE_COGNITO_USER_POOL_ID) await signOut()
    sessionStorage.clear(); setToken(''); setEmail('')
  }
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
      <div className="account"><span>{email}</span><button onClick={logout}><LogOut size={16} /> Sign out</button></div>
    </aside>
    <main className="workspace">
      <header><div><p className="eyebrow">Cross-habitat research platform</p><h1>{navigation.find(item => item.id === tab)?.label}</h1></div><div className="cloud-badge"><span>AWS</span><i /> <span>GCP</span></div></header>
      {tab === 'upload' && <UploadPanel token={token} onMedia={setLatest} />}
      {tab === 'search' && <SearchPanel token={token} />}
      {tab === 'manage' && <ManagePanel token={token} latest={latest} />}
      {tab === 'notifications' && <NotificationPanel token={token} email={email} />}
    </main>
  </div>
}
