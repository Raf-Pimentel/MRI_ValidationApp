import { DRAG_MODE, Niivue, MULTIPLANAR_TYPE, SHOW_RENDER, SLICE_TYPE } from '@niivue/niivue'

const SLOTS = ['A', 'B', 'C', 'D', 'E']
const CASE = 'case_01'
const VIEW_NAMES = ['Axial', 'Coronal', 'Sagital']
// Niivue tile type (axial=0, coronal=1, sagittal=2) -> component of crosshairPos [x, y, z]
const AXIS_OF_VIEW = [2, 1, 0]

const cols = document.getElementById('cols') as HTMLDivElement
const msg = document.getElementById('msg') as HTMLDivElement

// Shared position, as fractions of the volume. One component per view: scrolling a view changes only its own.
const pos = [0.5, 0.5, 0.5]
// Global display window (same for every image). Data is already in [0, 1], so the default window is 0-1.
const view = { brightness: 0, contrast: 100 }
const instances: Niivue[] = []
let dimsRAS: number[] = [0, 1, 1, 1]
// Enlarged viewer (magnifier): one extra Niivue showing a single view of one column.
let zoomNv: Niivue | null = null
const zoom = { view: 0, slot: 'A', level: 1 }
const zoomPan = [0, 0, 0]
const lupaSets: { canvas: HTMLCanvasElement; lupas: HTMLButtonElement[] }[] = []

const allViewers = () => (zoomNv ? [...instances, zoomNv] : instances)

function render() {
  for (const nv of allViewers()) {
    nv.scene.crosshairPos[0] = pos[0]
    nv.scene.crosshairPos[1] = pos[1]
    nv.scene.crosshairPos[2] = pos[2]
    nv.drawScene()
  }
  const parts = VIEW_NAMES.map((name, v) => {
    const axis = AXIS_OF_VIEW[v]
    const n = dimsRAS[axis + 1]
    return `${name} ${Math.min(n, Math.floor(pos[axis] * n) + 1)}/${n}`
  })
  msg.textContent = `${instances.length} volumes | ${parts.join(' | ')}`
}

function applyWindow() {
  const bright = view.brightness / 100
  const width = 1 / (view.contrast / 100)
  const center = 0.5 - bright
  for (const nv of allViewers()) {
    const vol = nv.volumes[0]
    vol.cal_min = center - width / 2
    vol.cal_max = center + width / 2
    nv.updateGLVolume()
  }
  render()
}

function scrollView(viewIndex: number, steps: number) {
  const axis = AXIS_OF_VIEW[viewIndex]
  const n = dimsRAS[axis + 1]
  pos[axis] = Math.min(1, Math.max(0, pos[axis] + steps / n))
  render()
}

function tileUnderMouse(nv: Niivue, canvas: HTMLCanvasElement, e: MouseEvent): number | null {
  const rect = canvas.getBoundingClientRect()
  const x = ((e.clientX - rect.left) * canvas.width) / rect.width
  const y = ((e.clientY - rect.top) * canvas.height) / rect.height
  for (const s of nv.screenSlices) {
    const [l, t, w, h] = s.leftTopWidthHeight
    if (w > 0 && x >= l && x <= l + w && y >= t && y <= t + h) return s.axCorSag as number
  }
  return null
}

async function createColumn(slot: string): Promise<Niivue> {
  const col = document.createElement('div')
  col.className = 'col'
  col.innerHTML = `<h2>Imagem ${slot}</h2><div class="cv"><canvas></canvas></div>`
  cols.appendChild(col)
  const canvas = col.querySelector('canvas') as HTMLCanvasElement
  const cv = col.querySelector('.cv') as HTMLDivElement
  const lupas = VIEW_NAMES.map((name, v) => {
    const b = document.createElement('button')
    b.className = 'lupa'
    b.innerHTML = '&#128269;'
    b.setAttribute('aria-label', `Ampliar ${name} da imagem ${slot}`)
    b.addEventListener('click', () => openZoom(v, slot))
    cv.appendChild(b)
    return b
  })
  lupaSets.push({ canvas, lupas })

  const nv = new Niivue({
    isColorbar: false,
    isRuler: false,
    isOrientCube: false,
    show3Dcrosshair: false,
    crosshairWidth: 0,
    multiplanarShowRender: SHOW_RENDER.NEVER,
    multiplanarLayout: MULTIPLANAR_TYPE.COLUMN,
    backColor: [0, 0, 0, 1],
    mouseEventConfig: {
      leftButton: { primary: DRAG_MODE.none },
      rightButton: DRAG_MODE.none,
      centerButton: DRAG_MODE.none,
    },
    touchEventConfig: { singleTouch: DRAG_MODE.none, doubleTouch: DRAG_MODE.none },
  })
  await nv.attachToCanvas(canvas)
  await nv.loadVolumes([{ url: `/dev-data/${CASE}/${CASE}_vol_${slot}.nii.gz`, colormap: 'gray' }])
  nv.setSliceType(SLICE_TYPE.MULTIPLANAR)

  // Own wheel handler (capture phase) replaces Niivue's, which would move all views together.
  canvas.addEventListener(
    'wheel',
    (e) => {
      e.preventDefault()
      e.stopImmediatePropagation()
      const tile = tileUnderMouse(nv, canvas, e)
      if (tile !== null) scrollView(tile, e.deltaY > 0 ? 1 : -1)
    },
    { capture: true, passive: false },
  )

  blockPointer(canvas)
  return nv
}

