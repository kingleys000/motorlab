import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

const viewer = document.getElementById('viewer');

const labelRenderer = new CSS2DRenderer();
labelRenderer.setSize(window.innerWidth, window.innerHeight);
labelRenderer.domElement.id = 'labels-layer';
viewer.appendChild(labelRenderer.domElement);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.1;
viewer.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x14161a);

const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.55;

const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
const CAMERA_HOME = new THREE.Vector3(4.6, 2.6, 5.4);
const TARGET_HOME = new THREE.Vector3(0, 0.1, 0);
camera.position.copy(CAMERA_HOME);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.copy(TARGET_HOME);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.maxDistance = 20;
controls.minDistance = 1.5;

const keyLight = new THREE.DirectionalLight(0xffffff, 2.6);
keyLight.position.set(5, 8, 4);
keyLight.castShadow = true;
keyLight.shadow.mapSize.set(2048, 2048);
keyLight.shadow.camera.left = -7;
keyLight.shadow.camera.right = 7;
keyLight.shadow.camera.top = 7;
keyLight.shadow.camera.bottom = -7;
keyLight.shadow.normalBias = 0.02;
keyLight.shadow.radius = 4;
scene.add(keyLight);

const fillLight = new THREE.DirectionalLight(0xbfd0e8, 0.5);
fillLight.position.set(-6, 3, -5);
scene.add(fillLight);

const materials = {
  steel: new THREE.MeshStandardMaterial({ color: 0x8b939c, metalness: 0.9, roughness: 0.35 }),
  steelCut: new THREE.MeshStandardMaterial({ color: 0x8b939c, metalness: 0.9, roughness: 0.35, side: THREE.DoubleSide }),
  aluminum: new THREE.MeshStandardMaterial({ color: 0xc8ccd2, metalness: 0.85, roughness: 0.4 }),
  polished: new THREE.MeshStandardMaterial({ color: 0xe3e6ea, metalness: 1.0, roughness: 0.12 }),
  lamination: new THREE.MeshStandardMaterial({ color: 0x555b63, metalness: 0.85, roughness: 0.45 }),
  laminationAlt: new THREE.MeshStandardMaterial({ color: 0x494f57, metalness: 0.85, roughness: 0.45 }),
  copper: new THREE.MeshStandardMaterial({ color: 0xb87333, metalness: 1.0, roughness: 0.28 }),
  ferrite: new THREE.MeshStandardMaterial({ color: 0x3a3d42, metalness: 0.4, roughness: 0.6 }),
  graphite: new THREE.MeshStandardMaterial({ color: 0x26282c, metalness: 0.2, roughness: 0.8 }),
  brass: new THREE.MeshStandardMaterial({ color: 0xa8893c, metalness: 0.9, roughness: 0.35 }),
  red: new THREE.MeshStandardMaterial({ color: 0xa02828, metalness: 0.1, roughness: 0.5 }),
  black: new THREE.MeshStandardMaterial({ color: 0x1c1e22, metalness: 0.1, roughness: 0.5 }),
};

function tubeX(radius, length, material, options = {}) {
  const geometry = new THREE.CylinderGeometry(
    radius, radius, length,
    options.segments ?? 64, 1, options.open ?? false,
    options.thetaStart ?? 0, options.thetaLength ?? Math.PI * 2,
  );
  geometry.rotateZ(Math.PI / 2);
  return new THREE.Mesh(geometry, material);
}

function solidCylinderX(radius, length, material, segments = 64) {
  const geometry = new THREE.CylinderGeometry(radius, radius, length, segments);
  geometry.rotateZ(Math.PI / 2);
  return new THREE.Mesh(geometry, material);
}

function box(width, height, depth, material) {
  return new THREE.Mesh(new THREE.BoxGeometry(width, height, depth), material);
}

function torusX(radius, tube, material) {
  const geometry = new THREE.TorusGeometry(radius, tube, 24, 96);
  geometry.rotateY(Math.PI / 2);
  return new THREE.Mesh(geometry, material);
}

function magnetArc(angleCenter, material) {
  const shape = new THREE.Shape();
  const halfAngle = Math.PI / 3.2;
  const start = angleCenter - halfAngle;
  const end = angleCenter + halfAngle;
  shape.absarc(0, 0, 0.93, start, end, false);
  shape.absarc(0, 0, 0.76, end, start, true);
  shape.closePath();
  const geometry = new THREE.ExtrudeGeometry(shape, { depth: 1.9, bevelEnabled: false, curveSegments: 48 });
  geometry.translate(0, 0, -0.95);
  geometry.rotateY(Math.PI / 2);
  return new THREE.Mesh(geometry, material);
}

const motor = new THREE.Group();
motor.position.y = 0.15;
scene.add(motor);

const CUT_START = Math.PI * 0.1;
const CUT_LENGTH = Math.PI * 1.5;

