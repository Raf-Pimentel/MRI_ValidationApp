import { ApiError, getPage, getSession, postRating, prefetchVolume } from './api'
import type { PageData, SessionInfo } from './api'
import { getViewerState, initViewer, showPage, strips } from './viewer'

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T

const screens = ['s-token', 's-intro', 's-done', 'app']
function show(id: string) {
  for (const s of screens) $(s).hidden = s !== id
}

let token = ''
let session: SessionInfo
let page: PageData | null = null
let viewerReady = false

// Current rating of each slot on the page being shown (what the server holds, plus unsent edits).
const local: Record<string, { score: number | null; comment: string }> = {}

// ---- Saving ----

// Saves run one after another, so the server sees them in the order the rater made them.
let chain: Promise<void> = Promise.resolve()
let unsaved = 0

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms))

function setStatus(slot: string, text: string, kind: '' | 'bad' | 'missing' = '') {
  const el = document.querySelector<HTMLElement>(`[data-status="${slot}"]`)
  if (!el) return
  el.textContent = text
  el.className = `status ${kind}`
}

function save(slot: string) {
  const r = local[slot]
  if (!page || r.score === null) return
  const body = {
    client_event_id: crypto.randomUUID(),
    position: page.position,
    slot,
    score: r.score,
    comment: r.comment.trim() === '' ? null : r.comment,
    viewer_state: getViewerState(),
  }
  unsaved++
  setStatus(slot, 'salvando...')
  updateNav()
  chain = chain.then(async () => {
    for (let attempt = 0; ; attempt++) {
      try {
        await postRating(token, body)
        setStatus(slot, 'salvo')
        break
      } catch (err) {
        // The server said no (bad request, bad link): resending the same thing will not help.
        if (err instanceof ApiError && err.status < 500) {
          setStatus(slot, 'erro ao salvar', 'bad')
          break
        }
        setStatus(slot, 'sem conexão, tentando de novo', 'bad')
        await wait(Math.min(5000, 500 * 2 ** attempt))
      }
    }
    unsaved--
    updateNav()
  })
}

window.addEventListener('beforeunload', (e) => {
  if (unsaved > 0) e.preventDefault()
})

// ---- Comment box ----

const cpop = $<HTMLDivElement>('cpop')
const cText = $<HTMLTextAreaElement>('cpop-text')
let cSlot: string | null = null
let cTimer = 0
let cDirty = false

function openComment(slot: string, anchor: HTMLElement) {
  cSlot = slot
  $('cpop-title').textContent =
    local[slot].score === null ? `Imagem ${slot}: dê uma nota para o comentário ser salvo` : `Comentário da imagem ${slot}`
  cText.value = local[slot].comment
  cpop.hidden = false
  const r = anchor.getBoundingClientRect()
  cpop.style.left = `${Math.max(4, Math.min(r.left, window.innerWidth - 270))}px`
  cpop.style.top = `${Math.max(4, r.top - cpop.offsetHeight - 6)}px`
  cText.focus()
}

function closeComment() {
  if (cSlot === null) return
  clearTimeout(cTimer)
  commitComment()
  cpop.hidden = true
  cSlot = null
}

function commitComment() {
  if (cSlot === null || !cDirty) return
  cDirty = false
  save(cSlot)
}

cText.addEventListener('input', () => {
  if (cSlot === null) return
  local[cSlot].comment = cText.value
  refreshCommentButton(cSlot)
  cDirty = true
  clearTimeout(cTimer)
  cTimer = window.setTimeout(commitComment, 700)
})
document.addEventListener('pointerdown', (e) => {
  const t = e.target as HTMLElement
  if (!cpop.hidden && !cpop.contains(t) && !t.closest('.cbtn')) closeComment()
})
window.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !cpop.hidden) closeComment()
})

function refreshCommentButton(slot: string) {
  const b = document.querySelector<HTMLElement>(`[data-cbtn="${slot}"]`)
  if (!b) return
  b.classList.toggle('has', local[slot].comment.trim() !== '')
}

// ---- Page ----

function buildStrips(p: PageData) {
  p.columns.forEach(({ slot }, i) => {
    const r = p.ratings[slot]
    local[slot] = { score: r?.score ?? null, comment: r?.comment ?? '' }
    strips[i].innerHTML = `
      <div class="scores" role="group" aria-label="Nota da imagem ${slot}">
        ${[1, 2, 3, 4, 5].map((n) => `<button data-score="${n}" aria-label="Nota ${n}">${n}</button>`).join('')}
      </div>
      <div class="row">
        <button class="cbtn" data-cbtn="${slot}">Comentário</button>
        <span data-status="${slot}"></span>
      </div>`
    const buttons = strips[i].querySelectorAll<HTMLButtonElement>('[data-score]')
    const paint = () =>
      buttons.forEach((b) => b.classList.toggle('on', Number(b.dataset.score) === local[slot].score))
    paint()
    buttons.forEach((b) =>
      b.addEventListener('click', () => {
        const score = Number(b.dataset.score)
        if (local[slot].score === score) return
        local[slot].score = score
        paint()
        save(slot)
      }),
    )
    const cbtn = strips[i].querySelector('.cbtn') as HTMLButtonElement
    cbtn.addEventListener('click', () => {
      closeComment()
      openComment(slot, cbtn)
    })
    refreshCommentButton(slot)
    setStatus(slot, r ? 'salvo' : 'sem nota', r ? '' : 'missing')
  })
  // A slot whose first rating was just sent no longer reads "sem nota"; save() sets its own status.
}

