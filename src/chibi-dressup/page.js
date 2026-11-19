import { getLanguage, localize, mountMarkup, onLanguageChange } from "../i18n/index.js";
import bodyUrl from "../../models/chibi-dressup/base_body.glb?url";
import motionUrl from "../../models/chibi-dressup/motion-clips.glb?url";
import poseUrl from "../../models/chibi-dressup/hand_gestures.glb?url";
import actionsUrl from "../../models/chibi-dressup/actions.glb?url";
import chairUrl from "../../models/chibi-dressup/props/chair.glb?url";
import cupUrl from "../../models/chibi-dressup/props/cup.glb?url";
import manifestData from "../../models/chibi-dressup/manifest.json";
import { CLIPS, EXPRESSIONS, GESTURES, HANDS, loadConfig, saveConfig, validateManifest } from "./config.js";
import { createExpressionController } from "./expression.js";
import { bindModule, createRig } from "./rig.js";
import { createView, disposeModels, getBounds, loadModels } from "./view.js";
import "./style.css";

const expressionUrls = Object.fromEntries(["happy", "surprised", "sad"].map(name => [
  name, new URL(`../../models/chibi-dressup/expressions/${name}.png`, import.meta.url).href,
]));
const moduleUrls = import.meta.glob("../../models/chibi-dressup/modules/*.glb", {
  eager: true, query: "?url", import: "default",
});

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
      </form>
    </div>
  </section>`);
  const stage = root.querySelector(".dressup-stage");
  const poster = stage.querySelector(".dressup-poster");
  poster.src = thumbnail;
  const form = root.querySelector(".dressup-panel");
  const wardrobe = form.querySelector(".dressup-wardrobe");
  const clipList = form.querySelector(".dressup-clips");
  const playButton = form.querySelector(".dressup-play");
  const hands = form.querySelector(".dressup-hands");
  const expressionList = form.querySelector(".dressup-expression-list");
  const motionPreference = matchMedia("(prefers-reduced-motion: reduce)");
  const scenes = new Set();
  let view, rig, face;
  const dispose = () => {
    delete stage.inspectDressup;
    view?.dispose();
    rig?.dispose();
    face?.dispose();
    disposeModels(scenes);
    scenes.clear();
  };

  try {
    const [body, motion, gestures, actions, chair, cup, ...models] = await loadModels([
      bodyUrl, motionUrl, poseUrl, actionsUrl, chairUrl, cupUrl,
      ...manifest.modules.map(({ file }) => {
        const url = moduleUrls[`../../models/chibi-dressup/${file}`];
        if (!url) throw new Error(`Unknown dress-up module file: ${file}`);
        return url;
      }),
    ], signal, scenes);
    signal.throwIfAborted();

    let skeleton;
    body.scene.traverse(node => {
      if (!node.isSkinnedMesh) return;
      if (skeleton && node.skeleton !== skeleton) throw new Error("Body has multiple skeletons");
      skeleton = node.skeleton;
      node.frustumCulled = false;
    });
    if (!skeleton) throw new Error("Body has no skeleton");
    const bounds = getBounds(body.scene);
    const modules = new Map(manifest.modules.map((module, index) => [
      module.id, bindModule(body.scene, models[index].scene, skeleton),
    ]));
    face = createExpressionController(body.scene, expressionUrls);
    rig = createRig(body.scene, skeleton, motion, gestures.animations, actions);
    // Props: the chair stays on the floor at the origin, the cup rides in the right hand.
    chair.scene.visible = false;
    body.scene.add(chair.scene);
    const hand = skeleton.bones.find(bone => bone.name === "mixamorigRightHand");
    if (!hand) throw new Error("Body has no right hand");
    cup.scene.visible = false;
    cup.scene.position.set(0.02593084, 0.02887651, 0.03611905);
    cup.scene.quaternion.set(0.27544212, 0.76551259, -0.46392176, 0.35056925);
    hand.add(cup.scene);
    const syncProps = () => {
      chair.scene.visible = ["sit_down", "sit_idle", "stand_up"].includes(rig.current);
      cup.scene.visible = rig.current === "hold_item";
    };
    rig.select(config.animation);

    const moduleButtons = new Map();
    const clipButtons = new Map();
    const expressionButtons = new Map();
    let playing = !motionPreference.matches;

    function renderConfig() {
      // A selected module can hide whole slots, for example a dress covers the bottoms.
      const covered = new Set(manifest.modules
        .filter(({ id, slot }) => config.modules[slot] === id)
        .flatMap(({ excludesSlots = [] }) => excludesSlots));
      for (const { id, slot } of manifest.modules) {
        const selected = config.modules[slot] === id;
        const button = moduleButtons.get(id);
        button.setAttribute("aria-pressed", String(selected));
        button.disabled = covered.has(slot);
        for (const mesh of modules.get(id)) mesh.visible = selected && !covered.has(slot);
      }
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

    function activate(button, handler) {
      button.type = "button";
      button.addEventListener("click", handler);
      return button;
    }

    for (const slot of manifest.slots) {
      const choices = manifest.modules.filter(module => module.slot === slot);
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
        const button = activate(document.createElement("button"), () => {
          config.modules[slot] = config.modules[slot] === module.id ? null : module.id;
          applyConfig();
        });
        button.dataset.module = module.id;
        moduleButtons.set(module.id, button);
        group.append(button);
      }
      wardrobe.append(group);
    }

    function translateModules() {
      for (const { id, label } of manifest.modules)
        moduleButtons.get(id).textContent = label[getLanguage()];
    }
    onLanguageChange(translateModules, signal);
    translateModules();

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
        face.set(name).catch(() => {});
      });
      button.dataset.expression = name;
      expressionButtons.set(name, button);
      expressionList.append(button);
    }
    face.set(config.expression).catch(() => {});

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

    view = createView(stage, body.scene, bounds, delta => {
      rig.update(delta, config.hands);
      syncProps();
    });
    renderConfig();
    // The browser smoke test samples the rendered rig without changing playback.
    stage.inspectDressup = () => ({
      ...rig.inspect(),
      triangles: view.triangles,
      expression: face.current,
      modules: Object.fromEntries([...modules].map(([id, meshes]) => [id, meshes.every(mesh => mesh.visible)])),
    });
    const loading = stage.querySelector(".dressup-loading");
    loading.remove();
    poster.remove();
    stage.dataset.state = "ready";
    stage.setAttribute("role", "img");
    localize(stage, "motion.stage", undefined, "aria-label");
    stage.setAttribute("aria-busy", "false");
    for (const fieldset of form.querySelectorAll("fieldset")) fieldset.disabled = false;
    return { dispose };
  } catch (error) {
    dispose();
    throw error;
  }
}
