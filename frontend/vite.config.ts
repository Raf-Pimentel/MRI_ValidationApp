import { createReadStream, existsSync, statSync } from 'node:fs'
import { join, normalize, resolve } from 'node:path'
import { defineConfig, type Plugin } from 'vite'

// Dev only: serve ../data/dev at /dev-data so the spike can load volumes.
// The real app serves volumes through the backend by opaque id.
function devData(): Plugin {
  const root = resolve(__dirname, '../data/dev')
  return {
    name: 'dev-data',
    configureServer(server) {
      server.middlewares.use('/dev-data', (req, res, next) => {
        const rel = normalize(decodeURIComponent((req.url ?? '/').split('?')[0]))
        const file = join(root, rel)
        if (!file.startsWith(root) || !existsSync(file) || !statSync(file).isFile()) return next()
        res.setHeader('Content-Type', 'application/octet-stream')
        res.setHeader('Content-Length', statSync(file).size)
        createReadStream(file).pipe(res)
      })
    },
  }
}

export default defineConfig({ plugins: [devData()] })
