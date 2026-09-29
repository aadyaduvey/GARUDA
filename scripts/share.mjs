// `pnpm share`: give the running dashboard a public https link via a Cloudflare quick tunnel.
// Finds cloudflared even when its installer did not add it to PATH (the usual case with winget).
import { spawn, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import net from 'node:net'

const PORT = 5174
const TARGET = `http://localhost:${PORT}`
const CANDIDATES = [
  'cloudflared',
  'C:\\Program Files (x86)\\cloudflared\\cloudflared.exe',
  'C:\\Program Files\\cloudflared\\cloudflared.exe',
  `${process.env.LOCALAPPDATA}\\Microsoft\\WinGet\\Links\\cloudflared.exe`,
]

const findCloudflared = () =>
  CANDIDATES.find((c) => (c.includes('\\') ? existsSync(c) : spawnSync(c, ['--version'], { stdio: 'ignore' }).status === 0))

const dashboardRunning = () =>
  new Promise((resolve) => {
    const socket = net.connect({ port: PORT, host: 'localhost' })
    socket.once('connect', () => socket.end(() => resolve(true)))
    socket.once('error', () => resolve(false))
  })

const cloudflared = findCloudflared()
if (!cloudflared) {
  console.error('\ncloudflared is not installed. Install it once with:\n  winget install --id Cloudflare.cloudflared\nthen run `pnpm share` again.\n')
  process.exit(1)
}
if (!(await dashboardRunning())) {
  console.error(`\nThe dashboard is not running on port ${PORT}. Start it first with \`pnpm start\` in another terminal, then run \`pnpm share\`.\n`)
  process.exit(1)
}

console.log('Opening a public link (takes a few seconds)...')
const tunnel = spawn(cloudflared, ['tunnel', '--no-autoupdate', '--url', TARGET], { stdio: ['ignore', 'pipe', 'pipe'] })
let announced = false
const recent = []
const onOutput = (chunk) => {
  for (const line of chunk.toString().split('\n')) {
    recent.push(line)
    if (recent.length > 15) recent.shift()
    const url = line.match(/https:\/\/[a-z0-9-]+\.trycloudflare\.com/)
    if (url && !announced) {
      announced = true
      console.log(`\n  Public link: ${url[0]}\n\n  Open it on any device, on any network. Anyone with the link can view the dashboard.`)
      console.log('  Keep this terminal and `pnpm start` running. Press Ctrl+C here to close the link.\n')
    }
  }
}
tunnel.stdout.on('data', onOutput)
tunnel.stderr.on('data', onOutput)
tunnel.on('exit', (code) => {
  if (code) console.error(`\nThe tunnel stopped (exit code ${code}). Last messages:\n${recent.join('\n')}`)
  process.exit(code ?? 0)
})
