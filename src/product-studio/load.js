/** Latest selection owns UI updates; obsolete parsed values must be released. */
export function createLatestLoader({ prepare, commit, release, start, fail }) {
  let generation = 0, active = null, disposed = false;
  return {
    async select(item) {
      if (disposed) return;
      const token = ++generation;
      active?.abort();
      const request = new AbortController();
      active = request;
      start(item);
      let value;
      try {
        value = await prepare(item, request.signal);
        if (disposed || token !== generation || request.signal.aborted) {
          release(value); value = undefined; return;
        }
        commit(value, item);
        value = undefined; // ownership transferred to the mounted scene
      } catch (error) {
        if (value) release(value);
        if (!disposed && token === generation && error?.name !== 'AbortError') fail(error, item);
      } finally {
        if (token === generation) active = null;
      }
    },
    dispose() { if (disposed) return; disposed = true; generation++; active?.abort(); active = null; },
  };
}

/** Per-call deduplication never retains disposed materials across model switches. */
export function disposeProduct(object) {
  const seen = new Set();
  object?.traverse(child => {
    if (child.geometry && !seen.has(child.geometry)) { seen.add(child.geometry); child.geometry.dispose(); }
    for (const material of child.material ? [].concat(child.material) : []) {
      if (seen.has(material)) continue;
      seen.add(material);
      for (const value of Object.values(material)) {
        if (!value?.isTexture || seen.has(value)) continue;
        seen.add(value); value.dispose();
        if (value.image && !seen.has(value.image)) { seen.add(value.image); value.image.close?.(); }
      }
      material.dispose();
    }
  });
}
