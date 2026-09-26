import { api } from '../services/traceveil-api.js';
import { isConnected } from '../services/http.js';
import { PENDING } from '../utils/display.js';

export const EXPORT_FORMATS = ['csv','json'];

export function exportFilename(disposition,actor,format) {
  const match=/filename="?([^";]+)"?/i.exec(disposition??'');
  const safe=match?.[1]?.replace(/[\\/:*?"<>|\u0000-\u001f]/g,'_');
  if (safe) return safe;
  return `traceveil-${String(actor.id).replace(/[^a-z0-9_-]/gi,'_')}.${format}`;
}
export class ExportView {
  constructor({dialogs,getActor,canRead,onStatus}) {
    Object.assign(this,{dialogs,getActor,canRead,onStatus});this.controller=null;
    document.querySelectorAll('[data-open-export]').forEach(button=>button.addEventListener('click',()=>this.open()));
    document.querySelectorAll('[data-export]').forEach(button=>button.addEventListener('click',()=>this.download(button.dataset.export)));
    document.querySelector('#export-dialog').addEventListener('close',()=>this.cancel());
  }
  refresh(message) {
    const ready=this.canRead()&&Boolean(this.getActor()?.id)&&isConnected('export');
    document.querySelectorAll('[data-export]').forEach(button=>{
      button.disabled=!ready||Boolean(this.controller);
      button.querySelector('span').textContent=ready?({csv:'CSV · Account connections →',json:'JSON · Account record →'}[button.dataset.export]):PENDING;
    });
    document.querySelector('#export-status').textContent=message??(ready?'Choose a format.':PENDING);
  }
  open() {this.refresh();this.dialogs.open(document.querySelector('#export-dialog'));}
  cancel() {this.controller?.abort();this.controller=null;}
  async download(format) {
    if(!EXPORT_FORMATS.includes(format)){this.refresh('Choose CSV or JSON.');return;}
    const actor=this.getActor();if(!actor||this.controller||!this.canRead())return;
    const controller=new AbortController();this.controller=controller;this.refresh('Preparing download…');
    try {
      // BACKEND CONNECT: CSV/JSON bytes come from the actual export endpoint.
      const result=await api.export(actor.id,format,controller.signal);
      if(controller.signal.aborted)return;
      this.controller=null;
      if(result.status!=='ready'){this.refresh(result.message??PENDING);this.onStatus(result);return;}
      const file=result.data,url=URL.createObjectURL(file.blob);
      const link=document.createElement('a');link.href=url;link.download=exportFilename(file.disposition,actor,format);
      document.body.append(link);link.click();link.remove();
      setTimeout(()=>URL.revokeObjectURL(url),10000);
      this.refresh('Download started.');
    } catch(error) {if(!controller.signal.aborted){this.controller=null;this.refresh(error.message);}}
  }
}
