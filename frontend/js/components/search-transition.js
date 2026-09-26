// Visible glitch/buffering is presentation, not a made-up backend percentage.
// The popup waits for BOTH this short visual transition AND the actual response.
// Abort clears its timer so a cancelled search can never open a late popup.
export function waitForSearchEffect(motion, signal, clock=globalThis) {
  return new Promise((resolve,reject) => {
    if (signal.aborted) { reject(new DOMException('Cancelled','AbortError')); return; }
    const cancel = () => { clock.clearTimeout(timer); signal.removeEventListener('abort',cancel); reject(new DOMException('Cancelled','AbortError')); };
    const timer = clock.setTimeout(() => { signal.removeEventListener('abort',cancel); resolve(); }, motion ? 1400 : 180);
    signal.addEventListener('abort',cancel,{once:true});
  });
}
