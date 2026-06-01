/* JBOOK 前端交互 */
(function () {
  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  function initLazyImages() {
    const imgs = qsa('.lazy-img');
    if ('IntersectionObserver' in window) {
      const io = new IntersectionObserver(entries => {
        entries.forEach(e => {
          if (e.isIntersecting) {
            e.target.classList.add('loaded');
            io.unobserve(e.target);
          }
        });
      });
      imgs.forEach(img => { if (img.complete) img.classList.add('loaded'); else io.observe(img); });
    } else imgs.forEach(img => img.classList.add('loaded'));
  }

  function initSearchSuggest() {
    const input = qs('#globalSearchInput');
    const box = qs('#searchSuggest');
    if (!input || !box) return;
    let timer;
    input.addEventListener('input', () => {
      clearTimeout(timer);
      const q = input.value.trim();
      if (q.length < 1) { box.classList.add('d-none'); return; }
      timer = setTimeout(() => {
        fetch('/api/search-suggest/?q=' + encodeURIComponent(q))
          .then(r => r.json())
          .then(data => {
            if (!data.items || !data.items.length) { box.classList.add('d-none'); return; }
            box.innerHTML = data.items.map(it =>
              `<a href="/books/?q=${encodeURIComponent(it.book_name)}">${it.book_name} · ${it.author}</a>`
            ).join('');
            box.classList.remove('d-none');
          });
      }, 250);
    });
    document.addEventListener('click', e => {
      if (!box.contains(e.target) && e.target !== input) box.classList.add('d-none');
    });
  }

  window.initPriceSlider = function (min, max) {
    const rMin = qs('#priceMinRange');
    const rMax = qs('#priceMaxRange');
    if (!rMin || !rMax) return;
    const sync = () => {
      let a = parseInt(rMin.value, 10);
      let b = parseInt(rMax.value, 10);
      if (a > b) [a, b] = [b, a];
      qs('#min_price').value = a;
      qs('#max_price').value = b;
      qs('#priceMinLabel').textContent = a;
      qs('#priceMaxLabel').textContent = b;
    };
    rMin.addEventListener('input', sync);
    rMax.addEventListener('input', sync);
    sync();
  };

  window.initSellForm = function () {
    const btnIsbn = qs('#btnIsbnLookup');
    const btnPrice = qs('#btnSuggestPrice');
    const cover = qs('#cover_img');
    const preview = qs('#coverPreview');
    const form = qs('#sellForm');

    if (btnIsbn) btnIsbn.addEventListener('click', () => {
      const isbn = qs('#isbn').value.trim();
      if (!isbn) return;
      fetch('/api/isbn/?isbn=' + encodeURIComponent(isbn))
        .then(r => r.json())
        .then(res => {
          if (!res.success) { alert(res.message || 'Not found'); return; }
          const d = res.data;
          ['book_name','author','publisher','pub_year','original_price','book_desc'].forEach(k => {
            const el = qs('#' + k);
            if (el && d[k] !== undefined) el.value = d[k];
          });
          if (d.cat_id) qs('#cat_id').value = d.cat_id;
        });
    });

    if (btnPrice) btnPrice.addEventListener('click', suggestPrice);
    ['original_price','pub_year','cat_id','quality'].forEach(id => {
      const el = qs('#' + id);
      if (el) el.addEventListener('change', suggestPrice);
    });

    if (cover && preview) cover.addEventListener('change', () => {
      const f = cover.files[0];
      if (!f) return;
      if (f.size > 2 * 1024 * 1024) { alert('Max 2MB'); cover.value = ''; return; }
      preview.src = URL.createObjectURL(f);
      preview.classList.remove('d-none');
    });

    if (form) form.addEventListener('submit', () => {
      const btn = qs('#btnSubmit');
      if (btn) { btn.disabled = true; btn.querySelector('.submit-text').textContent = '提交中...'; }
    });
  };

  function suggestPrice() {
    const params = new URLSearchParams({
      original_price: qs('#original_price')?.value || 50,
      pub_year: qs('#pub_year')?.value || 2020,
      cat_id: qs('#cat_id')?.value || 1,
      quality: qs('#quality')?.value || 3,
    });
    fetch('/api/suggest-price/?' + params)
      .then(r => r.json())
      .then(data => {
        if (!data.success) return;
        const el = qs('#second_price');
        if (el) el.value = data.suggested_price;
        const hint = qs('#priceHint');
        if (hint) hint.textContent = data.hint || ('¥' + data.suggested_price);
      });
  }
  window.suggestPrice = suggestPrice;

  window.initMessagePoll = function (partnerId) {
    if (!partnerId) return;
    const box = qs('#chatMessages');
    setInterval(() => {
      fetch('/trade/messages/poll/?with=' + partnerId)
        .then(r => r.json())
        .then(data => {
          if (!box || !data.messages) return;
          box.innerHTML = data.messages.map(m =>
            `<div class="chat-bubble ${m.from_me ? 'me' : 'other'}">${m.content}<div class="small opacity-75">${m.time}</div></div>`
          ).join('');
          box.scrollTop = box.scrollHeight;
        });
    }, 5000);
  };

  function initFormValidation() {
    qsa('form[novalidate]').forEach(form => {
      form.addEventListener('submit', e => {
        if (!form.checkValidity()) {
          e.preventDefault();
          e.stopPropagation();
        }
        form.classList.add('was-validated');
      });
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    initLazyImages();
    initSearchSuggest();
    initFormValidation();
  });
})();
