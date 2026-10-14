const $ = (selector, parent = document) => parent.querySelector(selector);
const $$ = (selector, parent = document) => [...parent.querySelectorAll(selector)];
const persianDigits = value => String(value).replace(/\d/g, digit => '۰۱۲۳۴۵۶۷۸۹'[digit]);
const formatToman = value => (value >= 1000000
  ? `${persianDigits(Number((value / 1000000).toFixed(1)))} میلیون تومان`
  : `${new Intl.NumberFormat('fa-IR').format(Math.round(value))} تومان`);

function openImportModal() {
  $('#import-modal').hidden = false;
  $('input[name="merchant_id"]', $('#score-form')).focus();
}
function closeImportModal() { $('#import-modal').hidden = true; }
const VIEW_TEXT = {
  overview: ['صبح بخیر، مدیر', 'تصویر امروز کسب‌وکارهای تحت پوشش را یک‌جا ببینید.'],
  analysis: ['تحلیل نقدینگی', 'دوره‌های کسری نقدینگی را از روی تراکنش‌های خام مرچنت بررسی کنید.'],
  history: ['تاریخچه تصمیم‌ها', 'تصمیم‌های اعتباری ثبت‌شده برای هر مرچنت را مرور کنید.'],
  network: ['اکوسیستم Teal', 'یک موتور تصمیم‌گیری، چند مسیر شفاف برای تأمین اعتبار.'],
};
const formatDate = value => new Intl.DateTimeFormat('fa-IR', { dateStyle: 'medium' }).format(new Date(value));
const formatDateTime = value => new Intl.DateTimeFormat('fa-IR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
const formatNumber = value => new Intl.NumberFormat('fa-IR').format(value);

function selectView(view) {
  if (view === 'import') { openImportModal(); return; }
  $$('.nav-item').forEach(item => item.classList.toggle('active', item.dataset.view === view));
  $$('.view').forEach(section => { section.hidden = section.id !== `view-${view}`; });
  const [title, subtitle] = VIEW_TEXT[view];
  $('.page-heading h1').textContent = title;
  $('.page-heading .muted').textContent = subtitle;
  if (view === 'network') loadNetworkOverview();
}

async function apiRequest(path, { apiKey, body } = {}) {
  const headers = {};
  if (apiKey) headers['X-API-Key'] = apiKey;
  if (body) headers['Content-Type'] = 'application/json';
  const response = await fetch(path, { method: body ? 'POST' : 'GET', headers, body: body && JSON.stringify(body) });
  if (!response.ok) {
    let detail = '';
    try { detail = (await response.json()).detail; } catch { /* non-JSON error body */ }
    if (response.status === 401 || response.status === 403) detail = 'کلید API نامعتبر است.';
    else if (response.status === 422) detail = 'ساختار داده ورودی معتبر نیست.';
    throw new Error(typeof detail === 'string' && detail ? detail : 'درخواست انجام نشد.');
  }
  return response.json();
}

function setStatus(form, message, ok = false) {
  const status = $('.form-status', form);
  status.style.color = ok ? '#3a9d73' : '#d66355';
  status.textContent = message;
}

async function withSubmitState(form, label, task) {
  const submit = $('button[type="submit"]', form);
  const original = submit.textContent;
  submit.disabled = true;
  submit.textContent = label;
  setStatus(form, '');
  try { await task(); } catch (error) { setStatus(form, error.message); } finally { submit.disabled = false; submit.textContent = original; }
}

function addCell(row, text) { const cell = document.createElement('td'); cell.textContent = text; row.append(cell); return cell; }

const DEMO_TRANSACTIONS = [
  { timestamp: '2026-09-01T10:00:00', amount: 12000000, source: 'pos' },
  { timestamp: '2026-09-02T10:00:00', amount: 15000000, source: 'marketplace' },
  { timestamp: '2026-09-03T10:00:00', amount: -4000000, source: 'psp' },
];

async function loadNetworkOverview() {
  const list = $('#network-providers');
  list.replaceChildren();
  const loading = document.createElement('p');
  loading.className = 'empty-state';
  loading.textContent = 'در حال دریافت پیشنهادها…';
  list.append(loading);
  try {
    const result = await apiRequest('/aggregate/offers', { body: { merchant_id: 'merchant-1042', transactions: DEMO_TRANSACTIONS.map(item => ({ ...item, merchant_id: 'merchant-1042' })) } });
    const { decision, offers } = result;
    $('#network-risk').textContent = persianDigits(Number(decision.risk_score).toFixed(2));
    $('#network-limit').textContent = formatToman(decision.recommended_credit_limit);
    $('#network-repayment').textContent = decision.repayment_model === 'fixed' ? 'اقساط ثابت' : 'درصدی از فروش';
    $('#network-match-count').textContent = formatNumber(offers.filter(offer => offer.eligible).length);
    list.replaceChildren();
    offers.forEach((offer, index) => {
      const card = document.createElement('div');
      card.className = `provider-card ${offer.eligible ? 'provider-match' : 'provider-muted'}`;
      const identity = document.createElement('div');
      identity.className = 'provider-identity';
      const rank = document.createElement('span');
      rank.className = 'provider-rank';
      rank.textContent = persianDigits(String(index + 1).padStart(2, '0'));
      const name = document.createElement('strong');
      name.textContent = offer.provider_name;
      identity.append(rank, name);
      const details = document.createElement('div');
      details.className = 'provider-details';
      const amount = document.createElement('strong');
      amount.textContent = offer.eligible ? formatToman(offer.offered_credit_limit) : '—';
      const reason = document.createElement('span');
      reason.textContent = offer.eligible ? `تناسب ${persianDigits(Math.round(offer.fit_score * 100))}٪ · ${offer.repayment_model === 'fixed' ? 'اقساط ثابت' : 'درصدی از فروش'}` : offer.reason;
      details.append(amount, reason);
      const status = document.createElement('span');
      status.className = `provider-status ${offer.eligible ? 'match' : 'no-match'}`;
      status.textContent = offer.eligible ? 'مناسب' : 'نامتناسب';
      card.append(identity, details, status);
      list.append(card);
    });
  } catch (error) {
    list.replaceChildren();
    const message = document.createElement('p');
    message.className = 'empty-state';
    message.textContent = error.message;
    list.append(message);
  }
}

$('#refresh-network').addEventListener('click', loadNetworkOverview);

$('#analysis-form').addEventListener('submit', event => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = new FormData(form);
  const merchantId = data.get('merchant_id').trim();
  let transactions;
  try { transactions = JSON.parse(data.get('transactions')); } catch { setStatus(form, 'داده تراکنش باید JSON معتبر باشد.'); return; }
  if (!Array.isArray(transactions) || !transactions.length) { setStatus(form, 'حداقل یک تراکنش لازم است.'); return; }
  withSubmitState(form, 'در حال تحلیل…', async () => {
    const result = await apiRequest('/cashflow/analyze', {
      apiKey: data.get('api_key'),
      body: { merchant_id: merchantId, transactions: transactions.map(item => ({ ...item, merchant_id: merchantId })) },
    });
    $('#an-events').textContent = formatNumber(result.gap_events.length);
    $('#an-days').textContent = formatNumber(result.total_days_in_gap);
    $('#an-max').textContent = formatToman(result.max_gap_depth);
    $('#an-freq').textContent = formatNumber(Number(result.gap_frequency_per_month.toFixed(2)));
    const rows = $('#an-rows');
    rows.replaceChildren();
    result.gap_events.forEach(gap => {
      const row = document.createElement('tr');
      addCell(row, formatDate(gap.start_date));
      addCell(row, formatDate(gap.end_date));
      addCell(row, `${formatNumber(gap.duration_days)} روز`);
      addCell(row, formatToman(gap.max_deficit));
      rows.append(row);
    });
    $('#an-empty').hidden = result.gap_events.length > 0;
    $('.table-wrap', $('#analysis-result')).hidden = result.gap_events.length === 0;
    $('#analysis-result').hidden = false;
    setStatus(form, 'تحلیل انجام شد.', true);
  });
});

