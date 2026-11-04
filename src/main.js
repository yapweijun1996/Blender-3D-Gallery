import './style.css';
import catalog from 'virtual:gallery-catalog';

const dialog = document.querySelector('#viewer');
const viewport = document.querySelector('#viewport');
const status = document.querySelector('#viewer-status');
const title = document.querySelector('#viewer-title');
const category = document.querySelector('#viewer-category');
const description = document.querySelector('#viewer-description');
const download = document.querySelector('#viewer-download');
const catalogElement = document.querySelector('#catalog');
const assets = catalog.collections.flatMap(collection => collection.assets);
const assetById = new Map(assets.map(asset => [asset.id, asset]));
let controller;
let activeViewer;
let opener;

function formatBytes(bytes) {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(2)} MiB` : `${(bytes / 1024).toFixed(1)} KiB`;
}
function createCard(asset, featured = false) {
  const card = document.createElement('article');
  card.className = `asset-card${featured ? ' asset-card-featured' : ''}`;
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'asset-image';
  button.dataset.assetId = asset.id;
  button.setAttribute('aria-label', `Preview ${asset.name} in 3D`);
  const image = document.createElement('img');
  image.src = asset.thumbnail;
  image.alt = `${asset.name} 3D model preview`;
  image.width = 400;
  image.height = 400;
  image.loading = 'lazy';
  const label = document.createElement('span');
  label.className = 'asset-image-label';
  label.textContent = 'VIEW IN 3D ↗';
  button.append(image, label);
  const body = document.createElement('div');
  body.className = 'asset-body';
  const group = document.createElement('p');
  group.className = 'asset-category';
  group.textContent = asset.category;
  const name = document.createElement('h4');
  name.textContent = asset.name;
  const metrics = document.createElement('p');
  metrics.className = 'asset-metrics';
  metrics.textContent = `${asset.triangles.toLocaleString()} triangles · ${formatBytes(asset.bytes)}`;
  const link = document.createElement('a');
  link.className = 'asset-download';
  link.href = asset.file;
  link.download = `${asset.id}.glb`;
  link.setAttribute('aria-label', `Download ${asset.name} GLB`);
  link.textContent = 'Download GLB ↓';
  body.append(group, name, metrics, link);
  card.append(button, body);
  button.addEventListener('click', () => openViewer(asset, button));
  return card;
}
for (const collection of catalog.collections) {
  const section = document.createElement('section');
  section.className = 'asset-collection';
  section.setAttribute('aria-label', collection.name);
  const heading = document.createElement('div');
  heading.className = 'collection-title';
  const collectionName = document.createElement('h3');
  collectionName.textContent = collection.name;
  const collectionDescription = document.createElement('p');
  collectionDescription.textContent = collection.description;
  heading.append(collectionName, collectionDescription);
  section.append(heading);
  const individual = collection.assets.filter(asset => asset.category !== 'Showcase');
  const grid = document.createElement('div');
  grid.className = 'asset-grid';
  for (const asset of individual) grid.append(createCard(asset));
  section.append(grid);
  const showcases = collection.assets.filter(asset => asset.category === 'Showcase');
  if (showcases.length) {
    const header = document.createElement('div');
    header.className = 'showcase-heading';
    const h = document.createElement('h4');
    h.textContent = 'Complete collection';
    const p = document.createElement('p');
    p.textContent = 'See the assembled scene.';
    header.append(h, p);
    section.append(header);
    for (const asset of showcases) section.append(createCard(asset, true));
  }
  catalogElement.append(section);
}

async function openViewer(asset, trigger, updateUrl = true) {
  controller?.abort();
  activeViewer?.dispose();
  activeViewer = null;
  controller = new AbortController();
  const { signal } = controller;
  opener = trigger || document.querySelector(`[data-asset-id="${asset.id}"]`);
  title.textContent = asset.name;
  category.textContent = `${asset.category.toUpperCase()} / INTERACTIVE 3D`;
  description.textContent = `${asset.triangles.toLocaleString()} triangles · ${formatBytes(asset.bytes)} · GLB`;
  download.href = asset.file;
  download.download = `${asset.id}.glb`;
  download.setAttribute('aria-label', `Download ${asset.name} GLB`);
  if (!dialog.open) dialog.showModal();
  document.querySelector('#close-viewer').focus();
  if (updateUrl) {
    const url = new URL(location.href);
    url.searchParams.set('model', asset.id);
    history.pushState({}, '', url);
  }
  status.textContent = 'Loading the 3D model…';
  try {
    const { default: createViewer } = await import('./viewer.js');
    if (signal.aborted) return;
    const viewer = await createViewer(viewport, asset.file, status, signal, asset.name);
    if (signal.aborted) { viewer.dispose(); return; }
    activeViewer = viewer;
    document.querySelector('#reset-view').onclick = viewer.reset;
  } catch (error) {
    if (signal.aborted) return;
    console.error('Unable to load the 3D viewer:', error);
    status.textContent = '3D view unavailable. Close and reopen it to retry.';
  }
}
function closeViewer(updateUrl = true) {
  controller?.abort();
  activeViewer?.dispose();
  activeViewer = null;
  document.querySelector('#reset-view').onclick = null;
  if (dialog.open) dialog.close();
  if (updateUrl) {
    const url = new URL(location.href);
    if (url.searchParams.has('model')) { url.searchParams.delete('model'); history.replaceState({}, '', url); }
  }
  opener?.focus();
}
document.querySelector('#close-viewer').addEventListener('click', () => closeViewer());
dialog.addEventListener('cancel', event => { event.preventDefault(); closeViewer(); });
dialog.addEventListener('click', event => { if (event.target === dialog) closeViewer(); });
function syncUrl() {
  const id = new URL(location.href).searchParams.get('model');
  if (assetById.has(id)) openViewer(assetById.get(id), null, false);
  else if (dialog.open) closeViewer(false);
}
window.addEventListener('popstate', syncUrl);
syncUrl();