const missingSlots = () => (page ? page.columns.map((c) => c.slot).filter((s) => local[s].score === null) : [])

function updateNav() {
  if (!page) return
  const rated = page.columns.length - missingSlots().length
  const last = page.position === page.total_pages
  $('progress').textContent = `Página ${page.position} de ${page.total_pages} | Sequência: ${page.sequence} | ${rated} de ${page.columns.length} notas`
  ;($('prev') as HTMLButtonElement).disabled = page.position <= 1
  const next = $<HTMLButtonElement>('next')
  next.disabled = unsaved > 0
  next.innerHTML = unsaved > 0 ? 'Salvando...' : last ? 'Finalizar' : 'Próxima &rarr;'
}

async function goTo(position: number) {
  closeComment()
  $<HTMLButtonElement>('prev').disabled = true
  $<HTMLButtonElement>('next').disabled = true
  try {
    const p = await getPage(token, position)
    if (!viewerReady) {
      show('app')
      await initViewer()
      viewerReady = true
    } else {
      show('app')
    }
    page = p
    buildStrips(p)
    updateNav()
    await showPage(p.columns)
    preloadNext(p)
  } catch (err) {
    $('progress').textContent = `Erro: ${err instanceof Error ? err.message : String(err)}`
    $<HTMLButtonElement>('prev').disabled = false
    $<HTMLButtonElement>('next').disabled = false
  }
}

// Pull the next page's volumes into the browser cache while the rater works on this one.
async function preloadNext(p: PageData) {
  if (p.position >= p.total_pages) return
  try {
    const nextPage = await getPage(token, p.position + 1)
    for (const c of nextPage.columns) await prefetchVolume(c.url)
  } catch {
    /* optimisation only */
  }
}

// ---- Dialog ----

function confirmDialog(text: string, no: string, yes: string): Promise<boolean> {
  $('modal-text').textContent = text
  $('modal-no').textContent = no
  $('modal-yes').textContent = yes
  $('modal').hidden = false
  return new Promise((resolve) => {
    const done = (v: boolean) => {
      $('modal').hidden = true
      $('modal-no').onclick = $('modal-yes').onclick = null
      resolve(v)
    }
    $('modal-no').onclick = () => done(false)
    $('modal-yes').onclick = () => done(true)
  })
}

async function leavePage(): Promise<boolean> {
  closeComment()
  const missing = missingSlots()
  if (missing.length > 0) {
    const names = missing.sort().join(', ')
    const ok = await confirmDialog(
      `Falta nota na${missing.length > 1 ? 's imagens' : ' imagem'} ${names}. Deseja seguir assim mesmo?`,
      'Voltar e avaliar',
      'Seguir sem nota',
    )
    if (!ok) return false
  }
  await chain
  return true
}

$('prev').addEventListener('click', async () => {
  if (!page) return
  closeComment()
  await chain
  goTo(page.position - 1)
})

$('next').addEventListener('click', async () => {
  if (!page || !(await leavePage())) return
  if (page.position < page.total_pages) goTo(page.position + 1)
  else finish()
})

// ---- Screens ----

async function finish() {
  session = await getSession(token)
  const left = session.total_pages - session.completed_pages
  const back = $<HTMLButtonElement>('done-back')
  if (left > 0) {
    $('done-text').textContent = `Você chegou ao fim, mas ${left} ${left > 1 ? 'páginas ainda têm' : 'página ainda tem'} imagens sem nota. Suas notas já estão salvas; você pode completar agora ou depois, pelo mesmo link.`
    back.hidden = false
  } else {
    $('done-text').textContent = 'Você avaliou todas as páginas. Suas notas foram salvas. Pode fechar esta janela.'
    back.hidden = true
  }
  show('s-done')
}

$('done-back').addEventListener('click', () => goTo(session.next_position ?? 1))

function tokenFromText(text: string): string {
  const t = text.trim()
  const m = t.match(/[?&]t=([^&#\s]+)/)
  return decodeURIComponent(m ? m[1] : t)
}

async function enter(t: string) {
  const info = await getSession(t)
  token = t
  session = info
  history.replaceState(null, '', `?t=${encodeURIComponent(t)}`)
  if (info.finished) return finish()
  $('intro-title').textContent = info.name ? `Bem-vindo, ${info.name}` : 'Bem-vindo'
  $('intro-progress').textContent =
    info.completed_pages > 0
      ? `Você já completou ${info.completed_pages} de ${info.total_pages} páginas. Vamos continuar de onde parou.`
      : `Serão ${info.total_pages} páginas.`
  $('intro-go').textContent = info.completed_pages > 0 ? 'Continuar' : 'Começar'
  show('s-intro')
}

$('intro-go').addEventListener('click', () => goTo(session.next_position ?? 1))

$('token-go').addEventListener('click', async () => {
  $('token-err').textContent = ''
  try {
    await enter(tokenFromText($<HTMLInputElement>('token-in').value))
  } catch (err) {
    $('token-err').textContent = err instanceof Error ? err.message : String(err)
  }
})

async function boot() {
  const t = new URLSearchParams(location.search).get('t')
  if (!t) return show('s-token')
  try {
    await enter(t)
  } catch (err) {
    show('s-token')
    $('token-err').textContent = err instanceof ApiError && err.status === 404 ? err.message : `Não foi possível entrar: ${err instanceof Error ? err.message : String(err)}`
  }
}

boot()