const RISK_CHIP = score => (score < 0.3 ? ['کم‌ریسک', 'ok'] : score < 0.6 ? ['ریسک متوسط', 'warn'] : ['پرریسک', 'bad']);

$('#history-form').addEventListener('submit', event => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = new FormData(form);
  const merchantId = data.get('merchant_id').trim();
  withSubmitState(form, 'در حال دریافت…', async () => {
    const records = await apiRequest(`/merchants/${encodeURIComponent(merchantId)}/history`, { apiKey: data.get('api_key') });
    const rows = $('#hist-rows');
    rows.replaceChildren();
    records.forEach(record => {
      const row = document.createElement('tr');
      addCell(row, formatDateTime(record.created_at));
      const scoreCell = addCell(row, `${persianDigits(Number(record.risk_score).toFixed(2))} `);
      const [label, tone] = RISK_CHIP(record.risk_score);
      const chip = document.createElement('span');
      chip.className = `chip ${tone}`;
      chip.textContent = label;
      scoreCell.append(chip);
      addCell(row, formatToman(record.recommended_credit_limit));
      addCell(row, record.repayment_model === 'fixed' ? 'اقساط ثابت' : 'درصدی از فروش');
      rows.append(row);
    });
    $('#hist-empty').hidden = records.length > 0;
    $('.table-wrap', $('#history-result')).hidden = records.length === 0;
    $('#history-result').hidden = false;
    if (records.length) setStatus(form, `${formatNumber(records.length)} تصمیم یافت شد.`, true);
  });
});

