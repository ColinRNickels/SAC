const pendingContainer = document.getElementById('pending-users');
const allUsersContainer = document.getElementById('all-users');
const certContainer = document.getElementById('certifications');
const certForm = document.getElementById('cert-form');
const grantForm = document.getElementById('grant-form');
const grantResult = document.getElementById('grant-result');
const grantSelect = document.getElementById('grant-certification');
const revokeButton = document.getElementById('revoke-button');
const swipeAnalytics = document.getElementById('swipe-analytics');
const uniqueAnalytics = document.getElementById('unique-analytics');
const certAnalytics = document.getElementById('cert-analytics');
const termsForm = document.getElementById('terms-form');
const termsInput = document.getElementById('terms-input');
const termsResult = document.getElementById('terms-result');
const adminAuthForm = document.getElementById('admin-auth-form');
const adminTokenInput = document.getElementById('admin-token');
const adminNameInput = document.getElementById('admin-name');
const adminAuthResult = document.getElementById('admin-auth-result');
const adminLogoutButton = document.getElementById('admin-logout');
const heatmapGrid = document.getElementById('heatmap-grid');

const TOKEN_KEY = 'sacAdminToken';
const NAME_KEY = 'sacAdminName';

const getToken = () => localStorage.getItem(TOKEN_KEY) || '';
const getAdminName = () => localStorage.getItem(NAME_KEY) || '';

const setToken = (token) => {
  localStorage.setItem(TOKEN_KEY, token);
};

const setAdminName = (name) => {
  localStorage.setItem(NAME_KEY, name);
};

const authHeaders = () => {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const fetchWithAuth = async (url, options = {}) => {
  const headers = {
    ...(options.headers || {}),
    ...authHeaders(),
  };
  const response = await fetch(url, { ...options, headers, credentials: 'same-origin' });
  if (response.status === 401) {
    setResult(adminAuthResult, 'Admin token required or invalid.', 'error');
  }
  return response;
};

const setResult = (element, message, status) => {
  element.textContent = message;
  element.className = `result ${status || ''}`.trim();
};

const renderPendingUsers = (users) => {
  pendingContainer.innerHTML = '';
  if (users.length === 0) {
    pendingContainer.textContent = 'No pending users.';
    return;
  }

  users.forEach((user) => {
    const row = document.createElement('div');
    row.className = 'table-row';
    row.innerHTML = `
      <div>
        <strong>${user.first_name} ${user.last_name}</strong>
        <small>Campus ID: ${user.campus_id}</small>
      </div>
      <div>
        <small>Email</small>
        <div>${user.email}</div>
      </div>
      <div class="button-row">
        <button class="button" data-action="approve" data-id="${user.id}">Approve</button>
        <button class="button ghost" data-action="deny" data-id="${user.id}">Deny</button>
      </div>
    `;
    pendingContainer.appendChild(row);
  });
};

const renderAllUsers = (users) => {
  allUsersContainer.innerHTML = '';
  if (users.length === 0) {
    allUsersContainer.textContent = 'No users yet.';
    return;
  }

  users.forEach((user) => {
    const row = document.createElement('div');
    row.className = 'table-row';
    row.innerHTML = `
      <div>
        <strong>${user.first_name} ${user.last_name}</strong>
        <small>Campus ID: ${user.campus_id}</small>
      </div>
      <div>
        <small>Email</small>
        <div>${user.email}</div>
      </div>
      <div>
        <small>Status</small>
        <div>${user.status}</div>
      </div>
    `;
    allUsersContainer.appendChild(row);
  });
};

const renderCertifications = (certs) => {
  certContainer.innerHTML = '';
  grantSelect.innerHTML = '';
  if (certs.length === 0) {
    certContainer.textContent = 'No certifications yet.';
    return;
  }

  certs.forEach((cert) => {
    const row = document.createElement('div');
    row.className = 'table-row';
    row.innerHTML = `
      <div>
        <strong>${cert.name}</strong>
        <small>${cert.scope}</small>
      </div>
      <div>${cert.description || 'No description'}</div>
      <div>ID: ${cert.id}</div>
    `;
    certContainer.appendChild(row);

    const option = document.createElement('option');
    option.value = cert.id;
    option.textContent = `${cert.name} (${cert.scope})`;
    grantSelect.appendChild(option);
  });
};

const renderAnalytics = (container, rows, labelKey = 'bucket') => {
  container.innerHTML = '';
  if (rows.length === 0) {
    container.textContent = 'No data yet.';
    return;
  }

  rows.forEach((row) => {
    const rowEl = document.createElement('div');
    rowEl.className = 'table-row';
    rowEl.innerHTML = `
      <div><strong>${row[labelKey]}</strong></div>
      <div>Count: ${row.count}</div>
    `;
    container.appendChild(rowEl);
  });
};

const renderHeatmap = (rows) => {
  heatmapGrid.innerHTML = '';
  const dayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const hours = Array.from({ length: 24 }, (_, i) => i);
  const counts = new Map(rows.map((row) => [`${row.day}-${row.hour}`, row.count]));
  const maxCount = rows.reduce((max, row) => Math.max(max, row.count), 0);

  const headerRow = document.createElement('div');
  headerRow.className = 'heatmap-row';
  headerRow.innerHTML = `<span class="heatmap-label"></span>${hours
    .map((hour) => `<span class="heatmap-label">${hour}</span>`)
    .join('')}`;
  heatmapGrid.appendChild(headerRow);

  dayLabels.forEach((label, dayIndex) => {
    const row = document.createElement('div');
    row.className = 'heatmap-row';
    const cells = hours
      .map((hour) => {
        const key = `${dayIndex}-${String(hour).padStart(2, '0')}`;
        const count = counts.get(key) || 0;
        const intensity = maxCount ? count / maxCount : 0;
        const alpha = 0.12 + intensity * 0.78;
        const background = `rgba(66, 126, 147, ${alpha})`;
        return `<span class="heatmap-cell" style="background:${background}" title="${label} ${hour}:00 • ${count} swipes"></span>`;
      })
      .join('');
    row.innerHTML = `<span class="heatmap-label">${label}</span>${cells}`;
    heatmapGrid.appendChild(row);
  });
};

const fetchAnalytics = async () => {
  const [swipesResponse, uniqueResponse, certResponse, heatmapResponse] = await Promise.all([
    fetchWithAuth('/api/analytics/swipes?interval=day'),
    fetchWithAuth('/api/analytics/unique-users'),
    fetchWithAuth('/api/analytics/cert-usage'),
    fetchWithAuth('/api/analytics/heatmap'),
  ]);

  const swipes = swipesResponse.ok ? await swipesResponse.json() : [];
  const uniques = uniqueResponse.ok ? await uniqueResponse.json() : [];
  const certs = certResponse.ok ? await certResponse.json() : [];
  const heatmap = heatmapResponse.ok ? await heatmapResponse.json() : [];

  renderAnalytics(swipeAnalytics, swipes);
  renderAnalytics(uniqueAnalytics, uniques);
  renderAnalytics(certAnalytics, certs, 'name');
  renderHeatmap(heatmap);
};

const fetchPending = async () => {
  const response = await fetchWithAuth('/api/users?status=pending');
  if (response.ok) {
    const data = await response.json();
    renderPendingUsers(data);
  }
};

const fetchAllUsers = async () => {
  const response = await fetchWithAuth('/api/users');
  if (response.ok) {
    const data = await response.json();
    renderAllUsers(data);
  }
};

const fetchCertifications = async () => {
  const response = await fetch('/api/certifications');
  const data = await response.json();
  renderCertifications(data);
};

const fetchTerms = async () => {
  const response = await fetch('/api/terms');
  const data = await response.json();
  termsInput.value = data.terms;
};

pendingContainer.addEventListener('click', async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLButtonElement)) return;
  const action = target.dataset.action;
  const id = target.dataset.id;
  if (!action || !id) return;

  const response = await fetchWithAuth(`/api/users/${id}/${action}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ performed_by: getAdminName() || 'admin' }),
  });
  if (response.ok) {
    await fetchPending();
    await fetchAllUsers();
  }
});

certForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(certForm);
  const payload = Object.fromEntries(formData.entries());

  const response = await fetchWithAuth('/api/certifications', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (response.ok) {
    certForm.reset();
    await fetchCertifications();
  }
});

const submitGrant = async (revoke = false) => {
  const formData = new FormData(grantForm);
  const payload = Object.fromEntries(formData.entries());
  payload.user_id = Number(payload.user_id);
  const certId = payload.certification_id;

  if (revoke) {
    const response = await fetchWithAuth(`/api/certifications/${certId}/revoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: payload.user_id, performed_by: getAdminName() || 'admin' }),
    });
    const data = await response.json();
    if (response.ok) {
      setResult(grantResult, 'Certification revoked.', 'success');
    } else {
      setResult(grantResult, data.error || 'Unable to revoke.', 'error');
    }
    return;
  }

  const response = await fetchWithAuth(`/api/certifications/${certId}/grant`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: payload.user_id,
      granted_by: payload.granted_by,
    }),
  });
  const data = await response.json();
  if (response.ok) {
    setResult(grantResult, 'Certification granted.', 'success');
    grantForm.reset();
  } else {
    setResult(grantResult, data.error || 'Unable to grant.', 'error');
  }
};

grantForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  await submitGrant(false);
});

revokeButton.addEventListener('click', async () => {
  await submitGrant(true);
});

termsForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const response = await fetchWithAuth('/api/terms', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ terms: termsInput.value }),
  });
  const data = await response.json();
  if (response.ok) {
    setResult(termsResult, 'Terms updated.', 'success');
  } else {
    setResult(termsResult, data.error || 'Unable to update terms.', 'error');
  }
});

adminAuthForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const token = adminTokenInput.value.trim();
  const adminName = adminNameInput.value.trim();
  if (!token) {
    setResult(adminAuthResult, 'Please enter a token.', 'error');
    return;
  }
  if (!adminName) {
    setResult(adminAuthResult, 'Please enter your name.', 'error');
    return;
  }
  const response = await fetchWithAuth('/api/admin/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, admin_name: adminName }),
  });
  if (response.ok) {
    setToken(token);
    setAdminName(adminName);
    setResult(adminAuthResult, 'Admin session started.', 'success');
    await fetchPending();
    await fetchAllUsers();
    await fetchAnalytics();
  } else {
    const data = await response.json();
    setResult(adminAuthResult, data.error || 'Unable to authenticate.', 'error');
  }
});

adminLogoutButton.addEventListener('click', async () => {
  await fetchWithAuth('/api/admin/logout', { method: 'POST' });
  setResult(adminAuthResult, 'Logged out.', 'success');
});

fetchPending();
fetchAllUsers();
fetchCertifications();
fetchAnalytics();
fetchTerms();

const storedToken = getToken();
if (storedToken) {
  adminTokenInput.value = storedToken;
}
const storedName = getAdminName();
if (storedName) {
  adminNameInput.value = storedName;
}