// No click, drag, touch or key may move Niivue's own crosshair: that would desync this column.
function blockPointer(canvas: HTMLCanvasElement, keepPointer = false) {
  const BLOCKED = [
    'click', 'dblclick', 'mousedown', 'mouseup', 'mousemove', 'contextmenu',
    'touchstart', 'touchmove', 'touchend', 'keydown', 'keyup',
  ]
  // The enlarged viewer reads pointer events itself to pan, so it keeps them.
  if (!keepPointer) BLOCKED.push('pointerdown', 'pointerup', 'pointermove')
  for (const type of BLOCKED) {
    canvas.addEventListener(type, (e) => e.stopImmediatePropagation(), { capture: true })
  }
}

function placeLupas() {
  for (const { canvas, lupas } of lupaSets) {
    const k = canvas.clientHeight / canvas.height
    instances[0].screenSlices.forEach((s) => {
      const [l, t, w, h] = s.leftTopWidthHeight
      const b = lupas[s.axCorSag as number]
      if (!b || h <= 0) return
      b.style.top = `${t * k + 4}px`
      b.style.left = `${(l + w) * k - 30}px`
    })
  }
}

// ---- Enlarged viewer ----

const zoomBox = document.getElementById('zoom') as HTMLDivElement
const zoomCanvas = document.getElementById('zoomcv') as HTMLCanvasElement
const zoomTitle = document.getElementById('ztitle') as HTMLSpanElement
const zoomSlider = document.getElementById('zl') as HTMLInputElement
const zoomOut = document.getElementById('zlv') as HTMLOutputElement
const zoomPicks = document.getElementById('zpick') as HTMLSpanElement

function applyZoom() {
  if (!zoomNv) return
  // Niivue zooms about the world origin; (1 - zoom) * centre keeps the volume centre in place. zoomPan is the drag offset.
  const c = zoomNv.frac2mm([0.5, 0.5, 0.5])
  const k = 1 - zoom.level
  zoomNv.setPan2Dxyzmm([zoomPan[0] + k * c[0], zoomPan[1] + k * c[1], zoomPan[2] + k * c[2], zoom.level])
  zoomOut.textContent = `${Math.round(zoom.level * 100)}%`
}

async function loadZoomSlot(slot: string) {
  if (!zoomNv) return
  zoom.slot = slot
  await zoomNv.loadVolumes([{ url: `/dev-data/${CASE}/${CASE}_vol_${slot}.nii.gz`, colormap: 'gray' }])
  zoomNv.setSliceType(zoom.view)
  zoomTitle.textContent = `Imagem ${slot} - ${VIEW_NAMES[zoom.view]}`
  zoomPicks.querySelectorAll('button').forEach((b) => b.classList.toggle('on', b.dataset.slot === slot))
  applyWindow()
  applyZoom()
}

async function openZoom(viewIndex: number, slot: string) {
  zoom.view = viewIndex
  zoom.level = 1
  zoomPan[0] = zoomPan[1] = zoomPan[2] = 0
  zoomSlider.value = '1'
  zoomBox.hidden = false
  if (!zoomNv) {
    zoomNv = new Niivue({
      isColorbar: false,
      isRuler: false,
      isOrientCube: false,
      show3Dcrosshair: false,
      crosshairWidth: 0,
      backColor: [0, 0, 0, 1],
      mouseEventConfig: {
        leftButton: { primary: DRAG_MODE.none },
        rightButton: DRAG_MODE.none,
        centerButton: DRAG_MODE.none,
      },
      touchEventConfig: { singleTouch: DRAG_MODE.none, doubleTouch: DRAG_MODE.none },
    })
    await zoomNv.attachToCanvas(zoomCanvas)
    zoomCanvas.addEventListener(
      'wheel',
      (e) => {
        e.preventDefault()
        e.stopImmediatePropagation()
        scrollView(zoom.view, e.deltaY > 0 ? 1 : -1)
      },
      { capture: true, passive: false },
    )
    blockPointer(zoomCanvas, true)
    ;(window as unknown as { __zoomNv: Niivue }).__zoomNv = zoomNv
  }
  await loadZoomSlot(slot)
  render()
}

function closeZoom() {
  zoomBox.hidden = true
}

