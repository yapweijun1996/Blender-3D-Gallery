export const warmupBudgetMs = 1500;

export async function warmWithinBudget(renderer, scene, camera, draws, budgetMs = warmupBudgetMs) {
  const deadline = performance.now() + budgetMs;
  let timer, frame, gl, fence, finished = false;
  const hasTime = () => !finished && performance.now() < deadline;
  const timeout = new Promise(resolve => { timer = setTimeout(resolve, budgetMs); });

  async function warm() {
    if (renderer.extensions.has('KHR_parallel_shader_compile')) await renderer.compileAsync(scene, camera);
    for (let i = 0; i < draws.length; i++) {
      if (!hasTime()) return;
      draws[i]();
      if (i < draws.length - 1 && hasTime()) {
        await new Promise(resolve => {
          frame = requestAnimationFrame(() => {
            frame = undefined;
            resolve();
          });
        });
      }
    }
    if (!hasTime()) return;
    gl = renderer.getContext();
    fence = gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0);
    if (!fence) return;
    // Submit the fence and all preceding draws before polling with zero timeout.
    gl.flush();
    while (hasTime() && gl.clientWaitSync(fence, 0, 0) === gl.TIMEOUT_EXPIRED) {
      await new Promise(resolve => setTimeout(resolve, 16));
    }
  }

  try {
    await Promise.race([timeout, warm()]);
  } finally {
    finished = true;
    clearTimeout(timer);
    if (frame !== undefined) cancelAnimationFrame(frame);
    if (fence) gl.deleteSync(fence);
  }
}
