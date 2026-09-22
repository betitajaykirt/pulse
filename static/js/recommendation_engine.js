/**
 * PULSE recommendation resolver for Leaflet's client-side proximity clusters.
 *
 * Clinical copy stays server-owned in recommendations_matrix.json. The browser
 * only groups, escalates, sorts, and de-duplicates structured bundles.
 */
(function (global) {
  'use strict';

  var STATUS_RANK = { Suspected: 1, Probable: 2, Confirmed: 3 };
  var CATEGORY_RANK = { 'Category I': 0, 'Category II': 1 };

  function normalizedStatus(value) {
    var status = String(value || '').trim().toLowerCase();
    if (status === 'confirmed') return 'Confirmed';
    if (status === 'probable') return 'Probable';
    return 'Suspected';
  }

  function mergeActions(actions) {
    var byCode = Object.create(null);
    (actions || []).forEach(function (action) {
      if (!action || !action.code) return;
      if (!byCode[action.code]) {
        byCode[action.code] = {
          code: action.code,
          text_en: action.text_en || '',
          text_local: action.text_local || '',
          target_units: (action.target_units || []).slice(),
        };
        return;
      }
      (action.target_units || []).forEach(function (target) {
        if (byCode[action.code].target_units.indexOf(target) === -1) {
          byCode[action.code].target_units.push(target);
        }
      });
    });
    return Object.keys(byCode).map(function (code) { return byCode[code]; });
  }

  function caseBundle(caseItem) {
    return caseItem && caseItem.recommendation_bundle
      ? caseItem.recommendation_bundle
      : null;
  }

  function resolveClusterRecommendations(casesArray) {
    var groups = Object.create(null);
    (casesArray || []).forEach(function (caseItem) {
      var bundle = caseBundle(caseItem);
      if (!bundle || !bundle.disease) return;
      if (!groups[bundle.disease]) groups[bundle.disease] = [];
      groups[bundle.disease].push({ caseItem: caseItem, bundle: bundle });
    });

    var cards = Object.keys(groups).map(function (disease) {
      var entries = groups[disease];
      entries.sort(function (left, right) {
        return STATUS_RANK[normalizedStatus(right.bundle.highest_status)] -
          STATUS_RANK[normalizedStatus(left.bundle.highest_status)];
      });
      var primary = entries[0].bundle;
      var caseCount = entries.reduce(function (sum, entry) {
        var count = Number(entry.caseItem.case_count || 1);
        return sum + (isFinite(count) && count > 0 ? count : 1);
      }, 0);
      var clusterActions = [];
      entries.forEach(function (entry) {
        clusterActions = clusterActions.concat(entry.bundle.cluster_actions || []);
      });
      var actions = mergeActions((primary.actions || []).concat(clusterActions));
      var targets = [];
      actions.forEach(function (action) {
        (action.target_units || []).forEach(function (target) {
          if (targets.indexOf(target) === -1) targets.push(target);
        });
      });
      return {
        disease: primary.disease,
        disease_code: primary.disease_code || '',
        category: primary.category,
        highest_status: normalizedStatus(primary.highest_status),
        case_count: caseCount,
        is_cluster: true,
        actions: actions,
        target_units: targets.sort(),
      };
    });

    cards.sort(function (left, right) {
      var categoryDelta = (CATEGORY_RANK[left.category] || 0) -
        (CATEGORY_RANK[right.category] || 0);
      if (categoryDelta) return categoryDelta;
      var statusDelta = STATUS_RANK[right.highest_status] - STATUS_RANK[left.highest_status];
      if (statusDelta) return statusDelta;
      if (right.case_count !== left.case_count) return right.case_count - left.case_count;
      return left.disease.localeCompare(right.disease);
    });

    var summary = [];
    cards.forEach(function (card) { summary = summary.concat(card.actions); });
    return {
      has_category_i: cards.some(function (card) { return card.category === 'Category I'; }),
      is_cluster: (casesArray || []).length > 1,
      disease_cards: cards,
      field_action_summary: mergeActions(summary),
    };
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function recommendationCards(bundle) {
    if (!bundle) return [];
    if (Array.isArray(bundle.disease_cards)) return bundle.disease_cards;
    return bundle.disease ? [bundle] : [];
  }

  function renderAction(action) {
    var targets = (action.target_units || []).map(function (target) {
      return '<span class="rec-target-tag">' + escapeHtml(target) + '</span>';
    }).join('');
    return '<li class="rec-action-item">'
      + '<div class="rec-action-item__en">' + escapeHtml(action.text_en) + '</div>'
      + '<div class="rec-action-item__local">' + escapeHtml(action.text_local) + '</div>'
      + (targets ? '<div class="rec-target-list">' + targets + '</div>' : '')
      + '</li>';
  }

  function renderRecommendationCards(bundle, options) {
    options = options || {};
    var cards = recommendationCards(bundle);
    if (!cards.length) {
      return '<div class="rec-empty">No protocol is available for this disease identity.</div>';
    }
    var hasCategoryI = bundle.has_category_i ||
      cards.some(function (card) { return card.category === 'Category I'; });
    var html = '<div class="recommendation-engine">';
    if (hasCategoryI) {
      html += '<div class="rec-priority-banner">'
        + '<strong>Category I priority</strong>'
        + '<span>Immediately reportable to the CHO surveillance unit.</span>'
        + '</div>';
    }
    cards.forEach(function (card) {
      var status = normalizedStatus(card.highest_status);
      html += '<article class="rec-disease-card rec-disease-card--'
        + (card.category === 'Category I' ? 'category-i' : 'category-ii') + '">';
      html += '<header class="rec-disease-card__head"><div>';
      html += '<strong class="rec-disease-card__title">' + escapeHtml(card.disease) + '</strong>';
      html += '<span class="rec-category-label">' + escapeHtml(card.category) + '</span></div>';
      html += '<div class="rec-badges"><span class="rec-status-badge rec-status-badge--'
        + status.toLowerCase() + '">' + escapeHtml(status.toUpperCase()) + '</span>';
      if (card.is_cluster || bundle.is_cluster) {
        html += '<span class="rec-cluster-badge">CLUSTER ALERT</span>';
      }
      html += '</div></header>';
      html += '<div class="rec-case-count">' + Number(card.case_count || 1)
        + ' case' + (Number(card.case_count || 1) === 1 ? '' : 's') + ' in selection</div>';
      html += '<ul class="rec-action-list">'
        + (card.actions || []).map(renderAction).join('') + '</ul>';
      if (options.canManage) {
        html += '<button type="button" class="nc-btn nc-btn--outline nc-btn--sm rec-edit-button"'
          + ' data-recommendation-edit="' + escapeHtml(card.disease) + '"'
          + ' data-recommendation-status="' + escapeHtml(status.toLowerCase()) + '">'
          + 'Edit &amp; Approve</button>';
      }
      html += '</article>';
    });
    if (options.showSummary && Array.isArray(bundle.field_action_summary)
        && bundle.field_action_summary.length) {
      html += '<section class="rec-field-summary"><h4>BHW Field Action Summary</h4>'
        + '<p>Combined and de-duplicated across pathogens.</p><ul class="rec-action-list">'
        + bundle.field_action_summary.map(renderAction).join('')
        + '</ul></section>';
    }
    return html + '</div>';
  }

  global.PulseRecommendationEngine = {
    resolveClusterRecommendations: resolveClusterRecommendations,
    mergeActions: mergeActions,
    renderRecommendationCards: renderRecommendationCards,
  };
  global.resolveClusterRecommendations = resolveClusterRecommendations;
})(window);
