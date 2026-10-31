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

function scrollView(view: number, steps: number) {
  const axis = AXIS_OF_VIEW[view]
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
      const view = tileUnderMouse(nv, canvas, e)
      if (view !== null) scrollView(view, e.deltaY > 0 ? 1 : -1)
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

async function main() {
  instances.push(...(await Promise.all(SLOTS.map(createColumn))))
  dimsRAS = instances[0].volumes[0].dimsRAS ?? instances[0].volumes[0].dims ?? dimsRAS
  render()
}

main().catch((err) => {
  msg.textContent = `Erro: ${err instanceof Error ? err.message : String(err)}`
  console.error(err)
})
