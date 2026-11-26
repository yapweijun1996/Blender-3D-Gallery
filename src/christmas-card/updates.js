import { cardVersion } from './version.js';

const version = `v${cardVersion}`;
const checkTimeoutMs = 20000;
const copy = {
  en: {
    check: 'Check for updates',
    checking: 'Checking…',
    updating: 'Updating…',
    ready: 'Update ready. The card will reload when you finish.',
    latest: `${version} is up to date.`,
    offline: 'You’re offline. Reconnect to check for updates.',
    error: 'Couldn’t check for updates. Try again.',
    timeout: 'The update check is taking longer than expected. Try again in a moment.',
    build: 'Build',
  },
  zh: {
    check: '检查更新',
    checking: '正在检查…',
    updating: '正在更新…',
    ready: '更新已就绪，贺卡将在你完成当前操作后重新加载。',
    latest: `${version} 已是最新版本。`,
    offline: '当前处于离线状态，请联网后检查更新。',
    error: '无法检查更新，请重试。',
    timeout: '检查更新耗时较长，请稍后重试。',
    build: '构建',
  },
};

function formInUse() {
  const focused = document.activeElement;
  return focused?.isContentEditable || focused?.matches('input, textarea, [role="textbox"]') ||
    [...document.querySelectorAll('dialog[open], [role="dialog"], [role="alertdialog"]')]
      .some(dialog => dialog.getClientRects().length && getComputedStyle(dialog).visibility === 'visible');
}

export function startCardUpdates({canReload}) {
  const button = document.getElementById('update');
  const status = document.getElementById('update-status');
  const build = button.dataset.build;
  const workers = navigator.serviceWorker;
  const script = new URL('./sw.js', location.href).href;
  const cardController = () => workers?.controller?.scriptURL === script ? workers.controller : null;
  let controller = cardController();
  let registration, candidate, checking = false, timeout, reloadPending = false;
  let language = 'en', state = 'idle';

  function render() {
    const words = copy[language];
    const action = state === 'checking' ? words.checking
      : state === 'updating' || state === 'ready' ? words.updating : words.check;
    button.textContent = `${version} · ${action}`;
    button.title = build ? `${words.build} ${build}` : '';
    status.textContent = ['idle', 'checking', 'updating'].includes(state) ? '' : words[state];
  }

  function report(next) {
    state = next;
    render();
  }

  function finish(result) {
    clearTimeout(timeout);
    if (!reloadPending) report(result);
  }

  const failure = () => navigator.onLine ? 'error' : 'offline';

  function startWaiting(next) {
    report(next);
    clearTimeout(timeout);
    timeout = setTimeout(() => finish(navigator.onLine ? 'timeout' : 'offline'), checkTimeoutMs);
  }

  function watch(worker) {
    if (!worker || worker === candidate) return;
    candidate = worker;
    if (registration.active && registration.active !== worker) startWaiting('updating');
    function changed() {
      if (candidate !== worker) return;
      if (worker.state === 'redundant' || worker.state === 'activated') {
        worker.removeEventListener('statechange', changed);
        candidate = null;
        finish(worker.state === 'activated' ? 'latest' : failure());
      }
    }
    worker.addEventListener('statechange', changed);
    changed();
  }

  async function check() {
    if (reloadPending) return;
    if (!workers || !navigator.onLine) {
      finish(failure());
      return;
    }
    if (checking || candidate) {
      if (state !== 'checking' && state !== 'updating') {
        startWaiting(candidate && registration.active ? 'updating' : 'checking');
      }
      return;
    }
    checking = true;
    startWaiting('checking');
    try {
      if (!registration) {
        registration = await workers.register(script, {scope:'./', updateViaCache:'none'});
        registration.addEventListener('updatefound', () => watch(registration.installing));
      }
      watch(registration.installing || registration.waiting);
      if (!candidate && registration.active) {
        await registration.update();
        watch(registration.installing || registration.waiting);
      }
      if (!candidate && (state === 'checking' || state === 'timeout')) finish('latest');
    } catch {
      finish(failure());
    } finally {
      checking = false;
    }
  }

  function reloadWhenSafe() {
    if (document.hidden || !canReload() || formInUse()) {
      setTimeout(reloadWhenSafe, 200);
      return;
    }
    location.reload();
  }

  workers?.addEventListener('message', event => {
    if (reloadPending || event.source !== controller || controller !== cardController() ||
        event.data?.type !== 'CARD_BUILD' || !build || event.data.build === build) return;
    reloadPending = true;
    clearTimeout(timeout);
    report('ready');
    reloadWhenSafe();
  });
  workers?.addEventListener('controllerchange', () => {
    const previous = controller;
    controller = cardController();
    // A first claim has no previous card controller and needs no reload.
    if (previous && controller && previous !== controller) controller.postMessage({type:'CARD_BUILD'});
  });
  // A takeover can finish before this module runs on a cached page.
  controller?.postMessage({type:'CARD_BUILD'});
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) void check();
  });
  button.addEventListener('click', check);
  void check();

  return {
    localize(next) {
      language = next;
      render();
    },
  };
}
