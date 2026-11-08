// Shahid Smriti School Main Client Script

function openMobileDrawer() {
    const drawer = document.getElementById('mobileDrawer');
    const panel = document.getElementById('drawerPanel');
    const overlay = document.getElementById('drawerOverlay');
    if (!drawer) return;

    drawer.classList.remove('pointer-events-none');
    drawer.classList.add('pointer-events-auto');
    drawer.setAttribute('aria-hidden', 'false');

    if (overlay) {
        overlay.classList.remove('opacity-0', 'pointer-events-none');
        overlay.classList.add('opacity-100', 'pointer-events-auto');
    }

    if (panel) {
        panel.classList.remove('-translate-x-full');
        panel.classList.add('translate-x-0');
    }

    document.body.style.overflow = 'hidden';
}

function closeMobileDrawer() {
    const drawer = document.getElementById('mobileDrawer');
    const panel = document.getElementById('drawerPanel');
    const overlay = document.getElementById('drawerOverlay');
    if (!drawer) return;

    if (panel) {
        panel.classList.remove('translate-x-0');
        panel.classList.add('-translate-x-full');
    }

    if (overlay) {
        overlay.classList.remove('opacity-100', 'pointer-events-auto');
        overlay.classList.add('opacity-0', 'pointer-events-none');
    }

    drawer.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';

    setTimeout(() => {
        if (drawer.getAttribute('aria-hidden') === 'true') {
            drawer.classList.remove('pointer-events-auto');
            drawer.classList.add('pointer-events-none');
        }
    }, 300);
}

function toggleDrawerSubmenu(id) {
    const sub = document.getElementById(id);
    const icon = document.getElementById(id + 'Icon');
    if (!sub) return;
    if (sub.classList.contains('hidden')) {
        sub.classList.remove('hidden');
        if (icon) icon.classList.add('rotate-180');
    } else {
        sub.classList.add('hidden');
        if (icon) icon.classList.remove('rotate-180');
    }
}

// Global hookup on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Attach listener to mobile menu buttons (all instances)
    const menuButtons = document.querySelectorAll('#mobileMenuBtn, [onclick="openMobileDrawer()"]');
    menuButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            openMobileDrawer();
        });
    });

    // Attach listener to close button
    const closeBtn = document.getElementById('closeDrawerBtn');
    if (closeBtn) {
        closeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            closeMobileDrawer();
        });
    }

    // Attach listener to overlay
    const overlay = document.getElementById('drawerOverlay');
    if (overlay) {
        overlay.addEventListener('click', closeMobileDrawer);
    }

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeMobileDrawer();
        }
    });

    // Initialize Lucide icons if available
    if (window.lucide) {
        window.lucide.createIcons();
    }
});