function buildHousing(cut) {
  const group = new THREE.Group();
  const thetaStart = cut ? CUT_START : 0;
  const thetaLength = cut ? CUT_LENGTH : Math.PI * 2;
  const material = cut ? materials.steelCut : materials.steel;

  group.add(tubeX(1.0, 2.2, material, { open: true, thetaStart, thetaLength, segments: 96 }));

  for (let i = 0; i < 9; i += 1) {
    const fin = tubeX(1.06, 0.045, material, { open: true, thetaStart, thetaLength, segments: 96 });
    fin.position.x = -0.96 + i * 0.24;
    group.add(fin);
  }

  if (cut) {
    for (const angle of [CUT_START, CUT_START + CUT_LENGTH]) {
      const edge = box(2.2, 0.035, 1.06, materials.steel);
      edge.position.set(0, Math.sin(angle) * 0.53, Math.cos(angle) * 0.53);
      edge.rotation.x = -angle;
      group.add(edge);
    }
  }
  return group;
}

const housingFull = buildHousing(false);
const housingCut = buildHousing(true);
housingCut.visible = false;
motor.add(housingFull, housingCut);

function buildBell(sign) {
  const group = new THREE.Group();
  const plate = solidCylinderX(1.02, 0.22, materials.aluminum, 96);
  group.add(plate);
  const boss = solidCylinderX(0.42, 0.22, materials.aluminum);
  boss.position.x = sign * 0.18;
  group.add(boss);
  const bearing = torusX(0.17, 0.055, materials.polished);
  bearing.position.x = sign * 0.3;
  group.add(bearing);
  const bearingInner = solidCylinderX(0.13, 0.1, materials.lamination);
  bearingInner.position.x = sign * 0.3;
  group.add(bearingInner);
  for (let i = 0; i < 4; i += 1) {
    const angle = Math.PI / 4 + i * Math.PI / 2;
    const screw = solidCylinderX(0.05, 0.3, materials.polished, 6);
    screw.position.set(0, Math.sin(angle) * 0.86, Math.cos(angle) * 0.86);
    group.add(screw);
  }
  group.position.x = sign * 1.21;
  return group;
}

const frontBell = buildBell(1);
const rearBell = buildBell(-1);
motor.add(frontBell, rearBell);

const magnetTop = magnetArc(Math.PI / 2, materials.ferrite);
const magnetBottom = magnetArc(-Math.PI / 2, materials.ferrite);
motor.add(magnetTop, magnetBottom);

const rotor = new THREE.Group();

const core = solidCylinderX(0.6, 1.6, materials.lamination, 96);
rotor.add(core);
for (let i = 0; i < 26; i += 1) {
  const disc = solidCylinderX(0.66, 0.045, i % 2 ? materials.lamination : materials.laminationAlt, 96);
  disc.position.x = -0.75 + i * 0.06;
  rotor.add(disc);
}

for (let i = 0; i < 12; i += 1) {
  const angle = (i / 12) * Math.PI * 2;
  const winding = solidCylinderX(0.085, 1.72, materials.copper, 24);
  winding.position.set(0, Math.sin(angle) * 0.62, Math.cos(angle) * 0.62);
  rotor.add(winding);
}
for (const sign of [-1, 1]) {
  const endWinding = torusX(0.52, 0.13, materials.copper);
  endWinding.position.x = sign * 0.88;
  rotor.add(endWinding);
}

const shaft = solidCylinderX(0.12, 4.3, materials.polished);
shaft.position.x = 0.35;
rotor.add(shaft);

for (let i = 0; i < 12; i += 1) {
  const geometry = new THREE.CylinderGeometry(0.27, 0.27, 0.34, 8, 1, false, (i / 12) * Math.PI * 2, Math.PI * 2 / 12 * 0.88);
  geometry.rotateZ(Math.PI / 2);
  const segment = new THREE.Mesh(geometry, materials.copper);
  segment.position.x = -1.32;
  rotor.add(segment);
}
motor.add(rotor);

function buildBrush(sign) {
  const group = new THREE.Group();
  const brush = box(0.16, 0.18, 0.22, materials.graphite);
  brush.position.y = sign * 0.33;
  group.add(brush);
  const holder = box(0.2, 0.16, 0.26, materials.brass);
  holder.position.y = sign * 0.5;
  group.add(holder);
  const spring = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.045, 0.22, 16), materials.polished);
  spring.position.y = sign * 0.68;
  group.add(spring);
  group.position.x = -1.32;
  return group;
}

const brushTop = buildBrush(1);
const brushBottom = buildBrush(-1);
motor.add(brushTop, brushBottom);

const terminals = new THREE.Group();
for (const [x, material] of [[-0.3, materials.red], [0.3, materials.black]]) {
  const post = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.055, 0.3, 24), materials.brass);
  post.position.set(x, 1.12, 0);
  terminals.add(post);
  const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.09, 0.09, 6), material);
  cap.position.set(x, 1.3, 0);
  terminals.add(cap);
}
motor.add(terminals);

const base = new THREE.Group();
for (const x of [-0.75, 0.75]) {
  const foot = box(0.35, 0.3, 1.1, materials.steel);
  foot.position.set(x, -1.05, 0);
  base.add(foot);
}
const plate = box(2.6, 0.09, 1.5, materials.lamination);
plate.position.y = -1.24;
base.add(plate);
motor.add(base);

