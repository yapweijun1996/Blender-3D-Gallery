import "./style.css";
import { makeRack, legalPlacement, TABLE, groupOf } from "./table.js";
import { createShot, stepPhysics } from "./physics.js";
import { adjudicate, RULES_VERSION } from "./rules.js";
import { openGameStore } from "./storage.js";
import { createGameScene } from "./scene.js";

export async function mountGame(root, assets, signal, onLeave) {
  root.innerHTML = `<section class="game-shell" aria-labelledby="game-title">
    <div class="game-heading"><div><p class="eyebrow">PLAY THE COLLECTION</p><h1 id="game-title">Eight-ball<span>.</span></h1></div><div class="game-heading-actions"><span class="game-mode">LOCAL TWO-PLAYER</span><button type="button" data-action="rules">Rules & controls</button></div></div>
    <div class="players"><div id="player-0" class="player-card"><span class="player-index">01</span><div><strong>Player 1</strong><span class="player-group">Open table</span></div><div class="remaining"><span class="remaining-full" aria-hidden="true"></span><span class="remaining-compact" aria-hidden="true"></span><span class="game-sr-only remaining-accessible"></span></div></div><div id="player-1" class="player-card"><span class="player-index">02</span><div><strong>Player 2</strong><span class="player-group">Open table</span></div><div class="remaining"><span class="remaining-full" aria-hidden="true"></span><span class="remaining-compact" aria-hidden="true"></span><span class="game-sr-only remaining-accessible"></span></div></div></div>
    <div class="game-layout"><div class="game-board"><div id="game-viewport" tabindex="0" aria-label="Pool table. Arrow keys adjust aim or cue placement."><div id="game-loading" role="status">Preparing your table…</div></div><div class="game-table-caption"><span>CASUAL EIGHT-BALL</span><button type="button" data-action="inspect" disabled>Inspect table</button><button type="button" data-action="options">App options</button></div></div>
    <aside class="game-controls" aria-label="Game controls"><div id="game-turn" class="game-turn">Your table is waiting.</div><p id="game-status" role="status" aria-live="polite">Load the table, then start a local match.</p>
      <div id="game-start" class="game-start"><button class="primary" data-action="new" disabled>New two-player match</button><button data-action="resume" disabled>Resume saved match</button><p>Pass the device between turns. No account needed.</p></div>
      <div id="game-load-error" role="alert" hidden><p>Check your connection and browser 3D support, then try again.</p><button data-action="retry-load" class="primary">Retry loading</button><button data-action="back-to-gallery">Back to Gallery</button></div>
      <div id="game-shot-controls" hidden><div class="aim-control"><label for="aim-angle">Aim <output id="angle-output">0°</output></label><input id="aim-angle" type="range" min="-180" max="180" step="0.25" value="0"><div class="aim-fine"><button data-action="aim-left" aria-label="Aim left one degree">−1°</button><button data-action="aim-right" aria-label="Aim right one degree">+1°</button></div></div>
        <div class="power-control"><label for="shot-power">Power <output id="power-output">45%</output></label><input id="shot-power" type="range" min="5" max="100" value="45"></div><button data-action="shoot" class="primary">Shoot</button><p class="control-note">Drag to aim; press Shoot to strike.</p></div>
      <div id="game-placement" hidden><strong>Ball in hand</strong><p id="placement-hint">Tap or drag on the table to place the cue ball.</p><label for="place-x">Along the table</label><input id="place-x" type="range" min="-1.076" max="1.076" step="0.005" value="-0.7"><label for="place-z">Across the table</label><input id="place-z" type="range" min="-0.492" max="0.492" step="0.005" value="0"><button data-action="place" class="primary">Confirm cue position</button></div>
      <div id="game-finish" hidden><button data-action="new" class="primary">Play again</button></div><div id="game-recovery" hidden><button data-action="restore" class="primary">Restore last turn</button></div>
      <button data-action="pause" id="game-pause" hidden>Pause / menu</button><p id="save-status" class="save-status" role="status">Checking local save…</p>
    </aside></div>
    <dialog id="game-options" aria-labelledby="game-options-title"><h2 id="game-options-title">Your app.</h2><label for="graphics-quality">Graphics quality</label><select id="graphics-quality" aria-describedby="graphics-quality-note" disabled><option value="standard">Standard</option><option value="performance">Performance</option></select><p id="graphics-quality-note">Performance lowers rendering resolution until you leave Game.</p><div class="offline-box"><span id="game-offline-status">Online play available</span><button data-action="offline">Make available offline</button><button data-action="install">Install app / help</button></div><button data-action="fullscreen">Fullscreen</button><button data-action="close-options" class="primary">Back to the table</button></dialog>
    <dialog id="game-menu" aria-labelledby="game-menu-title"><h2 id="game-menu-title">Take a break.</h2><p id="menu-save-message" role="status">Your last complete turn is saved when local storage is available.</p><button data-action="continue" class="primary">Continue game</button><button data-action="restart">Restart match</button><button data-action="leave">Save & return to Gallery</button><button data-action="discard" hidden>Leave without saving</button></dialog>
    <dialog id="game-rules" aria-labelledby="game-rules-title"><h2 id="game-rules-title">Casual Eight-Ball</h2><p>Two people, one device. Player 1 breaks. Drag to aim, set power, then press Shoot. Arrow keys adjust aim (Shift for fine aim); Enter confirms cue placement; Space shoots when the table is focused. Labeled sliders and buttons also work with a keyboard.</p><ul><li>Groups stay open on the break. The first legal post-break pot assigns solids or stripes. Pots are ordered by when they enter a pocket; simultaneous pots use ball number to break the tie.</li><li>First contact must be your group. When your group is cleared, hit the eight first. If every group ball has gone while the table is still open, either player may play the eight.</li><li>A scratch, wrong first contact or no contact gives your opponent ball in hand.</li><li>Clear your group before the shot that pockets the eight. An early eight, or an eight with a foul, loses.</li><li>Eight on the break is re-spotted. Eight + scratch on the break is a foul, not an instant loss.</li><li>No called pockets, four-rail break requirement, spin or jump shots. This is a casual ruleset, not competition rules.</li></ul><p>In inspection mode, drag or use the table-focused arrow keys to orbit, and use + or − to zoom. Use the return button to leave inspection. The guide estimates initial contact, not a guaranteed pot. Backgrounding pauses play. After a killed or interrupted shot, Resume restores its pre-shot checkpoint.</p><button data-action="close-rules" class="primary">Back to the table</button></dialog>
    <dialog id="game-confirm" aria-labelledby="game-confirm-title"><h2 id="game-confirm-title">Start a new match?</h2><p>This replaces the current match. Your gallery assets are unaffected.</p><div><button data-action="cancel-new">Keep current match</button><button data-action="confirm-new" class="primary">Start new match</button></div></dialog>
  </section>`;
  const $ = (s) => root.querySelector(s),
    all = (s) => [...root.querySelectorAll(s)];
  const loading = $("#game-loading"),
    status = $("#game-status"),
    saveStatus = $("#save-status"),
    viewport = $("#game-viewport");
  let state = null,
    stable = null,
    saved = null,
    store = null,
    view = null,
    angle = 0,
    power = 0.45,
    candidate = { x: -0.7, z: 0 },
    pausedPhase = null,
    inspection = false,
    shot = null,
    before = null,
    busy = false,
    pauseRequested = false,
    loadFailed = false,
    ready = false,
    disposed = false;
  let frame = 0,
    lastTime = performance.now(),
    accumulator = 0,
    manualUntil = 0,
    ownership = true,
    saveFailed = false,
    contextLost = false;
  const uuid = () => crypto.randomUUID();
  const stableCopy = (s) => structuredClone(s);
  const conflictMessage = "Your local turn conflicts with the saved match. Leave without saving or reload to restore the saved match.";
  function setSaveStatus(message, warning = false) {
    if (disposed) return;
    saveStatus.textContent = message;
    saveStatus.classList.toggle("is-warning", warning);
  }
  async function persist(s, pending = null) {
    if (!ownership) {
      setSaveStatus("This tab does not own the match. Your current turn was not saved.", true);
      saveFailed = true;
      return false;
    }
    if (!store) {
      setSaveStatus("Autosave unavailable. Keep this tab open.", true);
      saveFailed = true;
      return false;
    }
    try {
      await store.save(s, pending);
      setSaveStatus(
        pending ? "Previous turn saved. Shot in progress." : "Turn saved on this device.",
      );
      saveFailed = false;
      return true;
    } catch (e) {
      setSaveStatus(e.message, true);
      saveFailed = true;
      if (e.message.includes("another tab")) ownership = false;
      return false;
    }
  }
  function ui() {
    if (disposed) return;
    const phase = state?.phase;
    const returnAction = phase === "placing" || (phase === "paused" && pausedPhase === "placing")
      ? "Return to placement"
      : phase === "finished"
        ? "Return to table"
        : "Return to aim";
    root.querySelector(".game-shell").classList.toggle("is-playing", !!state);
    root.querySelector(".game-shell").dataset.phase = phase || "setup";
    $("#game-start").hidden = !!state || loadFailed;
    $("#game-load-error").hidden = !loadFailed;
    $("#game-shot-controls").hidden = phase !== "aiming" || contextLost;
    $("#game-placement").hidden = phase !== "placing" || contextLost;
    $("#game-finish").hidden = phase !== "finished" || contextLost;
    $("#game-recovery").hidden = phase !== "recovery" && !contextLost;
    $("#game-pause").hidden = !state || phase === "finished";
    $("#game-turn").textContent = !state
      ? "Your table is waiting."
      : phase === "finished"
        ? `Player ${state.winner + 1} wins!`
        : phase === "moving"
          ? "Watch your shot."
          : phase === "paused"
            ? "Game paused."
            : `Player ${state.player + 1} · ${state.groups[state.player] || "Open table"}`;
    status.textContent = contextLost
      ? "3D view interrupted. Reload the table to continue."
      : loadFailed
        ? "The 3D table could not load."
        : inspection && ["placing", "aiming"].includes(phase)
          ? `Inspect mode. Select ${returnAction} to continue.`
        : state?.message ||
          "Clear your group, then pocket the eight. Two players share this device.";
    viewport.setAttribute("aria-label", inspection
      ? `Inspection view. Use arrow keys to orbit and plus or minus to zoom. Select ${returnAction} to continue.`
      : "Pool table. Arrow keys adjust aim or cue placement.");
    $(".control-note").textContent = inspection
      ? "Inspect mode. Return to aim before shooting."
      : "Drag to aim; press Shoot to strike.";
    for (let i = 0; i < 2; i++) {
      const c = $(`#player-${i}`);
      c.classList.toggle(
        "active",
        !!state && state.player === i && phase !== "finished",
      );
      c.querySelector(".player-group").textContent =
        state?.groups[i] || "Open table";
      const remain = state?.groups[i]
        ? state.balls.filter(
            (b) => !b.pocketed && groupOf(b.id) === state.groups[i],
          )
        : [];
      c.querySelector(".remaining-full").textContent = remain.length
        ? remain.map((b) => String(b.id).padStart(2, "0")).join(" · ")
        : state?.groups[i]
          ? "8 BALL"
          : "";
      c.querySelector(".remaining-compact").textContent = !state?.groups[i]
        ? ""
        : remain.length
          ? `${remain.length} left`
          : state.balls[8].pocketed
            ? "Cleared"
            : "8 ball next";
      c.querySelector(".remaining-accessible").textContent = !state?.groups[i]
        ? ""
        : remain.length
          ? `${state.groups[i]} remaining: balls ${remain.map((b) => b.id).join(", ")}.`
          : state.balls[8].pocketed
            ? `${state.groups[i]} cleared.`
            : `${state.groups[i]} cleared; 8 ball next.`;
    }
    const disabled =
      busy || !ownership || inspection || contextLost || phase !== "aiming";
    all("#game-shot-controls button, #game-shot-controls input").forEach(
      (b) => (b.disabled = disabled),
    );
    $('[data-action="inspect"]').disabled =
      !ready ||
      !state ||
      busy ||
      contextLost ||
      ["moving", "adjudicating", "recovery"].includes(phase);
    $('[data-action="inspect"]').textContent = inspection
      ? returnAction
      : "Inspect table";
    $('[data-action="place"]').disabled =
      busy ||
      !ownership ||
      inspection ||
      contextLost ||
      !state ||
      !legalPlacement(state.balls, candidate.x, candidate.z, state.break);
    all('#game-placement input').forEach((input) => {
      input.disabled = busy || !ownership || inspection || contextLost || phase !== "placing";
    });
    if (phase === "placing") {
      const valid = legalPlacement(state.balls, candidate.x, candidate.z, state.break);
      $("#placement-hint").textContent = inspection
        ? "Inspect mode. Return to placement to position the cue ball."
        : !valid
          ? "Position is outside the legal area or overlaps a ball."
          : state.break
            ? "Place behind the head string, then confirm."
            : "Valid position. Confirm when ready.";
    }
    $("#angle-output").value = `${Math.round((angle * 180) / Math.PI)}°`;
    $("#aim-angle").value = (angle * 180) / Math.PI;
    $("#power-output").value = `${Math.round(power * 100)}%`;
    $("#shot-power").value = power * 100;
    $("#place-x").value = candidate.x;
    $("#place-z").value = candidate.z;
    $('[data-action="restore"]').textContent = contextLost
      ? stable
        ? "Save & reload 3D table"
        : "Reload 3D table"
      : "Restore last turn";
    all('[data-action="new"]').forEach(
      (b) => (b.disabled = !ready || !ownership || contextLost),
    );
    $('[data-action="resume"]').disabled =
      !ready || !saved || !ownership || contextLost;
    $('[data-action="continue"]').disabled = !ownership || busy;
    $('[data-action="restart"]').disabled = !ownership || busy;
    $('[data-action="confirm-new"]').disabled = !ownership || busy;
    $("#graphics-quality").disabled = !ready || contextLost || loadFailed;
  }
  const previewState = { phase: "preview", balls: makeRack(42) };
  function draw() {
    if (!contextLost) view?.update(state || previewState, angle, power, candidate);
  }
  async function startNew() {
    if (!ready || !ownership) return;
    busy = true;
    state = {
      schema: 1,
      rulesVersion: RULES_VERSION,
      tableVersion: TABLE.version,
      matchId: uuid(),
      revision: 0,
      player: 0,
      groups: [null, null],
      break: true,
      phase: "placing",
      ballInHand: true,
      winner: null,
      balls: makeRack(crypto.getRandomValues(new Uint32Array(1))[0]),
      message: "Player 1 breaks. Place the cue ball behind the head string.",
    };
    state.balls[0].pocketed = true;
    candidate = { x: -0.7, z: 0 };
    angle = 0;
    power = 0.45;
    inspection = false;
    view.setInspection(false);
    shot = null;
    pausedPhase = null;
    stable = stableCopy(state);
    ui();
    await persist(stable);
    if (disposed) return;
    finishBusy();
    ui();
    draw();
    viewport.focus({ preventScroll: true });
  }
  async function shoot() {
    if (
      !state ||
      state.phase !== "aiming" ||
      busy ||
      inspection ||
      contextLost ||
      !ownership
    )
      return;
    busy = true;
    ui();
    if (store) {
      try {
        const renewed = await store.renew();
        if (!canContinueShot()) return;
        if (!renewed) {
          ownership = false;
          state.message =
            "Another tab owns this match. Pause and return when it is closed.";
          finishBusy();
          ui();
          return;
        }
      } catch {
        saveFailed = true;
      }
    }
    if (!canContinueShot()) return;
    before = stableCopy(state);
    const id = uuid();
    await persist(before, { id });
    if (!canContinueShot()) return;
    if (!ownership) {
      finishBusy();
      ui();
      return;
    }
    try {
      shot = createShot(
        state.balls,
        { x: Math.cos(angle), z: Math.sin(angle) },
        power,
      );
      shot.id = id;
      state.phase = "moving";
      state.message = "Balls are moving…";
      accumulator = 0;
      lastTime = performance.now();
    } catch (e) {
      state.phase = "recovery";
      state.message = e.message;
    }
    finishBusy();
    ui();
    draw();
  }
  function canContinueShot() {
    if (!disposed && !contextLost && state?.phase === "aiming") return true;
    busy = false;
    pauseRequested = false;
    ui();
    return false;
  }
  async function completeShot() {
    if (busy) return;
    busy = true;
    state.phase = "adjudicating";
    ui();
    const next = adjudicate(before, state.balls, shot);
    shot = null;
    if (next.phase === "recovery") {
      state = next;
      finishBusy();
      ui();
      draw();
      return;
    }
    await persist(next);
    if (disposed) return;
    state = next;
    stable = stableCopy(next);
    if (contextLost) {
      state.phase = "recovery";
      state.message =
        "3D view interrupted. Save and reload to restore the last complete turn.";
    }
    candidate = { x: -0.7, z: 0 };
    finishBusy();
    ui();
    draw();
  }
  function simulate(dt) {
    if (state?.phase !== "moving" || !shot || busy) return;
    stepPhysics(state.balls, shot, dt);
    if (shot.invalid || shot.done) void completeShot();
  }
  let deferredUpdateMenu = false;
  function pause() {
    if (!state || contextLost || ["finished", "paused"].includes(state.phase)) return;
    if (busy) {
      pauseRequested = true;
      return;
    }
    pauseRequested = false;
    clearPointers();
    pausedPhase = state.phase;
    state.phase = "paused";
    state.message = "Take your time. Continue when ready.";
    ui();
    if (document.querySelector('#pwa-update-dialog')?.open) {
      deferredUpdateMenu = true;
      return;
    }
    $("#game-menu").showModal();
    $('#game-menu [data-action="continue"]').focus();
  }
  document.querySelector('#pwa-update-dialog')?.addEventListener('close', () => {
    if (!deferredUpdateMenu || disposed || contextLost || state?.phase !== 'paused') return;
    deferredUpdateMenu = false;
    if (!$('#game-menu').open) $('#game-menu').showModal();
    $('#game-menu [data-action="continue"]').focus();
  }, {signal});
  function finishBusy() {
    busy = false;
    if (pauseRequested) {
      pauseRequested = false;
      if (!disposed && !contextLost) pause();
    }
  }
  function resume() {
    if (state?.phase !== "paused" || !ownership || busy) return;
    state.phase = pausedPhase || "aiming";
    pausedPhase = null;
    state.message =
      state.phase === "moving" ? "Resuming the shot…" : "Ready when you are.";
    accumulator = 0;
    lastTime = performance.now();
    $("#game-menu").close();
    ui();
    draw();
  }
  const selectPoint = (e) => {
    if (
      !state ||
      inspection ||
      busy ||
      !["aiming", "placing"].includes(state.phase)
    )
      return;
    const p = view.point(e.clientX, e.clientY);
    if (!p) return;
    if (state.phase === "placing") candidate = { x: p.x, z: p.z };
    else angle = Math.atan2(p.z - state.balls[0].z, p.x - state.balls[0].x);
    ui();
    draw();
  };
  let pointer = null;
  const pointers = new Set();
  function clearPointers() {
    pointer = null;
    pointers.clear();
  }
  viewport.addEventListener(
    "pointerdown",
    (e) => {
      if (
        e.target.tagName !== "CANVAS" || inspection || busy || contextLost ||
        !state || !["aiming", "placing"].includes(state.phase)
      ) return;
      pointers.add(e.pointerId);
      e.target.setPointerCapture(e.pointerId);
      if (pointer !== null) return;
      viewport.focus({ preventScroll: true });
      pointer = e.pointerId;
      selectPoint(e);
    },
    { signal },
  );
  viewport.addEventListener(
    "pointermove",
    (e) => {
      if (pointer === e.pointerId) selectPoint(e);
    },
    { signal },
  );
  for (const event of ["pointerup", "pointercancel", "lostpointercapture"])
    viewport.addEventListener(
      event,
      (e) => {
        pointers.delete(e.pointerId);
        if (pointer === e.pointerId)
          pointer = pointers.keys().next().value ?? null;
      },
      { signal },
    );
  $("#aim-angle").addEventListener(
    "input",
    (e) => {
      angle = (Number(e.target.value) * Math.PI) / 180;
      ui();
      draw();
    },
    { signal },
  );
  $("#shot-power").addEventListener(
    "input",
    (e) => {
      power = Number(e.target.value) / 100;
      ui();
      draw();
    },
    { signal },
  );
  $("#graphics-quality").addEventListener(
    "change",
    (e) => view?.setQuality(e.target.value),
    { signal },
  );
  for (const axis of ["x", "z"])
    $(`#place-${axis}`).addEventListener(
      "input",
      (e) => {
        candidate[axis] = Number(e.target.value);
        ui();
        draw();
      },
      { signal },
    );
  root.addEventListener(
    "click",
    async (e) => {
      const b = e.target.closest("button[data-action]");
      if (!b || b.disabled) return;
      switch (b.dataset.action) {
        case "new":
          if (saved || state) {
            $("#game-confirm").showModal();
            $('[data-action="cancel-new"]').focus();
          } else await startNew();
          break;
        case "confirm-new":
          $("#game-confirm").close();
          $("#game-menu").close();
          await startNew();
          break;
        case "cancel-new":
          $("#game-confirm").close();
          break;
        case "resume":
          if (saved?.checkpoint) {
            state = stableCopy(saved.checkpoint);
            stable = stableCopy(state);
            state.message = saved.pending
              ? "Interrupted shot was not recorded. Your previous turn is restored."
              : "Saved match restored.";
            candidate = { x: -0.7, z: 0 };
            await persist(stable);
            ui();
            draw();
          }
          break;
        case "shoot":
          await shoot();
          break;
        case "place":
          if (
            !inspection &&
            !contextLost &&
            !busy &&
            ownership &&
            state?.phase === "placing" &&
            legalPlacement(state.balls, candidate.x, candidate.z, state.break)
          ) {
            Object.assign(state.balls[0], candidate, {
              pocketed: false,
              vx: 0,
              vz: 0,
            });
            state.phase = "aiming";
            state.ballInHand = false;
            state.revision++;
            state.message = "Aim, set power, then Shoot.";
            busy = true;
            stable = stableCopy(state);
            ui();
            await persist(stable);
            if (disposed) return;
            finishBusy();
            ui();
            draw();
          }
          break;
        case "aim-left":
        case "aim-right":
          angle += ((b.dataset.action === "aim-left" ? -1 : 1) * Math.PI) / 180;
          angle = Math.atan2(Math.sin(angle), Math.cos(angle));
          ui();
          draw();
          break;
        case "pause":
          pause();
          break;
        case "continue":
          resume();
          break;
        case "restart":
          $("#game-confirm").showModal();
          $('[data-action="cancel-new"]').focus();
          break;
        case "leave":
          if (!store && !ownership) {
            $("#menu-save-message").textContent = conflictMessage;
            $('[data-action="discard"]').hidden = false;
            break;
          }
          if (
            shot &&
            !confirm(
              "The unfinished shot will be discarded. Return to Gallery?",
            )
          )
            break;
          if (await persist(stable)) {
            onLeave();
          } else {
            $("#menu-save-message").textContent =
              "Saving failed. Keep this tab open to continue, retry Save, or explicitly leave without saving.";
            $('[data-action="discard"]').hidden = false;
          }
          break;
        case "discard":
          if (
            confirm(
              "Leave without saving? This device may only have an older turn, or no saved match.",
            )
          )
            onLeave();
          break;
        case "restore":
          if (contextLost) {
            if (
              !stable ||
              (await persist(stable)) ||
              confirm(
                "Saving is unavailable. Reload and lose the unsaved match?",
              )
            )
              location.reload();
            break;
          }
          if (stable) {
            state = stableCopy(stable);
            shot = null;
            busy = false;
            state.message = "Last stable turn restored.";
            ui();
            draw();
          }
          break;
        case "rules":
          $("#game-rules").showModal();
          $('[data-action="close-rules"]').focus();
          break;
        case "close-rules":
          $("#game-rules").close();
          break;
        case "options":
          $("#game-options").showModal();
          break;
        case "close-options":
          $("#game-options").close();
          break;
        case "retry-load":
          location.reload();
          break;
        case "back-to-gallery":
          onLeave();
          break;
        case "inspect":
          if (busy || contextLost || !ready || !state || ["moving", "adjudicating", "recovery"].includes(state.phase)) break;
          inspection = !inspection;
          if (inspection) clearPointers();
          view.setInspection(inspection);
          ui();
          draw();
          break;
        case "fullscreen":
          if (document.fullscreenElement) await document.exitFullscreen?.();
          else await $(".game-layout").requestFullscreen?.();
          break;
        case "install":
          window.dispatchEvent(new CustomEvent("install-app"));
          break;
        case "offline":
          window.dispatchEvent(new CustomEvent("prepare-game-offline"));
          break;
      }
    },
    { signal },
  );
  $("#game-menu").addEventListener(
    "cancel",
    (e) => {
      e.preventDefault();
      resume();
    },
    { signal },
  );
  viewport.addEventListener(
    "game-context-lost",
    () => {
      contextLost = true;
      pauseRequested = false;
      pausedPhase = null;
      clearPointers();
      for (const dialog of all("dialog[open]")) dialog.close();
      if (state) {
        state.phase = "recovery";
        state.message =
          "3D view interrupted. Save and reload to restore the last complete turn.";
      }
      ui();
      $('[data-action="restore"]').focus({ preventScroll: true });
    },
    { signal },
  );
  window.addEventListener(
    "keydown",
    (e) => {
      if (
        root.hidden ||
        e.target.matches("input,button,a") ||
        root.querySelector("dialog[open]")
      )
        return;
      if (e.key === "Escape") {
        // Fullscreen owns Escape; let the browser leave fullscreen first.
        if (document.fullscreenElement) return;
        if (state && !contextLost && !["finished", "paused"].includes(state.phase)) {
          // Keep this keypress from cancelling the modal it just opened.
          e.preventDefault();
          pause();
        }
        return;
      }
      if (e.target !== viewport) return;
      if (e.key.toLowerCase() === "f") {
        e.preventDefault();
        $('[data-action="fullscreen"]').click();
        return;
      }
      if (inspection) {
        if (e.code === "Space" || e.key === "Enter") e.preventDefault();
        if (!busy && !contextLost && !e.ctrlKey && !e.metaKey && !e.altKey && view?.inspectKey(e.key))
          e.preventDefault();
        return;
      }
      if (state?.phase === "placing" && !busy && ownership && e.key === "Enter") {
        e.preventDefault();
        $('[data-action="place"]').click();
      } else if (state?.phase === "placing" && !busy && ownership && e.key.startsWith("Arrow")) {
        const step = e.shiftKey ? 0.005 : 0.02;
        candidate.x +=
          e.key === "ArrowUp" ? step : e.key === "ArrowDown" ? -step : 0;
        candidate.z +=
          e.key === "ArrowRight" ? step : e.key === "ArrowLeft" ? -step : 0;
        e.preventDefault();
        ui();
        draw();
      } else if (state?.phase === "aiming" && !inspection) {
        if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
          angle +=
            ((e.key === "ArrowLeft" ? -1 : 1) *
              (e.shiftKey ? 0.25 : 2) *
              Math.PI) /
            180;
          angle = Math.atan2(Math.sin(angle), Math.cos(angle));
          e.preventDefault();
        } else if (e.key === "ArrowUp" || e.key === "ArrowDown") {
          power = Math.max(
            0.05,
            Math.min(1, power + (e.key === "ArrowUp" ? 0.05 : -0.05)),
          );
          e.preventDefault();
        } else if (e.code === "Space" && !e.repeat) {
          e.preventDefault();
          void shoot();
        }
        ui();
        draw();
      }
    },
    { signal },
  );
  document.addEventListener(
    "visibilitychange",
    () => {
      if (document.hidden) {
        clearPointers();
        pause();
      }
      lastTime = performance.now();
      accumulator = 0;
    },
    { signal },
  );
  let heartbeatRunning = false;
  const heartbeat = setInterval(async () => {
    // An in-flight save owns its state transition until it settles.
    if (!store || disposed || document.hidden || busy || heartbeatRunning) return;
    heartbeatRunning = true;
    try {
      const wasOwner = ownership;
      const acquired = ownership ? await store.renew() : await store.claim();
      if (disposed) return;
      if (acquired && !wasOwner) {
        // Keep input locked until the shared checkpoint replaces stale tab state.
        ownership = false;
        ui();
        saved = await store.load();
        if (disposed) return;
        if (state && (!saved?.checkpoint ||
            (saveFailed && JSON.stringify(stable) !== JSON.stringify(saved.checkpoint)))) {
          // Do not discard a local unsaved turn or keep a lease while blocked.
          saveFailed = true;
          const conflictedStore = store;
          store = null;
          setSaveStatus(conflictMessage, true);
          $("#menu-save-message").textContent = conflictMessage;
          $('[data-action="discard"]').hidden = false;
          ui();
          await conflictedStore.release();
          return;
        }
        if (state) {
          const paused = state.phase === "paused";
          stable = stableCopy(saved.checkpoint);
          state = stableCopy(saved.checkpoint);
          pausedPhase = paused ? state.phase : null;
          if (paused) state.phase = "paused";
          state.message = saved.pending
            ? "Interrupted shot was not recorded. Your previous turn is restored."
            : "Latest saved match restored from this device.";
          shot = null;
          before = null;
          candidate = { x: -0.7, z: 0 };
          saveFailed = false;
        }
        ownership = true;
        setSaveStatus("Local save ready. This tab now owns the match.");
        ui();
        draw();
      } else if (!(ownership = acquired) && state) {
        pause();
        setSaveStatus(
          "Another tab owns this match. Waiting for it to close…",
          true,
        );
        ui();
      }
    } catch {
      setSaveStatus("Local save is unavailable.", true);
    } finally {
      heartbeatRunning = false;
    }
  }, 5000);
  const frameLoop = (now) => {
    if (disposed) return;
    const elapsed = Math.min((now - lastTime) / 1000, 0.08);
    lastTime = now;
    if (!document.hidden && now > manualUntil) {
      accumulator += elapsed;
      let n = 0;
      while (accumulator >= TABLE.step && n++ < 12) {
        simulate(TABLE.step);
        accumulator -= TABLE.step;
      }
    }
    if (!document.hidden && state?.phase === "moving") draw();
    frame = requestAnimationFrame(frameLoop);
  };
  frame = requestAnimationFrame(frameLoop);
  window.render_game_to_text = () =>
    JSON.stringify({
      coordinates: "meters: x along table, z across; Y up",
      phase: state?.phase || "setup",
      revision: state?.revision,
      player: state?.player,
      groups: state?.groups,
      winner: state?.winner,
      break: state?.break,
      balls: state?.balls.map((b) => ({
        id: b.id,
        x: b.x,
        z: b.z,
        vx: b.vx,
        vz: b.vz,
        pocketed: b.pocketed,
      })),
      aim: angle,
      power,
      message: state?.message,
      ready,
      contextLost,
      ownership,
      saveFailed,
      inspection,
    });
  window.advanceTime = (ms) => {
    manualUntil = performance.now() + 1000;
    for (let n = 0; n < Math.ceil(ms / (TABLE.step * 1000)); n++)
      simulate(TABLE.step);
    draw();
  };
  const dispose = () => {
    if (disposed) return;
    disposed = true;
    cancelAnimationFrame(frame);
    clearInterval(heartbeat);
    view?.dispose();
    void store?.release().catch(() => {});
    delete window.render_game_to_text;
    delete window.advanceTime;
    for (const d of all("dialog[open]")) d.close();
    root.replaceChildren();
  };
  signal.addEventListener("abort", dispose, { once: true });
  try {
    try {
      const opened = await openGameStore();
      if (signal.aborted) {
        await opened.release();
        return { dispose };
      }
      store = opened;
      ownership = await store.claim();
      if (signal.aborted) return { dispose };
      saved = await store.load();
      if (signal.aborted) return { dispose };
      setSaveStatus(
        !ownership
          ? "Another session may be active. Waiting for ownership…"
          : saved?.corrupt
            ? "Saved data is incompatible. A new match will replace it."
            : "Local save ready.",
        !ownership || !!saved?.corrupt,
      );
      if (saved?.corrupt) saved = null;
    } catch {
      if (signal.aborted) return { dispose };
      setSaveStatus(
        "Autosave unavailable. This game will stay in this tab only.",
        true,
      );
    }
    if (signal.aborted) return { dispose };
    view = await createGameScene(
      viewport,
      assets,
      signal,
      (n, total) =>
        (loading.textContent = `Preparing your table… ${n}/${total}`),
    );
    if (signal.aborted) {
      view.dispose();
      return { dispose };
    }
    ready = true;
    loading.hidden = true;
    all('[data-action="new"]').forEach((b) => (b.disabled = !ownership));
    $('[data-action="resume"]').disabled = !saved || !ownership;
    ui();
    draw();
  } catch {
    if (!signal.aborted) {
      loadFailed = true;
      loading.textContent = "The 3D table could not load.";
      ui();
    }
  }
  return {
    dispose,
    hasActiveMatch: () => !!state && state.phase !== "finished",
    async prepareUpdate() {
      if (
        (!ownership && state) ||
        busy ||
        shot ||
        state?.phase === "moving" ||
        (state?.phase === "paused" && pausedPhase === "moving")
      )
        return false;
      if (state) {
        await persist(stable);
        return !saveFailed;
      }
      return true;
    },
    beforeLeave() {
      if (
        shot &&
        !confirm("Discard this unfinished shot and return to Gallery?")
      )
        return false;
      if (
        state &&
        saveFailed &&
        !confirm(
          "The current match is not saved. Leave and lose unsaved progress?",
        )
      )
        return false;
      return true;
    },
  };
}
