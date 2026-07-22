(function() {
    const NOTIFICATIONS_API_URL = '/dashboard/api/notifications/';
    const POLL_INTERVAL = 15000; // 15 seconds
    
    let notifiedIds = new Set(JSON.parse(localStorage.getItem('notifiedAlerts') || '[]'));
    let modalQueue = [];
    let isModalActive = false;

    const bellBtn = document.getElementById('notification-bell-btn');
    const badge = document.getElementById('notification-badge');
    const dropdown = document.getElementById('notification-dropdown');
    const listContainer = document.getElementById('notification-list');
    const toastContainer = document.getElementById('toast-container');

    if (!bellBtn) return;

    // Toggle dropdown
    bellBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isExpanded = bellBtn.getAttribute('aria-expanded') === 'true';
        bellBtn.setAttribute('aria-expanded', !isExpanded);
        dropdown.classList.toggle('show');
    });

    // Close dropdown on click outside
    document.addEventListener('click', (e) => {
        if (!bellBtn.contains(e.target) && !dropdown.contains(e.target)) {
            bellBtn.setAttribute('aria-expanded', 'false');
            dropdown.classList.remove('show');
        }
    });

    function getSeverityClass(severity) {
        const s = severity.toLowerCase();
        if (s.includes('critical') || s.includes('outbreak')) return 'critical';
        if (s.includes('high') || s.includes('probable')) return 'high';
        return 'moderate';
    }

    function createToastUI(notif) {
        const severityClass = getSeverityClass(notif.severity_level);
        const toast = document.createElement('div');
        toast.className = `toast toast-${severityClass}`;
        
        toast.innerHTML = `
            <div class="toast-header" style="padding: 16px; font-size: 1.1rem;">
                <span class="toast-badge" style="font-size: 0.8rem; padding: 0.4rem 0.8rem;">${notif.severity_level.toUpperCase()} OUTBREAK ALERT</span>
                <button class="toast-close">&times;</button>
            </div>
            <div class="toast-body" style="padding: 20px;">
                <h4 style="font-size: 1.25rem; margin-bottom: 12px;">${notif.disease} Alert - ${notif.barangay_name}</h4>
                <p style="font-size: 1.05rem;"><strong>${notif.spatial_metric || 'Spatial risk detected'}</strong></p>
                <p style="font-size: 1rem; margin-bottom: 20px;">${notif.temporal_metric || 'Recent surge detected'}</p>
                
                ${modalQueue.length > 0 ? `<div style="font-size: 0.85rem; color: #666; margin-bottom: 16px;">+ ${modalQueue.length} more unread alert(s) queued</div>` : ''}

                <div class="toast-actions" style="display: flex; gap: 12px; justify-content: flex-end;">
                    <button class="btn btn-secondary toast-dismiss-btn" style="padding: 0.6rem 1.2rem;">Dismiss</button>
                    <a href="/dashboard/alerts/" class="btn btn-primary" style="padding: 0.6rem 1.2rem;">View Details</a>
                </div>
            </div>
        `;

        toastContainer.appendChild(toast);
        
        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 10);

        const closeHandler = () => {
            removeToast(toast);
            setTimeout(showNextModal, 300);
        };

        toast.querySelector('.toast-close').addEventListener('click', closeHandler);
        toast.querySelector('.toast-dismiss-btn').addEventListener('click', closeHandler);
    }

    function queueToast(notif) {
        modalQueue.push(notif);
        // Sort highest severity first
        modalQueue.sort((a, b) => {
            const sA = getSeverityClass(a.severity_level);
            const sB = getSeverityClass(b.severity_level);
            const weight = { 'critical': 3, 'high': 2, 'moderate': 1 };
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
        
        item.innerHTML = `
            <div class="notification-item-icon bg-${severityClass}">
                <i data-lucide="alert-triangle" class="lucide-icon lucide-icon--sm"></i>
            </div>
            <div class="notification-item-content">
                <div class="notification-item-title">${notif.disease} in ${notif.barangay_name}</div>
                <div class="notification-item-desc">${notif.spatial_metric || ''}</div>
                <div class="notification-item-time">${new Date(notif.created_at).toLocaleString()}</div>
            </div>
        `;

        item.addEventListener('click', () => {
            if (!notif.is_read) {
                markAsRead(notif.id, item);
            }
            window.location.href = '/dashboard/alerts/';
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
            itemElement.classList.remove('unread');
            itemElement.classList.add('read');
            
            // Decrease badge
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
                // Update Badge
                if (data.unread_count > 0) {
                    badge.textContent = data.unread_count;
                    badge.style.display = 'flex';
                } else {
                    badge.style.display = 'none';
                }

                // Update List
                if (data.notifications.length === 0) {
                    listContainer.innerHTML = '<div class="notification-empty">No new alerts</div>';
                } else {
                    listContainer.innerHTML = '';
                    data.notifications.forEach(notif => {
                        listContainer.appendChild(renderDropdownItem(notif));
                        
                        // Show toast if new
                        if (!notifiedIds.has(notif.id) && !notif.is_read) {
                            queueToast(notif);
                        }
                        notifiedIds.add(notif.id);
                    });
                    
                    // Persist to local storage so they don't reappear on page refresh
                    localStorage.setItem('notifiedAlerts', JSON.stringify([...notifiedIds]));
                    
                    // Re-initialize lucide icons for new elements
                    if (window.lucide) {
                        window.lucide.createIcons();
                    }
                }

            }
        } catch (err) {
            console.error('Failed to fetch notifications:', err);
        }
    }

    // Initial fetch
    fetchNotifications();
    
    // Poll
    setInterval(fetchNotifications, POLL_INTERVAL);

})();