const floor = new THREE.Mesh(
  new THREE.PlaneGeometry(60, 60),
  new THREE.MeshStandardMaterial({ color: 0x1b1e23, metalness: 0.1, roughness: 0.9 }),
);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -1.15;
floor.receiveShadow = true;
scene.add(floor);

motor.traverse((object) => {
  if (object.isMesh) {
    object.castShadow = true;
    object.receiveShadow = true;
  }
});

const explodedParts = [
  { object: frontBell, home: frontBell.position.clone(), offset: new THREE.Vector3(1.5, 0, 0) },
  { object: rearBell, home: rearBell.position.clone(), offset: new THREE.Vector3(-1.6, 0, 0) },
  { object: rotor, home: rotor.position.clone(), offset: new THREE.Vector3(3.1, 0, 0) },
  { object: magnetTop, home: magnetTop.position.clone(), offset: new THREE.Vector3(0, 0.55, 0) },
  { object: magnetBottom, home: magnetBottom.position.clone(), offset: new THREE.Vector3(0, -0.55, 0) },
  { object: brushTop, home: brushTop.position.clone(), offset: new THREE.Vector3(-0.5, 0.7, 0) },
  { object: brushBottom, home: brushBottom.position.clone(), offset: new THREE.Vector3(-0.5, -0.7, 0) },
  { object: terminals, home: terminals.position.clone(), offset: new THREE.Vector3(0, 0.6, 0) },
];

const rotorLabels = new THREE.Group();
motor.add(rotorLabels);
explodedParts.push({ object: rotorLabels, home: rotorLabels.position.clone(), offset: new THREE.Vector3(3.1, 0, 0) });

const componentLabels = [];

function addLabel(text, parent, x, y, z, internal = false) {
  const element = document.createElement('div');
  element.className = 'label3d';
  element.textContent = text;
  const label = new CSS2DObject(element);
  label.position.set(x, y, z);
  parent.add(label);
  componentLabels.push({ label, internal });
}

function updateLabelVisibility() {
  const show = document.getElementById('labels').checked;
  const interiorVisible = document.getElementById('cutaway').checked
    || Number(document.getElementById('explode').value) > 10;
  for (const { label, internal } of componentLabels) {
    label.visible = show && (!internal || interiorVisible);
  }
}

addLabel('Carcasa de acero', motor, -0.4, 1.25, -0.3);
addLabel('Tapa delantera', frontBell, 0.3, 0.8, 0);
addLabel('Tapa trasera', rearBell, -0.2, 0.8, 0);
addLabel('Imán del estator', magnetTop, 0, 0.85, 0, true);
addLabel('Bobinas de cobre', rotorLabels, 0, 0.85, 0.35, true);
addLabel('Eje de acero', rotorLabels, 2.55, 0.25, 0);
addLabel('Conmutador', rotorLabels, -1.32, 0.5, 0.3, true);
addLabel('Escobilla de grafito', brushTop, 0, 0.9, 0, true);
addLabel('Bornes +/−', terminals, 0, 1.6, 0);
addLabel('Base de montaje', base, 1.1, -1.35, 0.6);

const rpmInput = document.getElementById('rpm');
const rpmValue = document.getElementById('rpm-value');
const spinButton = document.getElementById('spin');
const cutawayInput = document.getElementById('cutaway');
const explodeInput = document.getElementById('explode');
const explodeValue = document.getElementById('explode-value');
const resetButton = document.getElementById('reset-camera');

let spinning = true;

rpmInput.addEventListener('input', () => {
  rpmValue.textContent = `${rpmInput.value} RPM`;
});

spinButton.addEventListener('click', () => {
  spinning = !spinning;
  spinButton.textContent = spinning ? 'Detener' : 'Girar';
});

cutawayInput.addEventListener('change', () => {
  housingFull.visible = !cutawayInput.checked;
  housingCut.visible = cutawayInput.checked;
  updateLabelVisibility();
});

explodeInput.addEventListener('input', () => {
  const amount = Number(explodeInput.value) / 100;
  explodeValue.textContent = `${explodeInput.value}%`;
  for (const part of explodedParts) {
    part.object.position.copy(part.home).addScaledVector(part.offset, amount);
  }
  updateLabelVisibility();
});

resetButton.addEventListener('click', () => {
  camera.position.copy(CAMERA_HOME);
  controls.target.copy(TARGET_HOME);
});

const labelsInput = document.getElementById('labels');
labelsInput.addEventListener('change', updateLabelVisibility);
updateLabelVisibility();

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  labelRenderer.setSize(window.innerWidth, window.innerHeight);
});

const clock = new THREE.Clock();
let firstFrame = true;

renderer.setAnimationLoop(() => {
  const delta = Math.min(clock.getDelta(), 0.05);
  if (spinning) {
    const rpm = Number(rpmInput.value);
    const revolutionsPerSecond = 12 * Math.tanh(rpm / 600);
    rotor.rotation.x += revolutionsPerSecond * Math.PI * 2 * delta;
  }
  controls.update();
  renderer.render(scene, camera);
  labelRenderer.render(scene, camera);
  if (firstFrame) {
    firstFrame = false;
    document.getElementById('loading').classList.add('hidden');
  }
});
