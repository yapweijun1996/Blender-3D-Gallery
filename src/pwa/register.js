import { createUpdateUi } from "./update-ui.js";

const REQUEST_TIMEOUT = 12000,
  ACTIVATION_TIMEOUT = 15000;
export function setupPwa(getGame) {
  let registration,
    deferredInstall,
    lastCheck = 0,
    flow = null,
    reloaded = false,
    controllerChanged = false,
    offlineCheck = 0,
    preparingPack = false;
  const supported = import.meta.env.PROD && "serviceWorker" in navigator;
  let state = Object.freeze({
    connectivity: navigator.onLine ? "online" : "offline",
    offlinePack: "unknown",
    update: "idle",
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
  action.textContent = "Update now";
  later.textContent = "Later";
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
  installHelp.innerHTML =
    '<h2 id="pwa-install-title">Take the table with you.</h2><p>On iPhone, use Share → Add to Home Screen. On supported desktop or Android browsers, use the browser menu to install Blender 3D Gallery.</p><p>Use “Make available offline” in Game before you disconnect. Installation alone does not download the game pack.</p><button type="button">Got it</button>';
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
        reject(new Error("Offline support is starting. Retry shortly."));
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
        () => finish(new Error("Operation timed out. Reconnect and retry.")),
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
          : finish(new Error(event.data?.error || "Operation failed. Retry."));
      };
      signal?.addEventListener("abort", abort, { once: true });
      if (signal?.aborted) {
        abort();
        return;
      }
      try {
        worker.postMessage({ type, ...data }, [channel.port2]);
      } catch {
        finish(new Error("The update worker is unavailable. Retry shortly."));
      }
    });
  }
  const offlineText = (text) => {
    const el = document.querySelector("#game-offline-status");
    if (el) el.textContent = text;
  };
  async function checkOffline() {
    const run = ++offlineCheck;
    publish({ connectivity: navigator.onLine ? "online" : "offline" });
    if (preparingPack) return;
    if (!registration?.active) {
      offlineText(
        "Offline support is starting. Online game remains available.",
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
          ? "Offline ready · local matches available"
          : navigator.onLine
            ? "Game pack not yet saved offline"
            : "Offline · prepare the game pack when connected",
      );
    } catch {
      if (run !== offlineCheck || preparingPack) return;
      publish({ offlinePack: "error" });
      offlineText("Offline support unavailable. Reconnect and retry.");
    }
  }
  const showUpdate = () => {
    if (flow || reloaded) return;
    message.textContent = "A new version is available.";
    action.textContent = "Update now";
    action.disabled = later.disabled = false;
    notice.hidden = false;
    publish({ update: "available", error: null });
    positionNotice();
  };
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
    const text =
      error?.message || "The update could not finish. Reconnect and retry.";
    publish({ update: "error", error: text });
    message.textContent = text;
    action.textContent = "Retry update";
    action.disabled = later.disabled = false;
    notice.hidden = false;
    ui.show("error", text);
    positionNotice();
  };
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
    action.disabled = later.disabled = true;
    publish({ update: "preparing", error: null });
    ui.show("preparing", "Saving your turn and preparing the update…");
    current.timer = setTimeout(
      () =>
        failUpdate(
          current,
          new Error(
            "Update did not finish. Check your saved turn, then retry the update.",
          ),
        ),
      ACTIVATION_TIMEOUT,
    );
    // Paint feedback before potentially asynchronous IndexedDB work.
    await new Promise((resolve) => requestAnimationFrame(resolve));
    try {
      if (flow !== current) return;
      if (!current.worker && !controllerChanged)
        throw new Error(
          "The new version is no longer waiting. Check your connection and retry.",
        );
      const game = getGame();
      if (game && !(await game.prepareUpdate()))
        throw new Error(
          "Finish or restore the current shot, and save your turn before updating.",
        );
      if (flow !== current) return;
      // Another tab may already have activated the worker. Refresh this document
      // only after this tab's own explicit consent and safe Game save.
      if (!current.worker && controllerChanged) {
        clearTimeout(current.timer);
        flow = null;
        reloaded = true;
        publish({ update: "reloading" });
        ui.show("reloading", "Latest version is ready. Reloading the gallery…");
        location.reload();
        return;
      }
      current.ready = true;
      current.requested = true;
      publish({ update: "checking-tabs" });
      ui.show("checking-tabs", "Checking that every open tab is ready…");
      await request(current.worker, "ACTIVATE_UPDATE", {
        signal: current.abort.signal,
        data: {
          activationId: current.id,
          expiresAt: Date.now() + ACTIVATION_TIMEOUT,
        },
      });
      if (flow !== current || reloaded) return;
      publish({ update: "activating" });
      ui.show("activating", "Installing latest version…");
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
      publish({ update: registration?.waiting ? "available" : "idle" });
      positionNotice();
    }
  };
  navigator.serviceWorker?.addEventListener("message", (event) => {
    if (event.data?.type === "CAN_UPDATE") {
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
          "Another tab is installing an update. Please wait…",
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
      ui.show("reloading", "Latest version is ready. Reloading the gallery…");
      location.reload();
      return;
    }
    for (const challenge of [...remoteLocks.keys()]) releaseRemote(challenge);
    if (!reloaded) {
      message.textContent =
        "The latest version is ready. Reload this tab when your turn is saved.";
      action.textContent = "Reload saved version";
      action.disabled = later.disabled = false;
      notice.hidden = false;
      publish({ update: "available" });
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
    offlineText("Preparing offline game…");
    try {
      const result = await request(registration?.active, "CACHE_GAME", {
        timeout: 90000,
        onProgress: (progress) =>
          offlineText(
            `Saving game assets… ${progress.progress}/${progress.total}`,
          ),
      });
      publish({
        offlinePack: result.ready ? "ready" : "missing",
        build: result.build,
      });
      offlineText(
        result.ready
          ? "Offline ready · local matches available"
          : "Offline preparation incomplete. Retry.",
      );
    } catch (error) {
      publish({ offlinePack: "error" });
      offlineText(error.message);
    } finally {
      preparingPack = false;
      if (button?.isConnected) button.disabled = false;
    }
  });
  for (const type of ["online", "offline", "game-mounted"])
    window.addEventListener(type, () => void checkOffline());
  if (supported) {
    const register = async () => {
      try {
        const base = new URL(import.meta.env.BASE_URL, location.href);
        registration = await navigator.serviceWorker.register(
          new URL("sw.js", base),
          { scope: base.pathname, updateViaCache: "none" },
        );
        await navigator.serviceWorker.ready;
        void checkOffline();
        if (registration.waiting) showUpdate();
        registration.addEventListener("updatefound", () => {
          const worker = registration.installing;
          worker?.addEventListener("statechange", () => {
            if (
              worker.state === "installed" &&
              navigator.serviceWorker.controller
            )
              showUpdate();
          });
        });
        await registration.update();
      } catch {
        publish({ offlinePack: "error" });
        offlineText(
          "Offline preparation unavailable. Online game still works.",
        );
      }
    };
    void register();
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden && registration && Date.now() - lastCheck > 600000) {
        lastCheck = Date.now();
        void registration.update().catch(() => {});
      }
    });
  }
  return { checkOffline, getState: () => state };
}
