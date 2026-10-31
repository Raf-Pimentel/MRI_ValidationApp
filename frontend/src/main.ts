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

function render() {
  for (const nv of instances) {
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
  for (const nv of instances) {
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
  col.innerHTML = `<h2>Imagem ${slot}</h2><canvas></canvas>`
  cols.appendChild(col)
  const canvas = col.querySelector('canvas') as HTMLCanvasElement

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

  // No click, drag, touch or key may move Niivue's own crosshair: that would desync this column.
  const BLOCKED = [
    'click', 'dblclick', 'mousedown', 'mouseup', 'mousemove', 'contextmenu',
    'pointerdown', 'pointerup', 'pointermove', 'touchstart', 'touchmove', 'touchend',
    'keydown', 'keyup',
  ]
  for (const type of BLOCKED) {
    canvas.addEventListener(type, (e) => e.stopImmediatePropagation(), { capture: true })
  }
  return nv
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
  new ResizeObserver(() => requestAnimationFrame(place)).observe(gutter)
  place()
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
  applyWindow()
  ;(window as unknown as { __view: typeof view }).__view = view
}

main().catch((err) => {
  msg.textContent = `Erro: ${err instanceof Error ? err.message : String(err)}`
  console.error(err)
})
