/* PULSE — US date input helpers (mm/dd/yyyy) */
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

  function bindDateInputs(root) {
    var scope = root || document;
    scope.querySelectorAll('.date-input-md').forEach(function (input) {
      if (input.dataset.pulseDateBound === '1') return;
      input.dataset.pulseDateBound = '1';
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
