import { RULES_VERSION } from "./rules.js";
import { TABLE } from "./table.js";
export function validateMatch(m) {
  if (
    !m ||
    m.schema !== 1 ||
    m.rulesVersion !== RULES_VERSION ||
    m.tableVersion !== TABLE.version ||
    typeof m.matchId !== "string" ||
    m.matchId.length < 1 ||
    m.matchId.length > 128 ||
    !Number.isInteger(m.revision) ||
    m.revision < 0 ||
    ![0, 1].includes(m.player) ||
    !Array.isArray(m.groups) ||
    m.groups.length !== 2 ||
    !m.groups.every((g) => g === null || g === "solids" || g === "stripes") ||
    !["aiming", "placing", "finished"].includes(m.phase) ||
    !Array.isArray(m.balls) ||
    m.balls.length !== 16 ||
    !Array.from(m.balls).every(
      (b) => b && typeof b === "object" && !Array.isArray(b),
    ) ||
    new Set(m.balls.map((b) => b.id)).size !== 16
  )
    return false;
  if (
    m.groups[0] === null
      ? m.groups[1] !== null
      : m.groups[0] === m.groups[1] || m.groups[1] === null
  )
    return false;
  if (
    typeof m.break !== "boolean" ||
    typeof m.ballInHand !== "boolean" ||
    ![null, 0, 1].includes(m.winner)
  )
    return false;
  if (
    (m.phase === "finished") !== (m.winner !== null) ||
    (m.phase === "placing") !== m.ballInHand
  )
    return false;
  if (
    m.balls.some((b, i) => b.id !== i) ||
    ((m.phase === "placing") !== m.balls[0].pocketed &&
      m.phase !== "finished") ||
    (m.phase === "finished") !== m.balls[8].pocketed ||
    (m.break && (m.groups[0] !== null || m.phase === "finished"))
  )
    return false;
  for (const b of m.balls)
    if (
      !Number.isInteger(b.id) ||
      b.id < 0 ||
      b.id > 15 ||
      typeof b.pocketed !== "boolean" ||
      ![b.x, b.z, b.vx, b.vz].every(Number.isFinite) ||
      Math.abs(b.x) > 1.21 ||
      Math.abs(b.z) > 0.66 ||
      b.vx !== 0 ||
      b.vz !== 0 ||
      !Array.isArray(b.q) ||
      b.q.length !== 4 ||
      !Array.from(b.q).every(Number.isFinite) ||
      Math.abs(Math.hypot(...b.q) - 1) > 0.01
    )
      return false;
  const active = m.balls.filter((b) => !b.pocketed);
  for (let i = 0; i < active.length; i++)
    for (let j = i + 1; j < active.length; j++)
      if (
        Math.hypot(active[i].x - active[j].x, active[i].z - active[j].z) <
        TABLE.radius * 2 - 0.0015
      )
        return false;
  return true;
}
export async function openGameStore() {
  const db = await new Promise((resolve, reject) => {
    const r = indexedDB.open("blender-gallery-game-v1", 1);
    r.onupgradeneeded = () => r.result.createObjectStore("records");
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
  const owner = crypto.randomUUID();
  // Browser-managed locks disappear on reload/crash. The lease is the fallback
  // for browsers without Web Locks and is retried by the page after expiry.
  let unlock = null,
    released = false,
    claimPending = null,
    releasePending = null;
  const claimLock = () => {
    if (released) return Promise.resolve(false);
    if (!navigator.locks || unlock) return Promise.resolve(true);
    if (claimPending) return claimPending;
    claimPending = new Promise((resolve, reject) => {
      navigator.locks
        .request(
          "blender-gallery-game-owner",
          { ifAvailable: true },
          async (lock) => {
            // A request can complete after the owning route has been disposed.
            if (!lock || released) {
              resolve(false);
              return;
            }
            await new Promise((done) => {
              unlock = done;
              resolve(true);
            });
          },
        )
        .catch(reject);
    }).finally(() => {
      claimPending = null;
    });
    return claimPending;
  };
  const action = (fn, allowReleased = false) =>
    new Promise((resolve, reject) => {
      if (released && !allowReleased) {
        reject(new Error("Game storage is closed"));
        return;
      }
      let result;
      const tx = db.transaction("records", "readwrite");
      const s = tx.objectStore("records");
      tx.oncomplete = () => resolve(result);
      tx.onerror = () => reject(tx.error || new Error("Save failed"));
      tx.onabort = () => reject(tx.error || new Error("Save canceled"));
      fn(s, (v) => (result = v), tx);
    });
  const access = (s, done, write, acquire = false) => {
    const r = s.get("owner");
    r.onsuccess = () => {
      const current = r.result,
        now = Date.now();
      if (
        current &&
        current.id !== owner &&
        current.until > now &&
        !(acquire && unlock)
      ) {
        done(false);
        return;
      }
      if (!acquire && (!current || current.id !== owner)) {
        done(false);
        return;
      }
      s.put({ id: owner, until: now + 20000 }, "owner");
      write?.(s);
      done(true);
    };
  };
  return {
    claim: async () =>
      (await claimLock()) &&
      !released &&
      action((s, done) => access(s, done, null, true)),
    renew: () => action((s, done) => access(s, done)),
    load: () =>
      action((s, done) => {
        const r = s.get("match");
        r.onsuccess = () => {
          if (r.result && !validateMatch(r.result.checkpoint)) {
            done({ corrupt: true });
            return;
          }
          done(r.result || null);
        };
      }),
    save: (checkpoint, pending = null) => {
      if (!validateMatch(checkpoint))
        return Promise.reject(new Error("Invalid checkpoint"));
      return action((s, done) =>
        access(s, done, (s) => {
          const r = s.get("match");
          r.onsuccess = () => {
            if (r.result) s.put(r.result, "previous");
            s.put(
              {
                checkpoint: structuredClone(checkpoint),
                pending,
                savedAt: Date.now(),
              },
              "match",
            );
          };
        }),
      ).then((ok) => {
        if (!ok) throw new Error("This match is owned by another tab");
      });
    },
    release: () => {
      if (releasePending) return releasePending;
      released = true;
      releasePending = (async () => {
        try {
          await action((s, done) => {
            const r = s.get("owner");
            r.onsuccess = () => {
              if (r.result?.id === owner) s.delete("owner");
              done(true);
            };
          }, true);
        } finally {
          db.close();
          unlock?.();
          unlock = null;
        }
      })();
      return releasePending;
    },
  };
}
