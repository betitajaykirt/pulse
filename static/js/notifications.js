(function() {
    const NOTIFICATIONS_API_URL = '/dashboard/api/notifications/';
    const POLL_INTERVAL = 15000;

    let notifiedIds = new Set();
    let modalQueue = [];
    let isModalActive = false;

    const bellBtn = document.getElementById('notification-bell-btn');
    const badge = document.getElementById('notification-badge');
    const dropdown = document.getElementById('notification-dropdown');
    const listContainer = document.getElementById('notification-list');
    const toastContainer = document.getElementById('toast-container');

    if (!bellBtn) return;

    bellBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isExpanded = bellBtn.getAttribute('aria-expanded') === 'true';
        bellBtn.setAttribute('aria-expanded', !isExpanded);
        dropdown.classList.toggle('show');
    });

    document.addEventListener('click', (e) => {
        if (!bellBtn.contains(e.target) && !dropdown.contains(e.target)) {
            bellBtn.setAttribute('aria-expanded', 'false');
            dropdown.classList.remove('show');
        }
    });

    function escapeHtml(value) {
        if (value == null) return '';
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function getSeverityClass(severity) {
        const s = (severity || '').toLowerCase();
        if (s.includes('critical') || s.includes('outbreak')) return 'critical';
        if (s.includes('high') || s.includes('probable')) return 'high';
        return 'moderate';
    }

    function getAlertTitle(notif) {
        const s = (notif.severity_level || '').toLowerCase();
        if (s.includes('critical')) return 'CRITICAL OUTBREAK ALERT';
        if (s.includes('high')) return 'HIGH RISK ANOMALY DETECTED';
        return 'MODERATE SURVEILLANCE ALERT';
    }

    function formatRiskScoreLine(notif) {
        const parts = [];
        if (notif.final_risk_score != null) {
            parts.push(`Risk Score: ${Number(notif.final_risk_score).toFixed(2)}`);
        }
        if (notif.anomaly_score != null) {
            parts.push(`Anomaly: ${Number(notif.anomaly_score).toFixed(2)}`);
        }
        const label = (notif.severity_level || 'Moderate').replace(/_/g, ' ');
        if (!parts.length) {
            return `${label} — Surveillance alert`;
        }
        return `${parts.join(' · ')} — ${label}`;
    }

    function formatLocation(notif) {
        const barangay = notif.barangay_name ? `Barangay ${notif.barangay_name}` : 'Barangay —';
        const street = (notif.street_address || '').trim();
        return street ? `${barangay}, ${street}` : barangay;
    }

    function formatOfficer(notif) {
        if (notif.officer_name) {
            return notif.officer_name;
        }
        return 'Unassigned / pending routing';
    }

    function formatContact(notif) {
        if (notif.officer_contact) {
            return notif.officer_contact;
        }
        if (notif.officer_email) {
            return notif.officer_email;
        }
        return 'No contact on file';
    }

    function createToastUI(notif) {
        const severityClass = getSeverityClass(notif.severity_level);
        const toast = document.createElement('div');
        toast.className = `toast toast-${severityClass} pulse-alert-card`;

        const contactTel = (notif.officer_contact || '').replace(/\D/g, '');
        // For task notifications, if no contact number, fallback to 'Contact Officer via System' link
        const contactHref = contactTel ? `tel:${contactTel}` : (notif.officer_email ? `mailto:${notif.officer_email}` : '#');
        const mapUrl = notif.map_url || `/map/?barangay=${encodeURIComponent(notif.barangay_name || '')}`;
        const queuedNote = modalQueue.length > 0
            ? `<p class="pulse-alert-card__queue">+ ${modalQueue.length} more unread alert(s) queued</p>`
            : '';

        const acknowledge = () => {
            markAsRead(notif.id).finally(() => {
                removeToast(toast);
                setTimeout(showNextModal, 300);
            });
        };

        const locationText = notif.purok ? `${escapeHtml(notif.barangay_name)} — ${escapeHtml(notif.purok)}` : escapeHtml(notif.barangay_name);
        let badgeHtml = '';
            if (notif.score_shift && notif.score_shift > 0) {
                badgeHtml = `<span class="toast-badge" style="background:#fef2f2;color:#ef4444;margin-left:8px;">+${notif.score_shift.toFixed(2)} Risk Increase</span>`;
            }

            let subtitle = escapeHtml(notif.disease);
            if (notif.purok) subtitle += ` • ${escapeHtml(notif.purok)}`;
            if (notif.active_cases) subtitle += ` • ${notif.active_cases} Active Cases`;
            if (notif.trigger_source) subtitle += ` • Triggered by ${escapeHtml(notif.trigger_source)}`;

            toast.innerHTML = `
                <div class="toast-header pulse-alert-card__header">
                    <div>
                        <span class="toast-badge pulse-alert-card__classification">${escapeHtml(getAlertTitle(notif))}</span>${badgeHtml}
                        <h3 class="pulse-alert-card__title">${locationText}</h3>
                    </div>
                    <button type="button" class="toast-close" aria-label="Close alert">&times;</button>
                </div>
                <div class="toast-body pulse-alert-card__body">
                    <p>${subtitle}</p>
                    <div class="pulse-alert-risk-badge pulse-alert-risk-badge--${severityClass}">
                        ${escapeHtml(formatRiskScoreLine(notif))}
                    </div>
                    <dl class="pulse-alert-card__meta">
                        <div><dt>Status</dt><dd>${escapeHtml(notif.case_status || 'Active')}</dd></div>
                        <div><dt>Disease</dt><dd>${escapeHtml(notif.disease || '—')}</dd></div>
                        <div><dt>Location</dt><dd>${escapeHtml(formatLocation(notif))}</dd></div>
                        <div><dt>Officer</dt><dd>${escapeHtml(formatOfficer(notif))}</dd></div>
                        <div><dt>Contact</dt><dd>${escapeHtml(formatContact(notif))}</dd></div>
                    </dl>
                    <div class="pulse-alert-card__recommendations">
                        <strong>Recommended actions</strong>
                        <p>${escapeHtml(notif.recommendations || 'Review case details and coordinate barangay response.')}</p>
                    </div>
                    ${queuedNote}
                    <div class="toast-actions pulse-alert-card__actions">
                        <button type="button" class="btn btn-secondary toast-dismiss-btn">Acknowledge</button>
                        ${contactTel || notif.officer_email ? `<a href="${escapeHtml(contactHref)}" class="btn btn-outline pulse-alert-card__contact-btn">Contact Officer</a>` : ''}
                        <a href="${escapeHtml(mapUrl)}" class="btn btn-primary pulse-alert-card__map-btn">View on Map</a>
                    </div>
                </div>
            `;
        toastContainer.appendChild(toast);
        setTimeout(() => toast.classList.add('show'), 10);

        toast.querySelector('.toast-close').addEventListener('click', acknowledge);
        toast.querySelector('.toast-dismiss-btn').addEventListener('click', acknowledge);
        toast.querySelector('.pulse-alert-card__map-btn').addEventListener('click', () => {
            markAsRead(notif.id);
        });
    }

    function queueToast(notif) {
        modalQueue.push(notif);
        modalQueue.sort((a, b) => {
            const sA = getSeverityClass(a.severity_level);
            const sB = getSeverityClass(b.severity_level);
            const weight = { critical: 3, high: 2, moderate: 1 };
            return (weight[sB] || 0) - (weight[sA] || 0);
        });

        if (!isModalActive) {
            showNextModal();
        }
    }

    function showNextModal() {
        if (modalQueue.length === 0) {
            toastContainer.classList.remove('active');
            isModalActive = false;
            return;
        }
        isModalActive = true;
        toastContainer.classList.add('active');
        const notif = modalQueue.shift();
        createToastUI(notif);
    }

    function removeToast(toast) {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }

    function renderDropdownItem(notif) {
        const severityClass = getSeverityClass(notif.severity_level);
        const item = document.createElement('div');
        item.className = `notification-item ${notif.is_read ? 'read' : 'unread'}`;
        item.dataset.id = notif.id;

        const locationText = notif.purok ? `${escapeHtml(notif.barangay_name)} — ${escapeHtml(notif.purok)}` : escapeHtml(notif.barangay_name);
        
        let subtitle = escapeHtml(notif.disease);
        if (notif.purok) subtitle += ` • ${escapeHtml(notif.purok)}`;
        if (notif.active_cases) subtitle += ` • ${notif.active_cases} Active Cases`;
        if (notif.trigger_source) subtitle += ` • Triggered by ${escapeHtml(notif.trigger_source)}`;

        let badgeHtml = '';
        if (notif.score_shift && notif.score_shift > 0) {
            badgeHtml = `<span class="toast-badge" style="background:#fef2f2;color:#ef4444;margin-left:8px;">+${notif.score_shift.toFixed(2)} Risk Increase</span>`;
        }

        item.innerHTML = `
            <div class="notification-item-icon bg-${severityClass}">
                <i data-lucide="alert-triangle" class="lucide-icon lucide-icon--sm"></i>
            </div>
            <div class="notification-item-content">
                <div class="notification-item-title">${locationText}${badgeHtml}</div>
                <div class="notification-item-desc">${subtitle}</div>
                <div class="notification-item-time">${notif.last_evaluated_at ? 'Last Evaluated: ' + new Date(notif.last_evaluated_at).toLocaleString() : new Date(notif.created_at).toLocaleString()}</div>
            </div>
        `;

        item.addEventListener('click', () => {
            if (!notif.is_read) {
                markAsRead(notif.id, item);
            }
            window.location.href = notif.map_url || '/dashboard/alerts/';
        });

        return item;
    }

    async function markAsRead(id, itemElement) {
        try {
            const csrfTokenMatch = document.cookie.match(/csrftoken=([^;]+)/);
            const csrfToken = csrfTokenMatch ? csrfTokenMatch[1] : '';
            await fetch(`/dashboard/api/notifications/${id}/read/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            });
            if (itemElement) {
                itemElement.classList.remove('unread');
                itemElement.classList.add('read');
            }

            let currentCount = parseInt(badge.textContent) || 0;
            if (currentCount > 0) {
                currentCount--;
                badge.textContent = currentCount;
                if (currentCount === 0) badge.style.display = 'none';
            }
        } catch (err) {
            console.error('Error marking as read:', err);
        }
    }

    async function fetchNotifications() {
        try {
            const res = await fetch(NOTIFICATIONS_API_URL);
            if (!res.ok) return;
            const data = await res.json();

            if (data.ok) {
                if (data.unread_count > 0) {
                    badge.textContent = data.unread_count;
                    badge.style.display = 'flex';
                } else {
                    badge.style.display = 'none';
                }

                if (data.notifications.length === 0) {
                    listContainer.innerHTML = '<div class="notification-empty">No new alerts</div>';
                } else {
                    listContainer.innerHTML = '';
                    data.notifications.forEach(notif => {
                        listContainer.appendChild(renderDropdownItem(notif));

                        if (!notifiedIds.has(notif.id) && !notif.is_read) {
                            queueToast(notif);
                        }
                        notifiedIds.add(notif.id);
                    });

                    if (window.lucide) {
                        window.lucide.createIcons();
                    }
                }
            }
        } catch (err) {
            console.error('Failed to fetch notifications:', err);
        }
    }

    fetchNotifications();
    setInterval(fetchNotifications, POLL_INTERVAL);

})();
