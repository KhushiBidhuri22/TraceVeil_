import { api, pending, loading } from '../services/traceveil-api.js';
import { isConnected } from '../services/http.js';
import { PENDING } from '../utils/display.js';
const $ = selector => document.querySelector(selector);

// BACKEND CONNECT: Add the real signup URL, request fields and response mapping
// in BACKEND_CONNECT.js. No credentials/accounts are stored in browser storage.
// Successful registration continues to login; it never unlocks the workspace.
export class SignupView {
  constructor({onRegistered}) {
    this.onRegistered = onRegistered;
    this.state = pending();
    this.controller = null;
    $('#signup-form').addEventListener('submit', event => {
      event.preventDefault();
      this.register();
    });
    for (const id of ['signup-name', 'signup-password', 'signup-confirm']) {
      $('#' + id).addEventListener('input', () => $('#' + id).setCustomValidity(''));
    }
    $('#signup-password').addEventListener('input', () => $('#signup-confirm').setCustomValidity(''));
    this.render();
  }
  render(message) {
    const connected = isConnected('signup'), busy = this.state.status === 'loading';
    $('#signup-form').setAttribute('aria-busy', String(busy));
    for (const id of ['signup-name', 'signup-email', 'signup-organization', 'signup-password', 'signup-confirm']) {
      $('#' + id).disabled = busy;
    }
    $('#signup-submit').disabled = !connected || busy;
    $('#signup-submit').textContent = busy ? 'Creating account…' : 'Create account →';
    const status = $('#signup-status');
    status.textContent = message ?? (this.state.status === 'error' ? this.state.message : connected ? '' : PENDING);
    status.hidden = !status.textContent;
    status.dataset.state = this.state.status;
  }
  clearPasswords() {
    for (const id of ['signup-password', 'signup-confirm']) {
      $('#' + id).value = '';
      $('#' + id).setCustomValidity('');
    }
  }
  leave() {
    this.controller?.abort();
    this.controller = null;
    this.clearPasswords();
    this.state = pending();
    this.render();
  }
  async register() {
    if (!isConnected('signup') || this.state.status === 'loading') return;
    const form = $('#signup-form');
    const fullName = $('#signup-name').value.trim();
    const email = $('#signup-email').value.trim();
    const organization = $('#signup-organization').value.trim();
    const password = $('#signup-password').value;
    $('#signup-name').setCustomValidity(fullName ? '' : 'Enter your name.');
    $('#signup-password').setCustomValidity(password.length >= 8 ? '' : 'Use at least 8 characters.');
    $('#signup-confirm').setCustomValidity(password === $('#signup-confirm').value ? '' : 'Passwords must match.');
    if (!form.reportValidity()) return;
    const controller = new AbortController();
    this.controller = controller;
    this.state = loading();
    this.render('Creating your account…');
    try {
      const result = await api.signup({fullName, email, organization, password}, controller.signal);
      if (controller.signal.aborted || this.controller !== controller) return;
      this.controller = null;
      this.clearPasswords();
      this.state = result;
      if (result.status === 'ready') {
        form.reset();
        this.render();
        this.onRegistered(result.data, email);
      } else this.render(result.message ?? 'Registration was not completed. Try again.');
    } catch (error) {
      if (controller.signal.aborted || this.controller !== controller) return;
      this.controller = null;
      this.clearPasswords();
      this.state = {status:'error', message:error.message};
      this.render();
    }
  }
}
