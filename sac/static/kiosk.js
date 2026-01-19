const swipeForm = document.getElementById('swipe-form');
const swipeResult = document.getElementById('swipe-result');
const certSelect = document.getElementById('certification-select');
const onboardForm = document.getElementById('onboard-form');
const onboardResult = document.getElementById('onboard-result');
const termsBox = document.getElementById('terms-box');

const setResult = (element, message, status) => {
  element.textContent = message;
  element.className = `result ${status || ''}`.trim();
};

const loadCertifications = async () => {
  const response = await fetch('/api/certifications');
  const data = await response.json();
  data.forEach((cert) => {
    const option = document.createElement('option');
    option.value = cert.id;
    option.textContent = `${cert.name} (${cert.scope})`;
    certSelect.appendChild(option);
  });
};

const loadTerms = async () => {
  const response = await fetch('/api/terms');
  const data = await response.json();
  termsBox.textContent = data.terms;
};

swipeForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(swipeForm);
  const payload = Object.fromEntries(formData.entries());
  if (!payload.certification_id) {
    delete payload.certification_id;
  } else {
    payload.certification_id = Number(payload.certification_id);
  }

  const response = await fetch('/api/swipe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (response.ok && data.result === 'approved') {
    setResult(swipeResult, `Approved ✅ (User #${data.user_id ?? 'unknown'})`, 'success');
  } else {
    setResult(swipeResult, 'Denied ❌', 'error');
  }
  swipeForm.reset();
});

onboardForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(onboardForm);
  const payload = Object.fromEntries(formData.entries());
  payload.terms_accepted = formData.get('terms_accepted') === 'on';

  const response = await fetch('/api/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (response.ok) {
    setResult(onboardResult, 'Thanks! Your account is pending approval.', 'success');
    onboardForm.reset();
  } else {
    setResult(onboardResult, data.error || 'Unable to create account.', 'error');
  }
});

loadCertifications();
loadTerms();
