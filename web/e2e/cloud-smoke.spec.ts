import { expect, request, test } from '@playwright/test'

type Media = {
  mediaId: string
  status: string
  contentType: string
  tags: Record<string, number>
  originalUrl?: string
  thumbnailUrl?: string
}

const requiredEnv = [
  'PBA_CLOUD_WEB_URL',
  'PBA_CLOUD_EMAIL',
  'PBA_CLOUD_PASSWORD',
  'PBA_CLOUD_IMAGE_PATH',
] as const

test.describe('cloud smoke workflow', () => {
  test.skip(
    requiredEnv.some(name => !process.env[name]),
    `Set ${requiredEnv.join(', ')} to run the deployed cloud smoke test.`,
  )

  test('verified user can upload, query, and delete media in the deployed app', async ({ page }) => {
    const email = process.env.PBA_CLOUD_EMAIL!
    const password = process.env.PBA_CLOUD_PASSWORD!
    const imagePath = process.env.PBA_CLOUD_IMAGE_PATH!
    const expectedTag = process.env.PBA_CLOUD_EXPECTED_TAG ?? 'alectura_lathami'
    const expectedThumbnail = process.env.PBA_CLOUD_EXPECT_THUMBNAIL !== 'false'
    const readyTimeout = Number(process.env.PBA_CLOUD_READY_TIMEOUT_MS ?? 300_000)
    let readyMedia: Media | undefined

    await page.goto('/')
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password').fill(password)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByRole('heading', { name: 'Upload', exact: true })).toBeVisible()

    const readyResponse = page.waitForResponse(async response => {
      if (!response.url().includes('/api/v1/media/')) return false
      if (response.request().method() !== 'GET' || response.status() !== 200) return false
      const media = await response.json().catch(() => undefined) as Media | undefined
      if (media?.status !== 'READY' || !media.tags?.[expectedTag]) return false
      readyMedia = media
      return true
    }, { timeout: readyTimeout })

    await page.locator('input[type="file"]').setInputFiles(imagePath)
    await page.getByRole('button', { name: 'Upload and identify' }).click()
    const response = await readyResponse
    await expect(page.getByText(/Ready.*detected 1 species tag/i)).toBeVisible()
    expect(readyMedia).toBeTruthy()
    expect(readyMedia!.tags[expectedTag]).toBeGreaterThanOrEqual(1)
    expect(readyMedia!.originalUrl).toBeTruthy()
    if (expectedThumbnail) expect(readyMedia!.thumbnailUrl).toBeTruthy()
    console.log(`cloud-smoke-media-id=${readyMedia!.mediaId}`)
    console.log(`cloud-smoke-content-type=${readyMedia!.contentType}`)

    const apiBase = response.url().replace(/media\/[^/]+$/, '')
    const token = await page.evaluate(() => sessionStorage.getItem('pba-token'))
    expect(token).toBeTruthy()
    const api = await request.newContext({
      baseURL: apiBase,
      extraHTTPHeaders: { Authorization: `Bearer ${token}` },
    })

    const tagQuery = await api.post('queries/tags', { data: { tags: { [expectedTag]: 1 } } })
    expect(tagQuery.ok()).toBeTruthy()
    const tagMatches = await tagQuery.json() as Media[]
    expect(tagMatches.some(item => item.mediaId === readyMedia!.mediaId)).toBeTruthy()

    if (readyMedia!.thumbnailUrl) {
      const thumbnailQuery = await api.post('queries/thumbnail', {
        data: { thumbnailUrl: readyMedia!.thumbnailUrl },
      })
      expect(thumbnailQuery.ok()).toBeTruthy()
      expect((await thumbnailQuery.json()).mediaId).toBe(readyMedia!.mediaId)
    }

    const deleted = await api.delete('media', { data: { urls: [readyMedia!.originalUrl] } })
    expect(deleted.ok()).toBeTruthy()
    expect((await deleted.json()).deleted).toContain(readyMedia!.mediaId)
    const deletedMedia = await api.get(`media/${readyMedia!.mediaId}`)
    expect(deletedMedia.status()).toBe(404)
    await api.dispose()

    await page.getByRole('button', { name: 'Sign out' }).click()
    await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible()
  })
})
