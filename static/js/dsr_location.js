/**
 * dsr_location.js – Cascading District → Mandal → Village/City selector
 * for the DSR (Daily Status Report) forms.
 */

(function () {
  'use strict';

  let AP_LOCATIONS = {};

  function loadLocations(callback) {
    fetch('/static/data/ap_locations.json')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        AP_LOCATIONS = data;
        callback();
      })
      .catch(function () {
        console.warn('DSR: could not load ap_locations.json');
        callback();
      });
  }

  function populateDistricts(selectEl, selectedDistrict) {
    selectEl.innerHTML = '<option value="">-- Select District --</option>';
    var districts = Object.keys(AP_LOCATIONS).sort();
    districts.forEach(function (d) {
      var opt = document.createElement('option');
      opt.value = d;
      opt.textContent = d;
      if (d === selectedDistrict) opt.selected = true;
      selectEl.appendChild(opt);
    });
  }

  function populateMandals(districtSelectEl, mandalSelectEl, selectedMandal) {
    var district = districtSelectEl.value;
    mandalSelectEl.innerHTML = '<option value="">-- Select Mandal --</option>';
    if (district && AP_LOCATIONS[district]) {
      AP_LOCATIONS[district].forEach(function (m) {
        var opt = document.createElement('option');
        opt.value = m;
        opt.textContent = m;
        if (m === selectedMandal) opt.selected = true;
        mandalSelectEl.appendChild(opt);
      });
    }
  }

  function updatePlaceField(districtEl, mandalEl, villageEl, placeHiddenEl) {
    var parts = [villageEl.value, mandalEl.value, districtEl.value]
      .map(function (s) { return (s || '').trim(); })
      .filter(Boolean);
    placeHiddenEl.value = parts.join(', ');
  }

  /**
   * Parse a stored place string back into {district, mandal, village}.
   * Supports "village, mandal, district" format written by this module.
   * Falls back gracefully when format is not recognised.
   */
  function parseSavedPlace(savedPlace) {
    if (!savedPlace) return { district: '', mandal: '', village: '' };
    var parts = savedPlace.split(', ');
    if (parts.length >= 2) {
      var candidateDist = parts[parts.length - 1];
      var candidateMandal = parts[parts.length - 2];
      if (AP_LOCATIONS[candidateDist] && AP_LOCATIONS[candidateDist].indexOf(candidateMandal) !== -1) {
        return {
          district: candidateDist,
          mandal: candidateMandal,
          village: parts.slice(0, -2).join(', ')
        };
      }
      // Try just matching district
      if (AP_LOCATIONS[candidateDist]) {
        return { district: candidateDist, mandal: '', village: parts.slice(0, -1).join(', ') };
      }
    }
    // Unrecognised – put everything in village
    return { district: '', mandal: '', village: savedPlace };
  }

  /**
   * Initialise one location widget.
   * @param {object} opts
   *   districtId  – id of the district <select>
   *   mandalId    – id of the mandal <select>
   *   villageId   – id of the village <input>
   *   placeId     – id of the hidden <input name="place">
   *   savedPlace  – existing stored place string (for edit forms)
   */
  function initWidget(opts) {
    var districtEl = document.getElementById(opts.districtId);
    var mandalEl   = document.getElementById(opts.mandalId);
    var villageEl  = document.getElementById(opts.villageId);
    var placeEl    = document.getElementById(opts.placeId);

    if (!districtEl || !mandalEl || !villageEl || !placeEl) return;

    var pre = parseSavedPlace(opts.savedPlace || '');

    populateDistricts(districtEl, pre.district);
    populateMandals(districtEl, mandalEl, pre.mandal);
    villageEl.value = pre.village;

    districtEl.addEventListener('change', function () {
      populateMandals(districtEl, mandalEl, '');
      updatePlaceField(districtEl, mandalEl, villageEl, placeEl);
    });

    mandalEl.addEventListener('change', function () {
      updatePlaceField(districtEl, mandalEl, villageEl, placeEl);
    });

    villageEl.addEventListener('input', function () {
      updatePlaceField(districtEl, mandalEl, villageEl, placeEl);
    });

    // Sync once on load
    updatePlaceField(districtEl, mandalEl, villageEl, placeEl);
  }

  // Public API
  window.DsrLocation = {
    init: function (widgetConfigs) {
      loadLocations(function () {
        (widgetConfigs || []).forEach(function (cfg) { initWidget(cfg); });
      });
    }
  };
})();
