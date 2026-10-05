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
  const form = new FormData(event.currentTarget);
  const status = $('.form-status');
  const submit = $('button[type="submit"]', event.currentTarget);
  let transactions;
  try { transactions = JSON.parse(form.get('transactions')); } catch { status.textContent = 'داده تراکنش باید JSON معتبر باشد.'; return; }
  submit.disabled = true;
  submit.textContent = 'در حال تحلیل…';
  status.textContent = '';
  try {
    const headers = { 'Content-Type': 'application/json' };
    if (form.get('api_key')) headers['X-API-Key'] = form.get('api_key');
    const response = await fetch('/score/transactions', { method: 'POST', headers, body: JSON.stringify({ merchant_id: form.get('merchant_id'), transactions: transactions.map(item => ({ ...item, merchant_id: form.get('merchant_id') })) }) });
    if (!response.ok) throw new Error((await response.json()).detail || 'صدور تصمیم انجام نشد.');
    const decision = await response.json();
    $('#merchant-id').textContent = decision.merchant_id;
    $('#risk-score').textContent = persianDigits(Number(decision.risk_score).toFixed(2));
    $('#credit-limit').textContent = formatToman(decision.recommended_credit_limit);
    $('#repayment-model').textContent = decision.repayment_model === 'fixed' ? 'اقساط ثابت' : 'درصدی از فروش';
    status.style.color = '#3a9d73';
    status.textContent = 'تصمیم با موفقیت صادر شد.';
    setTimeout(closeImportModal, 800);
  } catch (error) { status.style.color = '#d66355'; status.textContent = error.message; }
  finally { submit.disabled = false; submit.textContent = 'تحلیل و صدور تصمیم'; }
});

fetch('/health').then(response => { if (!response.ok) throw new Error(); }).catch(() => { $('.status-dot span').textContent = 'اتصال نیاز به بررسی دارد'; $('.status-dot i').style.background = '#e5ad4c'; });
