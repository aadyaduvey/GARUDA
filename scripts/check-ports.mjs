// Run by `pnpm start` before the servers: fail fast, in plain words, if a port is already taken.
import net from 'node:net'

const PORTS = [
  [8000, 'API'],
  [5173, 'dashboard'],
]

// A port counts as taken if we cannot listen on it over IPv4 or IPv6 (Vite binds "localhost").
const taken = (port, host) =>
  new Promise((resolve) => {
    const server = net.createServer()
    server.once('error', (err) => resolve(err.code === 'EADDRINUSE'))
    server.once('listening', () => server.close(() => resolve(false)))
    server.listen(port, host)
  })

const busy = []
for (const [port, name] of PORTS) {
  if ((await taken(port, '127.0.0.1')) || (await taken(port, '::1'))) busy.push(`${port} (${name})`)
}

if (busy.length) {
  console.error(`\nPort ${busy.join(' and ')} is already in use, probably by an earlier \`pnpm dev\`, \`uvicorn\` or \`pnpm start\`.`)
  console.error('Stop it (press Ctrl+C in that terminal, or close the terminal) and run `pnpm start` again.\n')
  process.exit(1)
}
