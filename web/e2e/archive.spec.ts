import { expect, request, test } from '@playwright/test'

const apiBase = 'http://127.0.0.1:8000/api/v1/'
const pngBase64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADUlEQVR42mP8z8BQDwAFgwJ/l81+OQAAAABJRU5ErkJggg=='

function pngFixture(name: string) {
  const uniqueBytes = Buffer.from(`\ne2e-${Date.now()}-${Math.random()}`)
  return {
    name,
    mimeType: 'image/png',
    buffer: Buffer.concat([Buffer.from(pngBase64, 'base64'), uniqueBytes]),
  }
}

async function devToken(email: string) {
  const api = await request.newContext({ baseURL: apiBase })
  const response = await api.post('auth/dev-token', {
    data: { email, givenName: 'Playwright', familyName: 'Tester' },
  })
  expect(response.ok()).toBeTruthy()
  const payload = await response.json()
  await api.dispose()
  return payload.accessToken as string
}

async function signedApi(email: string) {
  const token = await devToken(email)
  return request.newContext({
    baseURL: apiBase,
    extraHTTPHeaders: { Authorization: `Bearer ${token}` },
  })
}

test('local archive workflow covers upload, queries, ownership, delete, and signed-out access', async ({ page, request: anon }) => {
  const ownerEmail = `owner-${Date.now()}@example.com`
  const mediaFile = pngFixture(`Alectura_lathami_${Date.now()}.png`)

  await page.goto('/')
  await page.getByLabel('Email').fill(ownerEmail)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('heading', { name: 'Upload', exact: true })).toBeVisible()

  await page.locator('input[type="file"]').setInputFiles(mediaFile)
  await page.getByRole('button', { name: 'Upload and identify' }).click()
  await expect(page.locator('.status-steps').getByText('Calculating SHA-256 checksum...')).toBeVisible()
  await expect(page.getByRole('article').getByText('READY')).toBeVisible({ timeout: 30_000 })
  await expect(page.getByRole('article').getByText('alectura_lathami x 1')).toBeVisible()

  await page.getByRole('button', { name: 'Upload and identify' }).click()
  await expect(page.getByText(/File content already exists/)).toBeVisible()

  const ownerApi = await signedApi(ownerEmail)
  const tagResponse = await ownerApi.post('queries/tags', { data: { tags: { alectura_lathami: 1 } } })
  expect(tagResponse.ok()).toBeTruthy()
  const [media] = await tagResponse.json()
  expect(media.mediaId).toBeTruthy()

  await page.getByRole('button', { name: 'Search' }).click()
  await page.getByRole('button', { name: 'Run query' }).click()
  await expect(page.getByText(/matching observation/)).toBeVisible()
  await expect(page.getByText(media.mediaId)).toBeVisible()

  await page.getByRole('button', { name: 'Species' }).click()
  await expect(page.locator('select option')).toHaveCount(46)
  await page.locator('select').selectOption('alectura_lathami')
  await page.getByRole('button', { name: 'Run query' }).click()
  await expect(page.getByText(media.mediaId)).toBeVisible()

  await page.getByRole('button', { name: 'Thumbnail' }).click()
  await page.getByLabel('Thumbnail URL').fill(media.thumbnailUrl)
  await page.getByRole('button', { name: 'Run query' }).click()
  await expect(page.getByText(media.mediaId)).toBeVisible()

  await page.getByRole('button', { name: 'File' }).click()
  await page.locator('.drop-zone.compact input[type="file"]').setInputFiles(pngFixture('Alectura_lathami_99.png'))
  await page.getByRole('button', { name: 'Run query' }).click()
  await expect(page.getByText(media.mediaId)).toBeVisible()

  await page.getByRole('navigation').getByRole('button', { name: 'Manage' }).click()
  await page.getByLabel('Media URLs or IDs').fill(media.originalUrl)
  await page.getByLabel('Tags').fill('demo_reviewed')
  await page.getByRole('button', { name: 'Add tags' }).click()
  await expect(page.getByText('Tags added to owned media.')).toBeVisible()
  await page.getByRole('button', { name: 'Remove tags' }).click()
  await expect(page.getByText('Tags removed from owned media.')).toBeVisible()

  const strangerApi = await signedApi(`stranger-${Date.now()}@example.com`)
  const forbidden = await strangerApi.post('tags/bulk', {
    data: { urls: [media.originalUrl], tags: ['forbidden'], operation: 1 },
  })
  expect(forbidden.status()).toBe(403)
  await strangerApi.dispose()

  page.once('dialog', dialog => dialog.accept())
  await page.getByRole('button', { name: 'Delete media' }).click()
  await expect(page.getByText('1 media item(s) deleted.')).toBeVisible()
  const deleted = await ownerApi.get(`media/${media.mediaId}`)
  expect(deleted.status()).toBe(404)
  await ownerApi.dispose()

  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible()
  const signedOut = await anon.get(`${apiBase}me`)
  expect(signedOut.status()).toBe(401)
})
