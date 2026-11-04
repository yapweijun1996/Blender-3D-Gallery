import './style.css';
import posterUrl from '../models/eight-ball-billiards/preview.webp';
import modelUrl from '../models/eight-ball-billiards/exports/billiards-scene.glb?url';

document.querySelector('#poster').src = posterUrl;
const dialog = document.querySelector('#viewer');
const viewport = document.querySelector('#viewport');
const status = document.querySelector('#viewer-status');
const openButton = document.querySelector('#open-viewer');
let disposeViewer = () => {};
let generation = 0;

async function openViewer(updateUrl = true) {
  if (dialog.open) return;
  dialog.showModal();
  document.querySelector('#close-viewer').focus();
  if (updateUrl) {
    const url = new URL(location.href);
    url.searchParams.set('model', 'eight-ball-billiards');
    history.pushState({}, '', url);
  }
  const run = ++generation;
  status.textContent = 'Loading the 3D model…';
  try {
    const [{ default: createViewer }] = await Promise.all([import('./viewer.js')]);
    if (run !== generation) return;
    const viewer = await createViewer(viewport, modelUrl, status);
    if (run !== generation) { viewer.dispose(); return; }
    disposeViewer = viewer.dispose;
    document.querySelector('#reset-view').onclick = viewer.reset;
  } catch (error) {
    console.error('Unable to load the 3D viewer:', error);
    if (run === generation) status.textContent = '3D view unavailable. Close this window to see the preview image.';
  }
}
function closeViewer() {
  ++generation;
  disposeViewer();
  disposeViewer = () => {};
  document.querySelector('#reset-view').onclick = null;
  if (dialog.open) dialog.close();
  const url = new URL(location.href);
  if (url.searchParams.has('model')) { url.searchParams.delete('model'); history.replaceState({}, '', url); }
  openButton.focus();
}
openButton.addEventListener('click', () => openViewer());
document.querySelector('#close-viewer').addEventListener('click', closeViewer);
dialog.addEventListener('cancel', event => { event.preventDefault(); closeViewer(); });
dialog.addEventListener('click', event => { if (event.target === dialog) closeViewer(); });
window.addEventListener('popstate', () => {
  if (new URL(location.href).searchParams.get('model') === 'eight-ball-billiards') openViewer(false);
  else if (dialog.open) closeViewer();
});
if (new URL(location.href).searchParams.get('model') === 'eight-ball-billiards') openViewer(false);
