import { localize, mountMarkup, t } from "../i18n/index.js";
import { copyError, pwaCopy, workerErrorKey } from "./copy.js";
import { createUpdateUi } from "./update-ui.js";
import { classifyUpdate, updateLabelVersion } from "./update-state.js";

const REQUEST_TIMEOUT = 12000,
  ACTIVATION_TIMEOUT = 15000;
export function setupPwa(getGame) {
  let registration,
    deferredInstall,
    lastCheck = 0,
    lastRecoveryCheck = 0,
    updateCheck = null,
    offeredWorker,
    flow = null,
    reloaded = false,
    controllerChanged = false,
    offlineCheck = 0,
    preparingPack = false,
    registrationPending = null;
  const supported = import.meta.env.PROD && "serviceWorker" in navigator;
  let state = Object.freeze({
    connectivity: navigator.onLine ? "online" : "offline",
    offlinePack: "unknown",
    update: "idle",
    updateReady: false,
    updateVersion: null,
    supported,
    build: null,
    error: null,
  });
  const publish = (patch) => {
    state = Object.freeze({ ...state, ...patch });
    window.dispatchEvent(
      new CustomEvent("pwa-state-change", { detail: state }),
    );
  };
  const ui = createUpdateUi(),
    remoteLocks = new Map();
  const notice = document.createElement("div");
  notice.className = "pwa-notice";
  notice.hidden = true;
  notice.setAttribute("role", "status");
  const message = document.createElement("span"),
    action = document.createElement("button"),
    later = document.createElement("button");
  action.type = later.type = "button";
  localize(action, "pwa.updateNow");
  localize(later, "pwa.later");
  notice.append(message, action, later);
  document.body.append(notice);
  // Keep explicit consent reachable inside an existing native modal.
  const positionNotice = () => {
    if (flow || remoteLocks.size) return;
    const dialogs = [...document.querySelectorAll("dialog[open]")].filter(
      (dialog) => dialog !== ui.dialog,
    );
    const parent = dialogs.at(-1) ?? document.body;
    if (notice.parentElement !== parent) parent.append(notice);
  };
  new MutationObserver(positionNotice).observe(document.body, {
    attributes: true,
    attributeFilter: ["open"],
    subtree: true,
    childList: true,
  });
  const installHelp = document.createElement("dialog");
  installHelp.className = "pwa-help";
  installHelp.setAttribute("aria-labelledby", "pwa-install-title");
  mountMarkup(installHelp, '<h2 id="pwa-install-title" data-i18n="pwa.installTitle"></h2><p data-i18n="pwa.installHelp"></p><p data-i18n="pwa.installOffline"></p><button type="button" data-i18n="pwa.gotIt"></button>');
  document.body.append(installHelp);
  let installOpener;
  installHelp.querySelector("button").onclick = () => installHelp.close();
  installHelp.addEventListener("close", () => {
    if (installOpener?.isConnected) installOpener.focus();
  });
  installHelp.addEventListener("click", (event) => {
    if (event.target === installHelp) {
      const r = installHelp.getBoundingClientRect();
      if (
        event.clientX < r.left ||
        event.clientX > r.right ||
        event.clientY < r.top ||
        event.clientY > r.bottom
      )
        installHelp.close();
    }
  });
  function request(
    worker,
    type,
    { onProgress, signal, timeout = REQUEST_TIMEOUT, data = {} } = {},
  ) {
    return new Promise((resolve, reject) => {
      if (!worker) {
        reject(copyError("pwa.starting"));
        return;
      }
      const channel = new MessageChannel();
      let settled = false;
      const finish = (error, result) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        signal?.removeEventListener("abort", abort);
        channel.port1.onmessage = null;
        channel.port1.close();
        channel.port2.close();
        error ? reject(error) : resolve(result);
      };
      const abort = () =>
        finish(new DOMException("Operation cancelled", "AbortError"));
      const timer = setTimeout(
        () => finish(copyError("pwa.timeout")),
        timeout,
      );
      channel.port1.onmessage = (event) => {
        if (settled) return;
        if (event.data?.progress) {
          onProgress?.(event.data);
          return;
        }
        event.data?.ok
          ? finish(null, event.data)
          : finish(copyError(workerErrorKey(event.data?.error, "pwa.failed")));
      };
      signal?.addEventListener("abort", abort, { once: true });
      if (signal?.aborted) {
        abort();
        return;
      }
      try {
        worker.postMessage({ type, ...data }, [channel.port2]);
      } catch {
        finish(copyError("pwa.workerUnavailable"));
      }
    });
  }
  const offlineText = (key, params) => {
    const el = document.querySelector("#game-offline-status");
    if (el) localize(el, key, params);
  };
  async function checkOffline() {
    const run = ++offlineCheck;
    publish({ connectivity: navigator.onLine ? "online" : "offline" });
    if (preparingPack) return;
    if (!registration?.active) {
      offlineText(
        state.offlinePack === "error"
          ? "pwa.offlineError"
          : "pwa.offlineStarting",
      );
      return;
    }
    publish({ offlinePack: "checking" });
    try {
      const result = await request(registration.active, "PACK_STATUS");
      if (run !== offlineCheck || preparingPack) return;
      publish({
        offlinePack: result.ready ? "ready" : "missing",
        build: result.build,
      });
      offlineText(
        result.ready
          ? "pwa.offlineReady"
          : navigator.onLine
            ? "pwa.packMissing"
            : "pwa.offlinePackMissing",
      );
    } catch {
      if (run !== offlineCheck || preparingPack) return;
      publish({ offlinePack: "error" });
      offlineText("pwa.offlineError");
    }
  }
  // Broadcast only an invalidation; each tab verifies its own active build's cache.
  const packSignal = `b3g-pack:${new URL(import.meta.env.BASE_URL, location.href).pathname}`;
  let packChannel;
  try {
    if ("BroadcastChannel" in window) {
      packChannel = new BroadcastChannel(packSignal);
      packChannel.onmessage = (event) => {
        if (event.data === "changed") void checkOffline();
      };
    }
  } catch { /* Focus refresh remains available when messaging is blocked. */ }
  window.addEventListener("storage", (event) => {
    if (event.key === packSignal) void checkOffline();
  });
  window.addEventListener("focus", () => void checkOffline());
  function notifyPackChange() {
    if (packChannel) packChannel.postMessage("changed");
    else {
      try { localStorage.setItem(packSignal, crypto.randomUUID()); }
      catch { /* Storage may be unavailable; focus still refreshes the status. */ }
    }
  }
  const observedRegistrations = new WeakSet();
  function observeUpdates(reg) {
    if (observedRegistrations.has(reg)) return;
    observedRegistrations.add(reg);
    const observeInstalling = () => {
      const worker = reg.installing;
      if (!worker) return;
      const changed = () => {
        if (reg.waiting === worker) showUpdate();
        if (["installed", "redundant", "activated"].includes(worker.state))
          worker.removeEventListener("statechange", changed);
      };
      worker.addEventListener("statechange", changed);
      changed();
    };
    reg.addEventListener("updatefound", observeInstalling);
    observeInstalling();
  }
  async function ensureActiveWorker() {
    if (!supported) throw copyError("pwa.browserUnsupported");
    if (registration?.active) return registration.active;
    if (registrationPending) return registrationPending;
    registrationPending = (async () => {
      const base = new URL(import.meta.env.BASE_URL, location.href);
      const reg = await navigator.serviceWorker.register(new URL("sw.js", base), {
        scope: base.pathname, updateViaCache: "none",
      });
      registration = reg;
      observeUpdates(reg);
      if (reg.active) return reg.active;
      const worker = reg.installing || reg.waiting;
      if (!worker) throw copyError("pwa.offlineStartFailed");
      await new Promise((resolve, reject) => {
        let timer;
        const finish = (error) => {
          clearTimeout(timer);
          worker.removeEventListener("statechange", changed);
          error ? reject(error) : resolve();
        };
        const changed = () => {
          if (reg.active) finish();
          else if (worker.state === "redundant")
            finish(copyError("pwa.offlineStartFailed"));
        };
        timer = setTimeout(() => finish(copyError("pwa.offlineTimeout")), REQUEST_TIMEOUT);
        worker.addEventListener("statechange", changed);
        changed();
      });
      return reg.active;
    })();
    try { return await registrationPending; }
    finally { registrationPending = null; }
  }
  async function readWaitingVersion(worker) {
    try {
      const [identity, info] = await Promise.all([
        request(worker, "BUILD_INFO"),
        fetch(new URL("build-info.json", registration.scope), {
          cache: "no-store",
          signal: AbortSignal.timeout?.(REQUEST_TIMEOUT),
        }).then(response => response.ok ? response.json() : null),
      ]);
      if (info && registration.waiting === worker && identity.build === info.build &&
          typeof info.version === "string" &&
          /^\d+\.\d+\.\d+(?:-[\w.-]+)?(?:\+[\w.-]+)?$/.test(info.version)) {
        publish({ updateVersion: info.version });
      }
    } catch {
      // A version label is optional. Consent is still tied to the waiting worker.
    }
  }
  const showUpdate = () => {
    const worker = registration?.waiting;
    if (!worker || flow || reloaded || remoteLocks.size) return;
    const changed = worker !== offeredWorker;
    offeredWorker = worker;
    localize(message, "pwa.updateAvailable");
    localize(action, "pwa.updateNow");
    action.disabled = later.disabled = false;
    notice.hidden = false;
    publish({
      update: "available",
      updateReady: true,
      updateVersion: changed ? null : state.updateVersion,
      error: null,
    });
    if (changed) void readWaitingVersion(worker);
    positionNotice();
  };
  async function checkForUpdate(recovery = false) {
    if (!supported || flow || reloaded) return;
    if (recovery && updateCheck) await updateCheck;
    if (flow || reloaded) return;
    if (recovery && registration?.waiting) {
      showUpdate();
      return;
    }
    if (!navigator.onLine || updateCheck || registration?.installing) return;
    const now = Date.now();
    if (recovery) {
      if (now - lastRecoveryCheck < 30000) return;
      lastRecoveryCheck = now;
    } else {
      if (now - lastCheck < 600000) return;
      lastCheck = now;
    }
    updateCheck = (async () => {
      try {
        await ensureActiveWorker();
        await registration.update();
        if (registration.waiting && (registration.waiting !== offeredWorker || state.update === "idle"))
          showUpdate();
      } catch {
        // Keep the running build and its retry UI when discovery fails.
      }
    })();
    try { await updateCheck; }
    finally { updateCheck = null; }
  }
  const cancelWorker = (current) => {
    try {
      current.worker?.postMessage({
        type: "CANCEL_UPDATE",
        activationId: current.id,
      });
    } catch {
      /* The waiting worker may already be gone. */
    }
  };
  const failUpdate = (current, error) => {
    if (flow !== current || reloaded) return;
    clearTimeout(current.timer);
    cancelWorker(current);
    current.abort.abort();
    flow = null;
    const key = error?.copyKey ?? "pwa.updateFailed";
    publish({ update: "error", error: t(key, {}, "en") });
    localize(message, key);
    localize(action, "pwa.retry");
    action.disabled = later.disabled = false;
    notice.hidden = false;
    ui.show("error", key);
    positionNotice();
  };
  // The waiting worker an update prompt offered can vanish: another tab activated it, the browser
  // discarded it or it became redundant. Re-read the registration and the published build instead
  // of leaving a prompt that can never succeed.
  async function reconcileUpdate() {
    try { if (navigator.onLine) await registration?.update(); } catch { /* Offline or blocked: use what is known. */ }
    let latestVersion = null;
    try {
      const response = await fetch(new URL("build-info.json", registration?.scope ?? location.href), {
        cache: "no-store", signal: AbortSignal.timeout?.(REQUEST_TIMEOUT),
      });
      if (response.ok && !response.redirected) latestVersion = (await response.json())?.version ?? null;
    } catch { /* The version label is optional; "unknown" keeps the retry prompt. */ }
    return classifyUpdate({ waiting: registration?.waiting, pageVersion: __APP_VERSION__, latestVersion });
  }
  function settleUpToDate() {
    clearTimeout(flow?.timer);
    flow = null;
    offeredWorker = undefined;
    action.disabled = later.disabled = false;
    notice.hidden = true;
    ui.close();
    publish({ update: "idle", updateReady: false, updateVersion: null, error: null });
    positionNotice();
  }
  function offerReload() {
    controllerChanged = true;
    localize(message, "pwa.reloadOffer");
    localize(action, "pwa.reloadSaved");
    action.disabled = later.disabled = false;
    notice.hidden = false;
    publish({ update: "available", updateReady: true, error: null });
    positionNotice();
  }
  // Heal a visible prompt whose worker is gone when the tab returns, comes back online or is shown again.
  async function healNotice() {
    if (!supported || notice.hidden || flow || reloaded || remoteLocks.size || controllerChanged || registration?.waiting) return;
    const outcome = await reconcileUpdate();
    if (flow || reloaded || notice.hidden) return;
    if (outcome === "current") settleUpToDate();
    else if (outcome === "stale") offerReload();
    else if (outcome === "waiting") showUpdate();
  }
  async function beginUpdate() {
    if (flow || reloaded || remoteLocks.size) return;
    const current = {
      id: crypto.randomUUID(),
      worker: registration?.waiting,
      abort: new AbortController(),
      ready: false,
      requested: false,
      timer: null,
    };
    flow = current;
    const target = updateLabelVersion(state.updateVersion, __APP_VERSION__);
    ui.setVersions(target ? `${pwaCopy.version(__APP_VERSION__)} → ${pwaCopy.version(target)}` : "");
    action.disabled = later.disabled = true;
    publish({ update: "preparing", error: null });
    ui.show("preparing", "pwa.preparingUpdate");
    current.timer = setTimeout(
      () =>
        failUpdate(
          current,
          copyError("pwa.updateTimeout"),
        ),
      ACTIVATION_TIMEOUT,
    );
    // Paint feedback before potentially asynchronous IndexedDB work.
    await new Promise((resolve) => requestAnimationFrame(resolve));
    try {
      if (flow !== current) return;
      if (!current.worker && !controllerChanged) {
        const outcome = await reconcileUpdate();
        if (flow !== current) return;
        if (outcome === "waiting") current.worker = registration.waiting;
        else if (outcome === "current") { settleUpToDate(); return; }
        else if (outcome === "stale") controllerChanged = true;
        else throw copyError("pwa.noWaitingUpdate");
      }
      const game = getGame();
      if (game && !(await game.prepareUpdate()))
        throw copyError("pwa.finishShot");
      if (flow !== current) return;
      // Another tab may already have activated the worker. Refresh this document
      // only after this tab's own explicit consent and safe Game save.
      if (!current.worker && controllerChanged) {
        clearTimeout(current.timer);
        flow = null;
        reloaded = true;
        publish({ update: "reloading" });
        ui.show("reloading", "pwa.reloading");
        location.reload();
        return;
      }
      current.ready = true;
      current.requested = true;
      publish({ update: "checking-tabs" });
      ui.show("checking-tabs", "pwa.checkTabs");
      await request(current.worker, "ACTIVATE_UPDATE", {
        signal: current.abort.signal,
        data: {
          activationId: current.id,
          expiresAt: Date.now() + ACTIVATION_TIMEOUT,
        },
      });
      if (flow !== current || reloaded) return;
      publish({ update: "activating" });
      ui.show("activating", "pwa.installing");
    } catch (error) {
      failUpdate(current, error);
    }
  }
  action.onclick = () => void beginUpdate();
  ui.onRetry(() => void beginUpdate());
  ui.onClose(() => {
    ui.close();
    positionNotice();
  });
  later.onclick = () => {
    if (!flow) notice.hidden = true;
  };
  const releaseRemote = (challenge) => {
    const lock = remoteLocks.get(challenge);
    if (!lock) return;
    clearTimeout(lock.timer);
    remoteLocks.delete(challenge);
    if (!remoteLocks.size && !flow) {
      ui.close();
      if (registration?.waiting) showUpdate();
      else publish({ update: "idle", updateReady: false, updateVersion: null });
      positionNotice();
    }
  };
  navigator.serviceWorker?.addEventListener("message", (event) => {
    if (event.data?.type === "RESOURCE_LOAD_FAILED" &&
        event.source === navigator.serviceWorker.controller) {
      void checkForUpdate(true);
    } else if (event.data?.type === "CAN_UPDATE") {
      const game = getGame(),
        ready = !!flow?.ready || !game?.hasActiveMatch();
      if (ready && !flow) {
        const challenge = event.data.challenge;
        if (!remoteLocks.has(challenge))
          remoteLocks.set(challenge, {
            timer: setTimeout(
              () => releaseRemote(challenge),
              ACTIVATION_TIMEOUT + 2000,
            ),
          });
        publish({ update: "checking-tabs" });
        ui.show(
          "checking-tabs",
          "pwa.remoteWait",
          true,
        );
      }
      event.source?.postMessage({
        type: "UPDATE_READY_REPLY",
        challenge: event.data.challenge,
        ready,
        protocol: 2,
      });
    } else if (event.data?.type === "UPDATE_DECISION" && !event.data.accepted)
      releaseRemote(event.data.challenge);
  });
  navigator.serviceWorker?.addEventListener("controllerchange", () => {
    controllerChanged = true;
    if (flow?.ready && flow.requested && !reloaded) {
      const current = flow;
      clearTimeout(current.timer);
      flow = null;
      reloaded = true;
      current.abort.abort();
      notice.hidden = true;
      publish({ update: "reloading" });
      ui.show("reloading", "pwa.reloading");
      location.reload();
      return;
    }
    for (const challenge of [...remoteLocks.keys()]) releaseRemote(challenge);
    if (!reloaded) {
      localize(message, "pwa.reloadOffer");
      localize(action, "pwa.reloadSaved");
      action.disabled = later.disabled = false;
      notice.hidden = false;
      publish({ update: "available", updateReady: true });
      positionNotice();
    }
    void checkOffline();
  });
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredInstall = event;
  });
  window.addEventListener("install-app", async () => {
    if (flow || remoteLocks.size) return;
    installOpener = document.activeElement;
    if (deferredInstall) {
      await deferredInstall.prompt();
      deferredInstall = null;
    } else if (!installHelp.open) {
      installHelp.showModal();
      installHelp.querySelector("button").focus();
    }
  });
  window.addEventListener("prepare-game-offline", async () => {
    const button = document.querySelector('[data-action="offline"]');
    if (preparingPack || button?.disabled || flow || remoteLocks.size) return;
    preparingPack = true;
    ++offlineCheck;
    if (button) button.disabled = true;
    publish({ offlinePack: "preparing" });
    offlineText("pwa.preparingPack");
    try {
      const worker = await ensureActiveWorker();
      const result = await request(worker, "CACHE_GAME", {
        timeout: 90000,
        onProgress: (progress) =>
          offlineText(
            "pwa.savingPack", { progress: progress.progress, total: progress.total },
          ),
      });
      publish({
        offlinePack: result.ready ? "ready" : "missing",
        build: result.build,
      });
      if (result.ready) notifyPackChange();
      offlineText(
        result.ready
          ? "pwa.offlineReady"
          : "pwa.packIncomplete",
      );
    } catch (error) {
      publish({ offlinePack: "error" });
      offlineText(error.copyKey ?? "pwa.packUnavailable");
    } finally {
      preparingPack = false;
      if (button?.isConnected) button.disabled = false;
    }
  });
  for (const type of ["online", "offline", "game-mounted"])
    window.addEventListener(type, () => void checkOffline());
  if (supported) {
    window.addEventListener("online", () => void checkForUpdate(true));
    const register = async () => {
      try {
        await ensureActiveWorker();
        void checkOffline();
        if (registration.waiting) showUpdate();
        void checkForUpdate();
      } catch {
        publish({ offlinePack: "error" });
        offlineText(
          "pwa.packUnavailable",
        );
      }
    };
    void register();
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) { void checkForUpdate(); void healNotice(); }
    });
    window.addEventListener("pageshow", () => void healNotice());
    window.addEventListener("online", () => void healNotice());
  }
  return { beginUpdate, checkForUpdate, getState: () => state };
}
