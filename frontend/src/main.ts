import { Niivue, MULTIPLANAR_TYPE, SHOW_RENDER, SLICE_TYPE } from '@niivue/niivue'

const SLOTS = ['A', 'B', 'C', 'D', 'E']
const CASE = 'case_01'

const cols = document.getElementById('cols') as HTMLDivElement
const msg = document.getElementById('msg') as HTMLDivElement

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
    multiplanarShowRender: SHOW_RENDER.NEVER,
    multiplanarLayout: MULTIPLANAR_TYPE.COLUMN,
    backColor: [0, 0, 0, 1],
  })
  await nv.attachToCanvas(canvas)
  await nv.loadVolumes([{ url: `/dev-data/${CASE}/${CASE}_vol_${slot}.nii.gz`, colormap: 'gray' }])
  nv.setSliceType(SLICE_TYPE.MULTIPLANAR)
  return nv
}

async function main() {
  const t0 = performance.now()
  const instances = await Promise.all(SLOTS.map(createColumn))
  const dims = instances.map((nv) => nv.volumes[0].dims?.slice(1, 4).join('x'))
  const secs = ((performance.now() - t0) / 1000).toFixed(1)
  msg.textContent = `${instances.length} volumes carregados em ${secs}s (${dims.join(' | ')})`
}

main().catch((err) => {
  msg.textContent = `Erro: ${err instanceof Error ? err.message : String(err)}`
  console.error(err)
})
