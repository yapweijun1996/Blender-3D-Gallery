import assert from 'node:assert/strict'
import {createHash} from 'node:crypto'
import {readFile, writeFile} from 'node:fs/promises'
import validator from '../../../node_modules/gltf-validator/index.js'
import {Box3, Vector3} from 'three'
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js'

const budgets = {
  'hdb_block.glb': 2200,
  'hdb_void_deck.glb': 2500,
  'hdb_coffee_shop.glb': 1800,
  'provision_shop.glb': 1200,
  'shoplot.glb': 1800,
  'public_market.glb': 3000,
  'mrt_entrance.glb': 2000,
}

const allowedMaterials = new Set([
  'paint', 'glass', 'tire', 'light', 'trim', 'wall', 'roof', 'window',
  'leaf', 'trunk', 'metal', 'concrete', 'chrome', 'plate',
])
const forbidden = ['animations', 'skins', 'cameras', 'textures', 'images', 'samplers',
  'extensions', 'extensionsUsed', 'extensionsRequired']
const rounded = (number) => Number(number.toFixed(4))

const models = []
let failures = 0
for (const [file, budget] of Object.entries(budgets)) {
  try {
    const bytes = await readFile(new URL(file, import.meta.url))
    assert.equal(bytes.toString('ascii', 0, 4), 'glTF')
    assert.equal(bytes.readUInt32LE(4), 2)
    assert.equal(bytes.readUInt32LE(8), bytes.length)
    assert.ok(bytes.length <= 350_000, `${file} exceeds 350 KB`)
    const jsonSize = bytes.readUInt32LE(12)
    const doc = JSON.parse(bytes.toString('utf8', 20, 20 + jsonSize))
    for (const key of forbidden) assert.equal(doc[key], undefined, `${file} contains ${key}`)
    assert.equal(doc.buffers.length, 1)
    assert.equal(doc.buffers[0].uri, undefined)
    assert.equal(doc.meshes.length, 1)
    assert.equal(doc.nodes.length, 1)
    assert.deepEqual(doc.scenes[doc.scene].nodes, [0])
    assert.equal(doc.nodes[0].mesh, 0)
    for (const field of ['matrix', 'translation', 'scale', 'rotation']) {
      assert.equal(doc.nodes[0][field], undefined, `${file} has node ${field}`)
    }
    const primitives = doc.meshes[0].primitives
    assert.ok(primitives.length <= 16)
    assert.equal(new Set(primitives.map((primitive) => primitive.material)).size, primitives.length)

    const materials = doc.materials.map((material) => material.name)
    assert.equal(materials.length, primitives.length)
    for (const material of materials) assert.ok(allowedMaterials.has(material), material)

    const min = [Infinity, Infinity, Infinity]
    const max = [-Infinity, -Infinity, -Infinity]
    let triangles = 0
    for (const primitive of primitives) {
      assert.equal(primitive.mode ?? 4, 4)
      assert.deepEqual(Object.keys(primitive.attributes).sort(), ['NORMAL', 'POSITION'])
      const count = doc.accessors[primitive.indices].count
      assert.equal(count % 3, 0)
      triangles += count / 3
      const positions = doc.accessors[primitive.attributes.POSITION]
      for (let axis = 0; axis < 3; axis++) {
        min[axis] = Math.min(min[axis], positions.min[axis])
        max[axis] = Math.max(max[axis], positions.max[axis])
      }
    }
    assert.ok(triangles <= budget)
    assert.ok(Math.abs(min[1]) < 1e-5, `${file} base sits at ${min[1]}`)

    const payload = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.length)
    const loaded = await new GLTFLoader().parseAsync(payload, '')
    const loadedSize = new Box3().setFromObject(loaded.scene).getSize(new Vector3()).toArray()
    assert.deepEqual(loadedSize.map(rounded), max.map((value, axis) => rounded(value - min[axis])))
    let loadedPrimitives = 0
    let loadedTriangles = 0
    loaded.scene.traverse((node) => {
      if (node.isMesh) {
        loadedPrimitives++
        loadedTriangles += node.geometry.index.count / 3
      }
    })
    assert.equal(loadedPrimitives, primitives.length)
    assert.equal(loadedTriangles, triangles)

    const report = await validator.validateBytes(bytes, {uri: file, maxIssues: 0})
    const {numErrors, numWarnings, numInfos, numHints, messages} = report.issues
    const stats = {
      file, triangles, bytes: bytes.length,
      size_metres: {width_x: rounded(max[0] - min[0]), height_y: rounded(max[1] - min[1]),
        depth_z: rounded(max[2] - min[2])},
      materials, primitives: primitives.length,
      sha256: createHash('sha256').update(bytes).digest('hex'),
      validator: {version: report.validatorVersion, errors: numErrors, warnings: numWarnings,
        infos: numInfos, hints: numHints, result: numErrors || numWarnings ? 'FAIL' : 'PASS'},
    }
    stats.three_js_load = 'PASS'
    console.log(JSON.stringify(stats), numErrors || numWarnings ? JSON.stringify(messages) : '')
    models.push(stats)
    if (numErrors || numWarnings) failures++
  } catch (error) {
    failures++
    console.error(file, error.message)
  }
}

if (failures) {
  process.exitCode = 1
} else {
  await writeFile(new URL('models.json', import.meta.url), JSON.stringify(models, null, 2) + '\n')
}
