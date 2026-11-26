export const warmupBudgetMs = 1500;

export async function warmWithinBudget(renderer, scene, camera, draw, budgetMs = warmupBudgetMs) {
  const deadline = performance.now() + budgetMs;
  let timer, gl, fence, finished = false;
  const hasTime = () => !finished && performance.now() < deadline;
  const timeout = new Promise(resolve => { timer = setTimeout(resolve, budgetMs); });

  async function warm() {
    await renderer.compileAsync(scene, camera);
    if (!hasTime()) return;
    draw(hasTime);
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
    if (fence) gl.deleteSync(fence);
  }
}
