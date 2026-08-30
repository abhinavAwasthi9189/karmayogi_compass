// Karmayogi Compass — shared auth/session helper.
// Talks to the FastAPI JSON API under /api/v1 using a JWT bearer token
// stored in localStorage. Include this on every page; it figures out
// what to do based on what's present in the DOM.

const KC_API_BASE = '/api/v1';
const KC_TOKEN_KEY = 'kc_token';
const KC_USER_KEY = 'kc_user';

function kcGetToken () {
  return localStorage.getItem(KC_TOKEN_KEY);
}

function kcGetUser () {
  try {
    return JSON.parse(localStorage.getItem(KC_USER_KEY) || 'null');
  } catch (e) {
    return null;
  }
}

function kcSetSession (token, user) {
  localStorage.setItem(KC_TOKEN_KEY, token);
  localStorage.setItem(KC_USER_KEY, JSON.stringify(user));
}

function kcClearSession () {
  localStorage.removeItem(KC_TOKEN_KEY);
  localStorage.removeItem(KC_USER_KEY);
}

// Fetch wrapper that attaches the bearer token and bounces to /login on 401.
async function kcAuthFetch (path, options = {}) {
  const token = kcGetToken();
  const headers = Object.assign({}, options.headers || {}, {
    Authorization: `Bearer ${token}`,
  });
  const res = await fetch(`${KC_API_BASE}${path}`, Object.assign({}, options, { headers }));
  if (res.status === 401) {
    kcClearSession();
    window.location.href = '/login';
    throw new Error('Not authenticated');
  }
  return res;
}

function kcInitials (name) {
  if (!name) return '?';
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join('');
}

// Turns a failed fetch Response into a readable message. Handles both a
// plain string `detail` and FastAPI's validation-error array format
// (`detail: [{ loc, msg, type }, ...]`), so callers never end up
// stringifying an array/object straight into the UI.
async function kcParseErrorMessage (res, fallback) {
  const body = await res.json().catch(() => ({}));
  if (typeof body.detail === 'string') {
    return body.detail;
  }
  if (Array.isArray(body.detail) && body.detail.length) {
    return body.detail.map((d) => d.msg).filter(Boolean).join('; ') || fallback;
  }
  return fallback;
}

// Fills in the shared sidebar/topbar profile block (name, role, avatar)
// from a freshly-fetched profile so it's never stale across pages.
async function kcPopulateProfileHeader () {
  const nameEl = document.getElementById('profileName');
  const roleEl = document.getElementById('profileRole');
  const avatarEl = document.getElementById('profileAvatar');
  if (!nameEl && !roleEl && !avatarEl) return null;

  try {
    const res = await kcAuthFetch('/profile/me');
    if (!res.ok) return null;
    const profile = await res.json();
    if (nameEl) nameEl.textContent = profile.name;
    if (roleEl) roleEl.textContent = `${profile.designation} — ${profile.department}`;
    if (avatarEl) avatarEl.textContent = kcInitials(profile.name);
    return profile;
  } catch (e) {
    return null;
  }
}

function kcWireLogoutLinks () {
  document.querySelectorAll('.btn-logout').forEach((el) => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      kcClearSession();
      window.location.href = '/login';
    });
  });
}

function kcWireLoginForm () {
  const form = document.getElementById('loginForm');
  if (!form) return;

  const errorEl = document.getElementById('loginError');
  const submitBtn = document.getElementById('loginSubmit');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('govId').value.trim();
    const password = document.getElementById('password').value;

    if (errorEl) errorEl.style.display = 'none';
    if (submitBtn) {
      submitBtn.setAttribute('disabled', 'true');
      submitBtn.textContent = 'Signing in…';
    }

    try {
      const res = await fetch(`${KC_API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        throw new Error(await kcParseErrorMessage(res, 'Incorrect email or password'));
      }

      const data = await res.json();
      kcSetSession(data.access_token, {
        user_id: data.user_id,
        name: data.name,
        role: data.role,
      });
      window.location.href = '/dashboard';
    } catch (err) {
      if (errorEl) {
        errorEl.textContent = err.message || 'Sign in failed. Please try again.';
        errorEl.style.display = 'block';
      }
    } finally {
      if (submitBtn) {
        submitBtn.removeAttribute('disabled');
        submitBtn.textContent = 'Sign In → Dashboard';
      }
    }
  });
}

function kcWireSignupForm () {
  const form = document.getElementById('signupForm');
  if (!form) return;

  const errorEl = document.getElementById('signupError');
  const submitBtn = document.getElementById('signupSubmit');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('name').value.trim();
    const email = document.getElementById('govId').value.trim();
    const department = document.getElementById('department').value.trim();
    const designation = document.getElementById('designation').value.trim();
    const password = document.getElementById('password').value;

    if (errorEl) errorEl.style.display = 'none';
    if (submitBtn) {
      submitBtn.setAttribute('disabled', 'true');
      submitBtn.textContent = 'Creating account…';
    }

    try {
      const res = await fetch(`${KC_API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password, department, designation }),
      });

      if (!res.ok) {
        throw new Error(await kcParseErrorMessage(res, 'Could not create account. Please try again.'));
      }

      const data = await res.json();
      kcSetSession(data.access_token, {
        user_id: data.user_id,
        name: data.name,
        role: data.role,
      });
      window.location.href = '/dashboard';
    } catch (err) {
      if (errorEl) {
        errorEl.textContent = err.message || 'Could not create account. Please try again.';
        errorEl.style.display = 'block';
      }
    } finally {
      if (submitBtn) {
        submitBtn.removeAttribute('disabled');
        submitBtn.textContent = 'Create Account → Dashboard';
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  const onLoginPage = !!document.getElementById('loginForm');
  const onSignupPage = !!document.getElementById('signupForm');

  if (onLoginPage || onSignupPage) {
    // If already signed in, skip straight to the dashboard.
    if (kcGetToken()) {
      window.location.href = '/dashboard';
      return;
    }
    if (onLoginPage) kcWireLoginForm();
    if (onSignupPage) kcWireSignupForm();
    return;
  }

  // Protected page: bounce to login if there's no session at all.
  if (!kcGetToken()) {
    window.location.href = '/login';
    return;
  }

  kcWireLogoutLinks();
  kcPopulateProfileHeader();
});
