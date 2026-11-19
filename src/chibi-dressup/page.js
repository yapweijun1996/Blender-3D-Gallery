import { getLanguage, localize, mountMarkup, onLanguageChange } from "../i18n/index.js";
import manifestData from "../../models/chibi-dressup/manifest.json";
import {
  CLIPS, EXPRESSIONS, GESTURES, HANDS, fitsBody, loadConfig, modulesForBody, saveConfig, validateManifest,
} from "./config.js";
import { createExpressionController } from "./expression.js";
import { createProps } from "./props.js";
import { bindModule, createRig } from "./rig.js";
import { createView, disposeModels, getBounds, loadModels } from "./view.js";
import "./style.css";

const expressionUrls = Object.fromEntries(["happy", "surprised", "sad"].map(name => [
  name, new URL(`../../models/chibi-dressup/expressions/${name}.png`, import.meta.url).href,
]));
// Every model file by path under models/chibi-dressup: bodies, motion, gestures, modules and props.
const assetUrls = import.meta.glob("../../models/chibi-dressup/**/*.glb", {
  eager: true, query: "?url", import: "default",
});
const assetUrl = file => {
  const url = assetUrls[`../../models/chibi-dressup/${file}`];
  if (!url) throw new Error(`Unknown dress-up model file: ${file}`);
  return url;
};

