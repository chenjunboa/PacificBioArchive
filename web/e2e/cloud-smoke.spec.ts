import { expect, test } from '@playwright/test'

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

  test('verified user can upload, query, and delete an image in the deployed app', async ({ page }) => {
    const email = process.env.PBA_CLOUD_EMAIL!
    const password = process.env.PBA_CLOUD_PASSWORD!
    const imagePath = process.env.PBA_CLOUD_IMAGE_PATH!
    const expectedTag = process.env.PBA_CLOUD_EXPECTED_TAG ?? 'alectura_lathami'

    await page.goto('/')
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password').fill(password)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByRole('heading', { name: 'Upload', exact: true })).toBeVisible()

    await page.locator('input[type="file"]').setInputFiles(imagePath)
    await page.getByRole('button', { name: 'Upload and identify' }).click()
    await expect(page.getByRole('article').getByText('READY')).toBeVisible({ timeout: 150_000 })

    const article = page.getByRole('article').first()
    await expect(article.getByText(expectedTag)).toBeVisible()
    const mediaText = await article.innerText()
    const mediaId = mediaText.match(/Media ID:\s*([a-f0-9-]+)/i)?.[1]
    expect(mediaId).toBeTruthy()
    const originalUrl = await article.getByRole('link', { name: 'Open original' }).getAttribute('href')
    expect(originalUrl).toBeTruthy()
    const thumbnailUrl = await article.getByRole('link', { name: 'Open thumbnail' }).getAttribute('href')
    expect(thumbnailUrl).toBeTruthy()

    await page.getByRole('button', { name: 'Search' }).click()
    await page.getByRole('button', { name: 'Run query' }).click()
    await expect(page.getByText(mediaId!)).toBeVisible()

    await page.getByRole('button', { name: 'Thumbnail' }).click()
    await page.getByLabel('Thumbnail URL').fill(thumbnailUrl!)
    await page.getByRole('button', { name: 'Run query' }).click()
    await expect(page.getByText(mediaId!)).toBeVisible()

    await page.getByRole('navigation').getByRole('button', { name: 'Manage' }).click()
    await page.getByLabel('Media URLs or IDs').fill(originalUrl!)
    page.once('dialog', dialog => dialog.accept())
    await page.getByRole('button', { name: 'Delete media' }).click()
    await expect(page.getByText(/media item\(s\) deleted/)).toBeVisible()

    await page.getByRole('button', { name: 'Sign out' }).click()
    await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible()
  })
})
