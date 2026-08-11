/* PULSE — US date input helpers (mm/dd/yyyy) with calendar picker */
window.PulseDates = (function () {
  var US_RE = /^(0[1-9]|1[0-2])\/(0[1-9]|[12]\d|3[01])\/(\d{4})$/;
  var ISO_RE = /^(\d{4})-(\d{2})-(\d{2})$/;

  function pad2(n) {
    return String(n).padStart(2, '0');
  }

  function buildDate(year, month, day) {
    var date = new Date(year, month - 1, day);
    if (
      date.getFullYear() !== year ||
      date.getMonth() !== month - 1 ||
      date.getDate() !== day
    ) {
      return null;
    }
    date.setHours(0, 0, 0, 0);
    return date;
  }

  function parseDate(str) {
    if (!str) return null;
    var text = String(str).trim();
    if (!text) return null;

    var iso = text.match(ISO_RE);
    if (iso) {
      return buildDate(Number(iso[1]), Number(iso[2]), Number(iso[3]));
    }

    var us = text.match(US_RE);
    if (us) {
      return buildDate(Number(us[3]), Number(us[1]), Number(us[2]));
    }

    return null;
  }

  function formatUsDate(date) {
    if (!(date instanceof Date) || isNaN(date.getTime())) return '';
    return pad2(date.getMonth() + 1) + '/' + pad2(date.getDate()) + '/' + date.getFullYear();
  }

  function isoToUs(str) {
    var parsed = parseDate(str);
    return parsed ? formatUsDate(parsed) : '';
  }

  function usToIso(str) {
    var parsed = parseDate(str);
    if (!parsed) return '';
    return parsed.getFullYear() + '-' + pad2(parsed.getMonth() + 1) + '-' + pad2(parsed.getDate());
  }

  function formatDisplay(str) {
    return isoToUs(str) || (str ? String(str) : '');
  }

  function maskInput(value) {
    var digits = String(value || '').replace(/\D/g, '').slice(0, 8);
    if (digits.length <= 2) return digits;
    if (digits.length <= 4) return digits.slice(0, 2) + '/' + digits.slice(2);
    return digits.slice(0, 2) + '/' + digits.slice(2, 4) + '/' + digits.slice(4);
  }

  function ensureDateFieldWrap(input) {
    var parent = input.parentElement;
    if (parent && parent.classList.contains('pulse-date-field')) {
      return parent;
    }

    var wrap = document.createElement('div');
    wrap.className = 'pulse-date-field flatpickr';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    input.setAttribute('data-input', '');

    var toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'pulse-date-field__toggle';
    toggle.setAttribute('data-toggle', '');
    toggle.setAttribute('aria-label', 'Open calendar');
    toggle.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="4" width="18" height="18" rx="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>';
    wrap.appendChild(toggle);
    return wrap;
  }

  function bindPlainDateInput(input) {
    input.setAttribute('placeholder', input.getAttribute('placeholder') || 'mm/dd/yyyy');
    input.setAttribute('inputmode', 'numeric');
    input.setAttribute('maxlength', '10');
    input.setAttribute('autocomplete', 'off');

    if (input.value && ISO_RE.test(input.value)) {
      input.value = isoToUs(input.value);
    }

    input.addEventListener('input', function () {
      var start = input.selectionStart;
      var prevLen = input.value.length;
      input.value = maskInput(input.value);
      var nextLen = input.value.length;
      var nextPos = Math.max(0, (start || 0) + (nextLen - prevLen));
      if (input.setSelectionRange) {
        input.setSelectionRange(nextPos, nextPos);
      }
    });

    input.addEventListener('blur', function () {
      if (!input.value) return;
      if (!parseDate(input.value)) {
        input.setCustomValidity('Enter a valid date as mm/dd/yyyy.');
      } else {
        input.setCustomValidity('');
        input.value = formatUsDate(parseDate(input.value));
      }
    });
  }

  function bindPickerDateInput(input) {
    var wrap = ensureDateFieldWrap(input);
    input.setAttribute('placeholder', input.getAttribute('placeholder') || 'mm/dd/yyyy');
    input.setAttribute('autocomplete', 'off');

    if (input.value && ISO_RE.test(input.value)) {
      input.value = isoToUs(input.value);
    }

    var options = {
      wrap: true,
      dateFormat: 'm/d/Y',
      allowInput: true,
      clickOpens: true,
      disableMobile: false,
    };

    if (input.dataset.maxToday === 'true') {
      options.maxDate = 'today';
    }

    options.onChange = function () {
      input.dispatchEvent(new Event('change', { bubbles: true }));
      input.dispatchEvent(new Event('input', { bubbles: true }));
    };

    var picker = flatpickr(wrap, options);

    input.addEventListener('blur', function () {
      if (!input.value) {
        input.setCustomValidity('');
        return;
      }
      if (!parseDate(input.value)) {
        input.setCustomValidity('Enter a valid date as mm/dd/yyyy.');
      } else {
        input.setCustomValidity('');
      }
    });

    input.addEventListener('change', function () {
      input.dispatchEvent(new Event('input', { bubbles: true }));
    });

    return picker;
  }

  function bindDateInputs(root) {
    var scope = root || document;
    scope.querySelectorAll('.date-input-md').forEach(function (input) {
      if (input.dataset.pulseDateBound === '1') return;
      input.dataset.pulseDateBound = '1';

      if (typeof flatpickr !== 'undefined') {
        bindPickerDateInput(input);
      } else {
        bindPlainDateInput(input);
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    bindDateInputs(document);
  });

  return {
    parseDate: parseDate,
    formatUsDate: formatUsDate,
    isoToUs: isoToUs,
    usToIso: usToIso,
    formatDisplay: formatDisplay,
    maskInput: maskInput,
    bindDateInputs: bindDateInputs,
  };
})();
