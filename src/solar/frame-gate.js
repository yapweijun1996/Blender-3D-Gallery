// Keep at most one Solar frame in the GPU queue. Poll only; never block JS.
// Simulation and input still update every RAF while the GPU finishes its work.
export function createFrameGate(gl) {
  let sync=null, disposed=false;
  let supported=['fenceSync','clientWaitSync','deleteSync','flush'].every(name=>typeof gl[name]==='function');
  const clear=()=>{const previous=sync;sync=null;if(previous)try{gl.deleteSync(previous);}catch{}};
  const fallback=()=>{clear();supported=false;};
  return {
    ready(){
      if(disposed)return false;
      if(gl.isContextLost?.()){clear();return false;}
      if(!supported||!sync)return true;
      try {
        const result=gl.clientWaitSync(sync,0,0);
        if(result===gl.TIMEOUT_EXPIRED)return false;
        if(result===gl.WAIT_FAILED){fallback();return true;}
        clear();return true;
      }catch{fallback();return true;}
    },
    submitted(){
      if(disposed||!supported||sync)return;
      try{sync=gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE,0);if(!sync){fallback();return;}gl.flush();}
      catch{fallback();}
    },
    dispose(){if(disposed)return;disposed=true;clear();},
  };
}
