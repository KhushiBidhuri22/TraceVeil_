import { api,pending,loading } from '../services/traceveil-api.js';
import { isConnected } from '../services/http.js';
import { text,PENDING } from '../utils/display.js';
const $=selector=>document.querySelector(selector);

// Signup is the new-visitor entry. Login remains directly available at #login.
// BACKEND CONNECT: Configure signup/session/login/logout in BACKEND_CONNECT.js.
// Only a user returned by the server unlocks the workspace. The backend must
// authenticate and authorize every protected request; hiding UI is not security.
export class AccessView {
  constructor({navigate,onChange}) {
    Object.assign(this,{navigate,onChange});
    this.user=null;this.state=pending();this.controller=null;
    $('#access-button').addEventListener('click',()=>this.open());
    $('#login-form').addEventListener('submit',event=>{event.preventDefault();this.signIn();});
    $('#logout-button').addEventListener('click',()=>this.signOut());
    $('#session-retry').addEventListener('click',()=>this.load().then(allowed=>{if(allowed)this.onChange(this.user);}));
    this.render();
  }
  canRead() { return Boolean(this.user); }
  open() { this.navigate('login'); }
  leave() {
    // Ignore a late sign-in response if the user moves to another public page.
    // An initial session check may continue so a real existing session can restore.
    if(this.phase==='login'&&this.controller){
      this.controller.abort();this.controller=null;this.state=pending();
    }
    $('#login-password').value='';this.render();
  }
  registered(registration,email) {
    this.controller?.abort();this.controller=null;this.phase='login';
    this.user=null;this.state={status:'ready',data:null};
    $('#login-identity').value=registration.loginIdentifier??email;
    $('#login-password').value='';
    const messages={
      created:'Your account has been created. Sign in to continue.',
      pending_approval:'Registration submitted. Your organization must approve your account before you can sign in.',
      verification_required:'Check your email to verify your account before signing in.',
    };
    this.render(registration.message??messages[registration.status]);
    this.navigate('login');
  }
  render(message) {
    const connected=isConnected('login')&&isConnected('session');
    const busy=this.state.status==='loading',signedIn=Boolean(this.user);
    $('#login-form').hidden=signedIn;
    $('#login-switch').hidden=signedIn;
    $('#login-form').setAttribute('aria-busy',String(busy));
    for(const id of ['login-identity','login-password','login-submit'])$('#'+id).disabled=!connected||busy;
    $('#login-submit').textContent=busy?'Please wait…':connected?'Sign in →':PENDING;
    $('#access-continue').hidden=!signedIn;
    $('#logout-button').hidden=!signedIn;
    $('#logout-button').disabled=!isConnected('logout')||busy;
    $('#logout-button').textContent=isConnected('logout')?'Sign out':PENDING;
    $('#session-retry').hidden=!(this.phase==='session'&&this.state.status==='error');
    $('#session-retry').disabled=busy;
    $('#access-status').textContent=message??(signedIn?`${text(this.user.name)} · ${text(this.user.role)}`:this.state.status==='error'?this.state.message:connected?'Sign in with your personnel account.':PENDING);
    $('#session-footer').hidden=!signedIn;
    $('#session-footer').textContent=signedIn?`${text(this.user.name)} / ${text(this.user.role)}`:'';
    $('#access-button').textContent=signedIn?'Personnel account':'Personnel access';
  }
  async load() {
    this.controller?.abort();
    const controller=new AbortController();this.controller=controller;this.phase='session';
    this.state=loading();this.render(isConnected('session')?'Checking session…':PENDING);
    try {
      const result=await api.session(controller.signal);
      if(controller.signal.aborted||this.controller!==controller)return false;
      this.controller=null;
      // A 401 means the visitor is signed out, not that the UI should open.
      this.state=result.code===401?{status:'ready',data:null}:result;
      this.user=this.state.status==='ready'?this.state.data:null;
      this.render();return this.canRead();
    } catch(error) {
      if(error.name!=='AbortError'&&this.controller===controller){this.controller=null;this.state={status:'error',message:error.message};this.render();}
      return false;
    }
  }
  async signIn() {
    if(!isConnected('login')||!isConnected('session')||this.state.status==='loading')return;
    const username=$('#login-identity').value.trim(),password=$('#login-password').value;
    if(!username||!password)return;
    this.controller?.abort();
    const controller=new AbortController();this.controller=controller;this.phase='login';
    this.state=loading();this.render('Signing in…');
    try {
      const result=await api.login(username,password,controller.signal);
      if(controller.signal.aborted||this.controller!==controller)return;
      this.controller=null;$('#login-password').value='';this.state=result;
      if(result.status==='ready'&&result.data){
        this.user=result.data;this.render();this.onChange(this.user);
      } else this.render(result.message??'Sign-in was not completed.');
    } catch(error) {
      if(error.name!=='AbortError'&&this.controller===controller){
        this.controller=null;$('#login-password').value='';
        this.state={status:'error',message:error.message};this.render();
      }
    }
  }
  async signOut() {
    if(!isConnected('logout')||this.state.status==='loading')return;
    const controller=new AbortController();this.controller=controller;this.phase='logout';
    this.state=loading();this.render('Signing out…');
    try {
      const result=await api.logout(controller.signal);
      if(controller.signal.aborted||this.controller!==controller)return;
      this.controller=null;this.state=result;
      if(result.status==='ready'||result.code===401){
        this.user=null;$('#login-password').value='';this.render('Signed out.');this.onChange(null);
      } else this.render(result.message??PENDING);
    } catch(error) {
      if(error.name!=='AbortError'&&this.controller===controller){this.controller=null;this.state={status:'error',message:error.message};this.render();}
    }
  }
  expire() {
    this.controller?.abort();this.controller=null;
    this.user=null;this.state={status:'ready',data:null};$('#login-password').value='';
    this.render('Your session has expired. Sign in again.');
  }
}
