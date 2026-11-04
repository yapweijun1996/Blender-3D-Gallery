import './style.css';
import catalog from 'virtual:gallery-catalog';
import { setupPwa } from './pwa/register.js';

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
  if (collection.id === 'solar-system') {
    const link = document.createElement('a');
    link.href = '?page=solar'; link.dataset.page = 'solar'; link.className = 'solar-collection-link';
    link.textContent = 'Explore the Solar System ↗'; section.append(link);
  }
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
  if (asset.details) {
    const facts = asset.details.scientific_properties;
    description.textContent += facts ? ` · ${facts.diameter_km.toLocaleString()} km diameter · ${facts.axial_tilt_degrees}° axial tilt. ` : '. ';
    description.textContent += asset.details.accuracy_notes + ' ' + asset.details.attribution.map(x => x.credit).join('; ');
  }
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
    const viewer = await createViewer(viewport, asset.file, status, signal, asset);
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
function syncModelUrl() {
  const id = new URL(location.href).searchParams.get('model');
  if (assetById.has(id)) openViewer(assetById.get(id), null, false);
  else if (dialog.open) closeViewer(false);
}
let gamePage = null, gameController = null, solarPage = null, solarController = null, routeRun = 0;
const galleryRoot = document.querySelector('#gallery-page');
const gameRoot = document.querySelector('#game-page');
const solarRoot = document.querySelector('#solar-page');
const footer = document.querySelector('.footer');
setupPwa(() => gamePage);
async function syncRoute() {
  const page = new URL(location.href).searchParams.get('page');
  const isGame = page === 'game', isSolar = page === 'solar';
  if (isGame && (gamePage || gameController) || isSolar && (solarPage || solarController)) return;
  if (!isGame && gamePage && !gamePage.beforeLeave()) {
    history.replaceState({}, '', '?page=game'); return;
  }
  const run = ++routeRun;
  if (!isGame) { gameController?.abort(); gameController = null; gamePage?.dispose(); gamePage = null; }
  if (!isSolar) { solarController?.abort(); solarController = null; solarPage?.dispose(); solarPage = null; }
  galleryRoot.hidden = isGame || isSolar; gameRoot.hidden = !isGame; solarRoot.hidden = !isSolar;
  footer.hidden = isGame; document.body.classList.toggle('game-page', isGame);
  document.querySelectorAll('[data-page]').forEach(link => link.setAttribute('aria-current', link.dataset.page === (isGame ? 'game' : isSolar ? 'solar' : 'gallery') ? 'page' : 'false'));
  if (isGame || isSolar) {
    if (dialog.open) closeViewer(false);
    const url = new URL(location.href); url.searchParams.delete('model'); history.replaceState({}, '', url);
    const controller = new AbortController();
    if (isGame) gameController = controller; else solarController = controller;
    try {
      let module;
      if (isGame) module = await import('./game/page.js');
      else module = await import('./solar/page.js');
      if (run !== routeRun || controller.signal.aborted) return;
      const result = isGame
        ? await module.mountGame(gameRoot, assets, controller.signal, () => navigate('gallery', true))
        : await module.mountSolar(solarRoot, assets.filter(a => a.family === 'solar-system'), controller.signal);
      if (controller.signal.aborted) result.dispose();
      else if (isGame) { gamePage = result; window.dispatchEvent(new CustomEvent('game-mounted')); }
      else { solarPage = result; window.dispatchEvent(new CustomEvent('solar-mounted')); }
    } catch (error) {
      if (controller.signal.aborted) return;
      (isGame ? gameRoot : solarRoot).textContent = 'This page could not start. Reconnect and return to Gallery to retry.';
      console.error(error);
    }
  } else syncModelUrl();
}
function navigate(page, alreadyConfirmed = false) {
  if (page !== 'game' && gamePage && !alreadyConfirmed && !gamePage.beforeLeave()) return;
  if (page !== 'game' && gamePage) { gameController?.abort(); gameController = null; gamePage.dispose(); gamePage = null; }
  const url = new URL(location.href); url.search = ''; url.hash = '';
  if (page === 'game' || page === 'solar') url.searchParams.set('page', page);
  history.pushState({}, '', url); window.scrollTo(0, 0); void syncRoute();
}
document.querySelectorAll('[data-page]').forEach(link => link.addEventListener('click', event => {
  if (event.metaKey || event.ctrlKey || event.shiftKey) return;
  event.preventDefault(); navigate(link.dataset.page);
  if (link.hash) document.querySelector(link.hash)?.scrollIntoView();
}));
document.querySelector('.brand').addEventListener('click', event => {
  if (event.metaKey || event.ctrlKey || event.shiftKey) return;
  event.preventDefault(); navigate('gallery');
});
window.addEventListener('popstate', () => void syncRoute());
void syncRoute();
