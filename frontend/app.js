const $ = (selector, parent = document) => parent.querySelector(selector);
const $$ = (selector, parent = document) => [...parent.querySelectorAll(selector)];
const persianDigits = value => String(value).replace(/\d/g, digit => '۰۱۲۳۴۵۶۷۸۹'[digit]);
const formatToman = value => `${persianDigits(Math.round(value / 1000000))} میلیون تومان`;

function openImportModal() {
  $('#import-modal').hidden = false;
  $('input[name="merchant_id"]', $('#score-form')).focus();
}
function closeImportModal() { $('#import-modal').hidden = true; }
function selectView(view) {
  if (view === 'import') { openImportModal(); return; }
  $$('.nav-item').forEach(item => item.classList.toggle('active', item.dataset.view === view));
  if (view !== 'overview') {
    const labels = { analysis: 'تحلیل نقدینگی', history: 'تاریخچه تصمیم‌ها' };
    $('.page-heading h1').textContent = labels[view] || 'نمای کلی';
    $('.page-heading .muted').textContent = 'این بخش در کنار داشبورد اصلی، تصویر دقیق‌تری از داده‌ها می‌دهد.';
  } else {
    $('.page-heading h1').textContent = 'صبح بخیر، مدیر';
    $('.page-heading .muted').textContent = 'تصویر امروز کسب‌وکارهای تحت پوشش را یک‌جا ببینید.';
  }
}

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
