import { Niivue, MULTIPLANAR_TYPE, SHOW_RENDER, SLICE_TYPE } from '@niivue/niivue'

const canvas = document.getElementById('gl') as HTMLCanvasElement
const msg = document.getElementById('msg') as HTMLDivElement

async function main() {
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
  await nv.loadVolumes([{ url: '/dev-data/case_01/case_01_vol_A.nii.gz', colormap: 'gray' }])
  nv.setSliceType(SLICE_TYPE.MULTIPLANAR)
  const dims = nv.volumes[0].dims
  msg.textContent = `Volume carregado: ${dims?.[1]} x ${dims?.[2]} x ${dims?.[3]}`
}

main().catch((err) => {
  msg.textContent = `Erro: ${err instanceof Error ? err.message : String(err)}`
  console.error(err)
})
