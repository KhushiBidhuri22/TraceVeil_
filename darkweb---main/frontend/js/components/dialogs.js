export function createDialogs(getMotion) {
  const timers = new WeakMap();
  function open(dialog) {
    clearTimeout(timers.get(dialog)); dialog.classList.remove('is-closing');
    if (!dialog.open) dialog.showModal();
  }
  function close(dialog, after, immediate=false) {
    clearTimeout(timers.get(dialog));
    if (!dialog.open) { after?.(); return; }
    const finish = () => { dialog.classList.remove('is-closing'); dialog.close(); timers.delete(dialog); after?.(); };
    if (!getMotion() || immediate) finish();
    else { dialog.classList.add('is-closing'); timers.set(dialog,setTimeout(finish,160)); }
  }
  document.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click',() => close(button.closest('dialog'))));
  document.querySelectorAll('dialog:not(#scan-dialog)').forEach(dialog => {
    dialog.addEventListener('cancel',e => { e.preventDefault(); close(dialog); });
    dialog.addEventListener('click',e => {
      const b = dialog.getBoundingClientRect();
      if (e.target === dialog && (e.clientX < b.left || e.clientX > b.right || e.clientY < b.top || e.clientY > b.bottom)) close(dialog);
    });
  });
  return {open,close,closeAll:() => document.querySelectorAll('dialog[open]').forEach(dialog => close(dialog,null,true))};
}