function bindZoom() {
  zoomPicks.innerHTML = SLOTS.map((s) => `<button data-slot="${s}">${s}</button>`).join('')
  zoomPicks.querySelectorAll('button').forEach((b) =>
    b.addEventListener('click', () => loadZoomSlot((b as HTMLButtonElement).dataset.slot!)),
  )
  zoomSlider.addEventListener('input', () => {
    zoom.level = Number(zoomSlider.value)
    if (zoom.level === 1) zoomPan[0] = zoomPan[1] = zoomPan[2] = 0
    applyZoom()
  })
  document.getElementById('zclose')!.addEventListener('click', closeZoom)
  window.addEventListener('keydown', (e) => {
    if (zoomBox.hidden) return
    if (e.key === 'Escape') closeZoom()
    const i = 'abcde'.indexOf(e.key.toLowerCase())
    if (e.key.length === 1 && i >= 0) loadZoomSlot(SLOTS[i])
  })
  // Dragging pans the enlarged image (Niivue's own drag is disabled, so we do it by hand).
  let drag: { x: number; y: number } | null = null
  zoomCanvas.addEventListener('pointerdown', (e) => {
    drag = { x: e.clientX, y: e.clientY }
    zoomCanvas.setPointerCapture(e.pointerId)
  })
  zoomCanvas.addEventListener('pointermove', (e) => {
    if (!drag) return
    // Pan units are mm of the unzoomed view: fovMM shrinks with the zoom level, so scale it back up.
    const k = (zoomNv!.screenSlices[0].fovMM[0] * zoom.level) / zoomCanvas.clientWidth
    zoomPan[0] += (e.clientX - drag.x) * k
    zoomPan[1] -= (e.clientY - drag.y) * k
    drag = { x: e.clientX, y: e.clientY }
    applyZoom()
  })
  zoomCanvas.addEventListener('pointerup', () => (drag = null))
}

function buildGutter() {
  const col = document.createElement('div')
  col.className = 'col'
  col.innerHTML = '<h2>&nbsp;</h2><div id="gutter"></div>'
  cols.prepend(col)
  const gutter = col.querySelector('#gutter') as HTMLDivElement
  const groups = VIEW_NAMES.map((name, v) => {
    const g = document.createElement('div')
    g.className = 'rowctl'
    g.innerHTML = `<button aria-label="${name}: corte seguinte">&#9650;</button><span>${name}</span><button aria-label="${name}: corte anterior">&#9660;</button>`
    const [up, down] = Array.from(g.querySelectorAll('button'))
    holdToRepeat(up, () => scrollView(v, 1))
    holdToRepeat(down, () => scrollView(v, -1))
    gutter.appendChild(g)
    return g
  })
  const place = () => {
    const canvas = cols.querySelector('canvas') as HTMLCanvasElement
    const k = canvas.clientHeight / canvas.height
    instances[0].screenSlices.forEach((s) => {
      const [, t, , h] = s.leftTopWidthHeight
      if (h > 0 && groups[s.axCorSag]) groups[s.axCorSag].style.top = `${(t + h / 2) * k}px`
    })
  }
  new ResizeObserver(() =>
    requestAnimationFrame(() => {
      place()
      placeLupas()
    }),
  ).observe(gutter)
  place()
  placeLupas()
}

function holdToRepeat(btn: HTMLButtonElement, action: () => void) {
  let delay = 0
  let timer = 0
  const stop = () => {
    clearTimeout(delay)
    clearInterval(timer)
  }
  btn.addEventListener('pointerdown', (e) => {
    e.preventDefault()
    action()
    delay = window.setTimeout(() => {
      timer = window.setInterval(action, 60)
    }, 350)
  })
  for (const ev of ['pointerup', 'pointerleave', 'pointercancel']) btn.addEventListener(ev, stop)
}

function bindToolbar() {
  const br = document.getElementById('br') as HTMLInputElement
  const ct = document.getElementById('ct') as HTMLInputElement
  const brv = document.getElementById('brv') as HTMLOutputElement
  const ctv = document.getElementById('ctv') as HTMLOutputElement
  const sync = () => {
    view.brightness = Number(br.value)
    view.contrast = Number(ct.value)
    brv.textContent = String(view.brightness)
    ctv.textContent = `${view.contrast}%`
    applyWindow()
  }
  br.addEventListener('input', sync)
  ct.addEventListener('input', sync)
  document.getElementById('rs')!.addEventListener('click', () => {
    br.value = '0'
    ct.value = '100'
    sync()
  })
}

async function main() {
  instances.push(...(await Promise.all(SLOTS.map(createColumn))))
  dimsRAS = instances[0].volumes[0].dimsRAS ?? instances[0].volumes[0].dims ?? dimsRAS
  buildGutter()
  bindToolbar()
  bindZoom()
  // The enlarged viewer starts below the toolbar so brightness/contrast stay usable.
  const tb = document.getElementById('tb') as HTMLDivElement
  document.documentElement.style.setProperty('--tbh', `${tb.getBoundingClientRect().bottom}px`)
  applyWindow()
  ;(window as unknown as { __view: typeof view }).__view = view
}

main().catch((err) => {
  msg.textContent = `Erro: ${err instanceof Error ? err.message : String(err)}`
  console.error(err)
})
