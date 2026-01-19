import * as THREE from "./three/three.module.js";
import { OrbitControls } from "./three/OrbitControls.js";
import { GLTFLoader } from "./three/GLTFLoader.js";

const container = document.getElementById("viewer-root");
const overlay = document.getElementById("overlay");
const overlayStatus = overlay ? overlay.querySelector(".status") : null;
const overlayDetails = overlay ? overlay.querySelector(".details") : null;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0f1115);

const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 1000);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio || 1);
container.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;

const hemiLight = new THREE.HemisphereLight(0xffffff, 0x222831, 0.9);
scene.add(hemiLight);

const keyLight = new THREE.DirectionalLight(0xffffff, 0.8);
keyLight.position.set(4, 6, 3);
scene.add(keyLight);

const fillLight = new THREE.DirectionalLight(0x9fb4ff, 0.35);
fillLight.position.set(-4, 2, -3);
scene.add(fillLight);

let currentModel = null;

const loader = new GLTFLoader();

function setOverlay(status, details) {
  if (!overlay || !overlayStatus || !overlayDetails) return;
  overlayStatus.textContent = status;
  overlayDetails.textContent = details;
  overlay.classList.remove("hidden");
}

function hideOverlay() {
  overlay?.classList.add("hidden");
}

function resize() {
  const { clientWidth, clientHeight } = container;
  if (!clientWidth || !clientHeight) return;
  camera.aspect = clientWidth / clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(clientWidth, clientHeight, false);
}

function fitCameraToObject(object) {
  const boundingBox = new THREE.Box3().setFromObject(object);
  const size = boundingBox.getSize(new THREE.Vector3());
  const center = boundingBox.getCenter(new THREE.Vector3());

  const maxDim = Math.max(size.x, size.y, size.z);
  const fov = camera.fov * (Math.PI / 180);
  let cameraZ = Math.abs(maxDim / (2 * Math.tan(fov / 2)));
  cameraZ *= 1.6;

  camera.position.set(center.x + cameraZ, center.y + cameraZ * 0.6, center.z + cameraZ);
  camera.near = maxDim / 100;
  camera.far = maxDim * 100;
  camera.updateProjectionMatrix();

  controls.target.copy(center);
  controls.update();
}

window.loadModel = function loadModel(url) {
  if (!url) {
    setOverlay("No model URL", "Provide a valid GLB path.");
    return;
  }

  setOverlay("Loading", "Fetching model...");

  loader.load(
    url,
    (gltf) => {
      if (currentModel) {
        scene.remove(currentModel);
      }
      currentModel = gltf.scene;
      scene.add(currentModel);
      fitCameraToObject(currentModel);
      hideOverlay();
    },
    (event) => {
      if (event && event.total) {
        const progress = Math.round((event.loaded / event.total) * 100);
        setOverlay("Loading", `Downloading model (${progress}%).`);
      }
    },
    (error) => {
      console.error("Failed to load model", error);
      setOverlay("Load failed", "Unable to load GLB file.");
    }
  );
};

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}

window.addEventListener("resize", resize);

resize();
animate();