$$('[data-view]').forEach(button => button.addEventListener('click', () => selectView(button.dataset.view)));
$$('.modal-close, .modal-cancel').forEach(button => button.addEventListener('click', closeImportModal));
$('#import-modal').addEventListener('click', event => { if (event.target === $('#import-modal')) closeImportModal(); });

document.addEventListener('keydown', event => { if (event.key === 'Escape') closeImportModal(); });

$('#score-form').addEventListener('submit', async event => {
  event.preventDefault();
  const form = event.currentTarget;
  const formData = new FormData(form);
  const status = $('.form-status', form);
  const submit = $('button[type="submit"]', form);
  let transactions;
  try { transactions = JSON.parse(formData.get('transactions')); } catch { status.textContent = 'داده تراکنش باید JSON معتبر باشد.'; return; }
  submit.disabled = true;
  submit.textContent = 'در حال مقایسه…';
  status.textContent = '';
  try {
    const headers = { 'Content-Type': 'application/json' };
    if (formData.get('api_key')) headers['X-API-Key'] = formData.get('api_key');
    const response = await fetch('/aggregate/offers', { method: 'POST', headers, body: JSON.stringify({ merchant_id: formData.get('merchant_id'), transactions: transactions.map(item => ({ ...item, merchant_id: formData.get('merchant_id') })) }) });
    if (!response.ok) throw new Error((await response.json()).detail || 'صدور تصمیم انجام نشد.');
    const payload = await response.json();
    const decision = payload.decision;
    $('#merchant-id').textContent = decision.merchant_id;
    $('#risk-score').textContent = persianDigits(Number(decision.risk_score).toFixed(2));
    $('#credit-limit').textContent = formatToman(decision.recommended_credit_limit);
    $('#repayment-model').textContent = decision.repayment_model === 'fixed' ? 'اقساط ثابت' : 'درصدی از فروش';
    const offerList = $('#offer-list');
    offerList.replaceChildren();
    payload.offers.forEach(offer => {
      const item = document.createElement('div');
      item.className = `offer-row ${offer.eligible ? 'eligible' : 'ineligible'}`;
      const name = document.createElement('strong');
      name.textContent = offer.provider_name;
      const details = document.createElement('span');
      details.textContent = offer.eligible ? `${formatToman(offer.offered_credit_limit)} · ${offer.repayment_model === 'fixed' ? 'اقساط ثابت' : 'درصدی از فروش'}` : offer.reason;
      item.append(name, details);
      offerList.append(item);
    });
    $('#offer-results').hidden = false;
    status.style.color = '#3a9d73';
    status.textContent = 'تصمیم با موفقیت صادر شد.';
    setTimeout(closeImportModal, 800);
  } catch (error) { status.style.color = '#d66355'; status.textContent = error.message; }
  finally { submit.disabled = false; submit.textContent = 'مقایسه پیشنهادهای اعتبار'; }
});

fetch('/health').then(response => { if (!response.ok) throw new Error(); }).catch(() => { $('.status-dot span').textContent = 'اتصال نیاز به بررسی دارد'; $('.status-dot i').style.background = '#e5ad4c'; });
