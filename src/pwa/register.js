export function setupPwa(getGame) {
  let registration,
    deferredInstall,
    updating = false,
    readyForUpdate = false,
    lastCheck = 0;
  const notice = document.createElement("div");
  notice.className = "pwa-notice";
  notice.hidden = true;
  notice.setAttribute("role", "status");
  const message = document.createElement("span"),
    action = document.createElement("button"),
    later = document.createElement("button");
  later.textContent = "Later";
  action.textContent = "Update now";
  notice.append(message, action, later);
  document.body.append(notice);
  const installHelp = document.createElement("dialog");
  installHelp.className = "pwa-help";
  installHelp.innerHTML =
    '<h2>Take the table with you.</h2><p>On iPhone, use Share → Add to Home Screen. On supported desktop or Android browsers, use the browser menu to install Blender 3D Gallery.</p><p>Use “Make available offline” in Game before you disconnect. Installation alone does not download the game pack.</p><button type="button">Got it</button>';
  document.body.append(installHelp);
  installHelp.querySelector("button").onclick = () => installHelp.close();
  const request = (worker, type, onProgress) =>
    new Promise((resolve, reject) => {
      if (!worker) {
        reject(new Error("Offline support is starting. Retry shortly."));
        return;
      }
      const channel = new MessageChannel(),
        timer = setTimeout(
          () => reject(new Error("Operation timed out. Reconnect and retry.")),
          90000,
        );
      channel.port1.onmessage = (e) => {
        if (e.data.progress) {
          onProgress?.(e.data);
          return;
        }
        clearTimeout(timer);
        channel.port1.close();
        e.data.ok
          ? resolve(e.data)
          : reject(new Error(e.data.error || "Operation failed"));
      };
      worker.postMessage({ type }, [channel.port2]);
    });
  const offlineText = (text) => {
    const el = document.querySelector("#game-offline-status");
    if (el) el.textContent = text;
  };
  async function checkOffline() {
    try {
      const r = await request(registration?.active, "PACK_STATUS");
      offlineText(
        r.ready
          ? "Offline ready · local matches available"
          : navigator.onLine
            ? "Game pack not yet saved offline"
            : "Offline · prepare the game pack when connected",
      );
    } catch {
      offlineText("Online play · offline support not ready");
    }
  }
  const showUpdate = () => {
    message.textContent = "A new version is available.";
    action.textContent = "Update now";
    action.disabled = false;
    notice.hidden = false;
  };
  action.onclick = async () => {
    if (updating) return;
    updating = true;
    action.disabled = true;
    later.disabled = true;
    message.textContent = "Saving your turn and preparing the update…";
    try {
      const game = getGame();
      if (game && !(await game.prepareUpdate()))
        throw new Error("Finish or restore the current shot before updating.");
      readyForUpdate = true;
      await request(registration?.waiting, "ACTIVATE_UPDATE");
      message.textContent = "Installing latest version…";
      setTimeout(() => {
        if (updating) {
          message.textContent =
            "Update did not activate. Reload when your turn is saved.";
          action.disabled = false;
          later.disabled = false;
          updating = false;
          readyForUpdate = false;
        }
      }, 12000);
    } catch (e) {
      message.textContent = e.message;
      updating = false;
      readyForUpdate = false;
      action.disabled = false;
      later.disabled = false;
    }
  };
  later.onclick = () => {
    notice.hidden = true;
  };
  navigator.serviceWorker?.addEventListener("message", (event) => {
    if (event.data?.type === "CAN_UPDATE") {
      const game = getGame();
      event.source?.postMessage({
        type: "UPDATE_READY_REPLY",
        challenge: event.data.challenge,
        ready: readyForUpdate || !game?.hasActiveMatch(),
      });
    }
  });
  navigator.serviceWorker?.addEventListener("controllerchange", () => {
    if (updating) {
      updating = false;
      location.reload();
    }
  });
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredInstall = event;
  });
  window.addEventListener("install-app", async () => {
    if (deferredInstall) {
      await deferredInstall.prompt();
      deferredInstall = null;
    } else installHelp.showModal();
  });
  window.addEventListener("prepare-game-offline", async () => {
    const button = document.querySelector('[data-action="offline"]');
    if (button?.disabled) return;
    if (button) button.disabled = true;
    offlineText("Preparing offline game…");
    try {
      if (!registration?.active)
        throw new Error(
          "Offline support is starting. Reopen Game and retry shortly.",
        );
      const r = await request(registration.active, "CACHE_GAME", (p) =>
        offlineText(`Saving game assets… ${p.progress}/${p.total}`),
      );
      offlineText(
        r.ready
          ? "Offline ready · local matches available"
          : "Offline preparation incomplete. Retry.",
      );
    } catch (e) {
      offlineText(e.message);
    } finally {
      if (button) button.disabled = false;
    }
  });
  window.addEventListener("online", () => void checkOffline());
  window.addEventListener("offline", () => void checkOffline());
  window.addEventListener("game-mounted", () => void checkOffline());
  if (!import.meta.env.PROD || !("serviceWorker" in navigator))
    return { checkOffline };
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
      offlineText("Offline preparation unavailable. Online game still works.");
    }
  };
  void register();
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && registration && Date.now() - lastCheck > 600000) {
      lastCheck = Date.now();
      void registration.update().catch(() => {});
    }
  });
  return { checkOffline };
}