export async function mountDressup(root, thumbnail, signal) {
  const manifest = validateManifest(manifestData);
  const config = loadConfig(manifest);
  mountMarkup(root, `<section class="dressup">
    <header class="dressup-heading">
      <h1 data-i18n="demo.chibi-dressup.title"></h1>
      <p data-i18n="demo.chibi-dressup.description"></p>
    </header>
    <div class="dressup-layout">
      <div class="dressup-preview">
        <div class="dressup-stage" data-state="loading" aria-busy="true">
          <img class="dressup-poster" alt="">
          <p class="dressup-loading" role="status" data-i18n="dressup.loading"></p>
        </div>
        <p class="dressup-hint" data-i18n="common.orbitHint"></p>
      </div>
      <form class="dressup-panel">
        <fieldset class="dressup-bodies" disabled hidden>
          <legend data-i18n="dressup.body"></legend>
          <div class="dressup-clips dressup-body-list"></div>
        </fieldset>
        <fieldset class="dressup-wardrobe" disabled>
          <legend data-i18n="dressup.wardrobe"></legend>
        </fieldset>
        <fieldset disabled>
          <legend data-i18n="common.animation"></legend>
          <div class="dressup-clips"></div>
          <button type="button" class="dressup-play" data-i18n="common.play"></button>
        </fieldset>
        <fieldset class="dressup-expressions" disabled>
          <legend data-i18n="dressup.expression"></legend>
          <div class="dressup-clips dressup-expression-list"></div>
        </fieldset>
        <fieldset class="dressup-hands" disabled>
          <legend data-i18n="dressup.hands"></legend>
        </fieldset>
        <p class="dressup-body-status" role="status" aria-live="polite"></p>
      </form>
    </div>
  </section>`);
  const stage = root.querySelector(".dressup-stage");
  const poster = stage.querySelector(".dressup-poster");
  poster.src = thumbnail;
  const form = root.querySelector(".dressup-panel");
  const wardrobe = form.querySelector(".dressup-wardrobe");
  const bodies = form.querySelector(".dressup-bodies");
  const bodyList = form.querySelector(".dressup-body-list");
  const bodyStatus = form.querySelector(".dressup-body-status");
  const clipList = form.querySelector(".dressup-clips:not(.dressup-body-list):not(.dressup-expression-list)");
  const playButton = form.querySelector(".dressup-play");
  const hands = form.querySelector(".dressup-hands");
  const expressions = form.querySelector(".dressup-expressions");
  const expressionList = form.querySelector(".dressup-expression-list");
  const motionPreference = matchMedia("(prefers-reduced-motion: reduce)");
  // Props load once; each body brings its own skeleton, motion, gestures, face and modules.
  const propScenes = new Set();
  let characterScenes = new Set();
  let view, rig, face, props, character, switching = false, playing = !motionPreference.matches;
  const moduleButtons = new Map();
  const clipButtons = new Map();
  const expressionButtons = new Map();
  const bodyButtons = new Map();

  function teardownCharacter() {
    view?.dispose();
    rig?.dispose();
    face?.dispose();
    props?.detach();
    view = rig = face = props = character = undefined;
    disposeModels(characterScenes);
    characterScenes = new Set();
  }
  const dispose = () => {
    delete stage.inspectDressup;
    teardownCharacter();
    disposeModels(propScenes);
    propScenes.clear();
  };

  const activate = (button, handler) => {
    button.type = "button";
    button.addEventListener("click", handler);
    return button;
  };
  const syncProps = () => props?.sync(rig.current, rig.time);

  function renderConfig() {
    if (!character) return;
    // A selected module can hide whole slots, for example a dress covers the bottoms.
    const covered = new Set(character.fitting
      .filter(({ id, slot }) => config.modules[slot] === id)
      .flatMap(({ excludesSlots = [] }) => excludesSlots));
    for (const { id, slot } of character.fitting) {
      const selected = config.modules[slot] === id;
      const button = moduleButtons.get(id);
      button.setAttribute("aria-pressed", String(selected));
      button.disabled = covered.has(slot);
      // A module that has not been downloaded yet has nothing to show.
      for (const mesh of character.modules.get(id) ?? []) mesh.visible = selected && !covered.has(slot);
    }
    for (const [name, button] of bodyButtons) button.setAttribute("aria-pressed", String(config.body === name));
    for (const [name, button] of expressionButtons)
      button.setAttribute("aria-pressed", String(config.expression === name));
    for (const [clip, button] of clipButtons)
      button.setAttribute("aria-pressed", String(config.animation === clip));
    localize(playButton, playing ? "common.pause" : "common.play");
    rig.update(0, config.hands);
    syncProps();
    view.setPlaying(playing);
    view.invalidate();
  }

  function applyConfig() {
    renderConfig();
    saveConfig(config, manifest);
  }

  function translateModules() {
    for (const { id, label } of manifest.modules) {
      const button = moduleButtons.get(id);
      if (button) button.textContent = label[getLanguage()];
    }
    for (const { id, label } of manifest.bodies) bodyButtons.get(id).textContent = label[getLanguage()];
  }
  onLanguageChange(translateModules, signal);

  function buildWardrobe() {
    wardrobe.querySelectorAll(".dressup-slot").forEach(group => group.remove());
    moduleButtons.clear();
    for (const slot of manifest.slots) {
      const choices = character.fitting.filter(module => module.slot === slot);
      if (!choices.length) continue;
      const group = document.createElement("div");
      group.className = "dressup-slot";
      group.setAttribute("role", "group");
      const key = `dressup.slot.${slot}`;
      localize(group, key, undefined, "aria-label");
      const label = localize(document.createElement("span"), key);
      label.setAttribute("aria-hidden", "true");
      group.append(label);
      for (const module of choices) {
        const button = activate(document.createElement("button"), () => void chooseModule(slot, module));
        button.dataset.module = module.id;
        moduleButtons.set(module.id, button);
        group.append(button);
      }
      wardrobe.append(group);
    }
    translateModules();
  }

  // Modules download the first time they are worn; the body and the worn modules load with the character.
  async function ensureModule(module) {
    const current = character;
    if (current.modules.has(module.id)) return;
    let pending = current.pending.get(module.id);
    if (!pending) {
      pending = (async () => {
        const [gltf] = await loadModels([assetUrl(module.file)], signal, current.scenes);
        signal.throwIfAborted();
        if (character === current) current.modules.set(module.id, bindModule(current.body.scene, gltf.scene, current.skeleton));
      })().finally(() => current.pending.delete(module.id));
      current.pending.set(module.id, pending);
    }
    await pending;
  }

  async function chooseModule(slot, module) {
    const previous = config.modules[slot];
    config.modules[slot] = previous === module.id ? null : module.id;
    if (config.modules[slot] === module.id && !character.modules.has(module.id)) {
      const button = moduleButtons.get(module.id);
      button.setAttribute("aria-busy", "true");
      const current = character;
      try {
        await ensureModule(module);
      } catch (error) {
        if (signal.aborted) return;
        console.error("Dress-up module failed to load", error);
        if (character === current && config.modules[slot] === module.id) config.modules[slot] = previous;
        if (character === current) renderConfig();
        return;
      } finally {
        button.removeAttribute("aria-busy");
      }
      // The visitor changed body or slot while the file downloaded.
      if (character !== current || config.modules[slot] !== module.id) return;
    }
    applyConfig();
  }

  async function buildCharacter(bodyId) {
    const spec = manifest.bodies.find(item => item.id === bodyId);
    const fitting = manifest.modules.filter(module => fitsBody(module, bodyId, manifest));
    const incoming = new Set();
    const worn = fitting.filter(({ id, slot }) => config.modules[slot] === id);
    let loaded;
    try {
      loaded = await loadModels([
        assetUrl(spec.body), assetUrl(spec.gestures), ...spec.motion.map(assetUrl),
        ...worn.map(({ file }) => assetUrl(file)),
      ], signal, incoming);
      signal.throwIfAborted();
    } catch (error) {
      disposeModels(incoming);
      throw error;
    }
    teardownCharacter();
    characterScenes = incoming;
    const [body, gestures, ...rest] = loaded;
    const motion = rest.slice(0, spec.motion.length);
    const models = rest.slice(spec.motion.length);
    let skeleton;
    body.scene.traverse(node => {
      if (!node.isSkinnedMesh) return;
      if (skeleton && node.skeleton !== skeleton) throw new Error("Body has multiple skeletons");
      skeleton = node.skeleton;
      node.frustumCulled = false;
    });
    if (!skeleton) throw new Error("Body has no skeleton");
    const bounds = getBounds(body.scene);
    const modules = new Map(worn.map((module, index) => [
      module.id, bindModule(body.scene, models[index].scene, skeleton),
    ]));
    try { face = createExpressionController(body.scene, expressionUrls); } catch { face = null; }
    expressions.hidden = !face;
    rig = createRig(body.scene, skeleton, motion, gestures.animations, spec.layers);
    // Props: the chair stays on the floor at the origin; hand props ride in the right hand.
    const hand = skeleton.bones.find(bone => bone.name === "mixamorigRightHand");
    if (!hand) throw new Error("Body has no right hand");
    props = createProps({
      root: body.scene, hand, chair: shared.chair.scene, cup: shared.cup.scene, box: shared.box.scene,
      bag: shared.bag.scene, shelf: shared.shelf.scene, fitted: spec.sockets,
    });
    rig.select(config.animation);
    character = { body, skeleton, modules, fitting, scenes: incoming, pending: new Map() };
    buildWardrobe();
    face?.set(config.expression).catch(() => {});
    view = createView(stage, body.scene, bounds, delta => {
      rig.update(delta, config.hands);
      syncProps();
    });
    renderConfig();
  }

  async function switchBody(bodyId) {
    if (switching || bodyId === config.body) return;
    switching = true;
    const previous = { body: config.body, modules: { ...config.modules } };
    form.querySelectorAll("fieldset").forEach(fieldset => { fieldset.disabled = true; });
    stage.dataset.state = "loading";
    stage.setAttribute("aria-busy", "true");
    localize(bodyStatus, "dressup.bodyLoading");
    try {
      config.modules = modulesForBody(config.modules, bodyId, manifest);
      config.body = bodyId;
      await buildCharacter(bodyId);
      saveConfig(config, manifest);
      bodyStatus.textContent = "";
    } catch (error) {
      if (signal.aborted) return;
      console.error("Dress-up body switch failed", error);
      // Keep the previous body usable when the new one cannot load.
      config.body = previous.body;
      config.modules = previous.modules;
      await buildCharacter(previous.body);
      localize(bodyStatus, "dressup.bodyFailed");
    } finally {
      switching = false;
      stage.dataset.state = "ready";
      stage.setAttribute("aria-busy", "false");
      form.querySelectorAll("fieldset").forEach(fieldset => { fieldset.disabled = false; });
      expressions.hidden = !face;
      if (view) renderConfig();
    }
  }

  let shared;
  try {
    const [chair, cup, box, bag, shelf] = await loadModels([
      "props/chair.glb", "props/cup.glb", "props/box.glb", "props/bag.glb", "props/shelf_item.glb",
    ].map(assetUrl), signal, propScenes);
    shared = { chair, cup, box, bag, shelf };
    signal.throwIfAborted();

    for (const spec of manifest.bodies) {
      const button = activate(document.createElement("button"), () => void switchBody(spec.id));
      button.dataset.body = spec.id;
      bodyButtons.set(spec.id, button);
      bodyList.append(button);
    }
    bodies.hidden = manifest.bodies.length < 2;

    for (const clip of CLIPS) {
      const button = activate(localize(document.createElement("button"), `clip.${clip}`), () => {
        config.animation = clip;
        rig.select(clip);
        applyConfig();
      });
      button.dataset.clip = clip;
      clipButtons.set(clip, button);
      clipList.append(button);
    }
    playButton.addEventListener("click", () => {
      playing = !playing;
      renderConfig();
    });
    motionPreference.addEventListener("change", event => {
      if (event.matches) {
        playing = false;
        renderConfig();
      }
    }, { signal });

    for (const name of EXPRESSIONS) {
      const button = activate(localize(document.createElement("button"), `dressup.expression.${name}`), () => {
        config.expression = name;
        applyConfig();
        face?.set(name).catch(() => {});
      });
      button.dataset.expression = name;
      expressionButtons.set(name, button);
      expressionList.append(button);
    }

    for (const side of HANDS) {
      const label = document.createElement("label");
      const select = document.createElement("select");
      select.dataset.hand = side;
      for (const gesture of ["", ...GESTURES]) {
        const option = localize(document.createElement("option"),
          gesture ? `dressup.gesture.${gesture}` : "dressup.gesture.none");
        option.value = gesture;
        select.append(option);
      }
      select.value = config.hands[side] ?? "";
      select.addEventListener("change", () => {
        config.hands[side] = select.value || null;
        applyConfig();
      });
      label.append(localize(document.createElement("span"), `dressup.hand.${side}`), select);
      hands.append(label);
    }

    await buildCharacter(config.body);
    // The browser smoke test samples the rendered rig without changing playback.
    stage.inspectDressup = () => ({
      ...(rig?.inspect() ?? { joints: [] }),
      body: config.body,
      switching,
      triangles: view?.triangles ?? 0,
      expression: face?.current ?? null,
      modules: Object.fromEntries([...(character?.modules ?? [])].map(([id, meshes]) => [id, meshes.every(mesh => mesh.visible)])),
    });
    stage.querySelector(".dressup-loading")?.remove();
    poster.remove();
    stage.dataset.state = "ready";
    stage.setAttribute("role", "img");
    localize(stage, "motion.stage", undefined, "aria-label");
    stage.setAttribute("aria-busy", "false");
    for (const fieldset of form.querySelectorAll("fieldset")) fieldset.disabled = false;
    expressions.hidden = !face;
    return { dispose };
  } catch (error) {
    dispose();
    throw error;
  }
}
