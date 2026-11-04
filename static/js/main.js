// Shahid Smriti School Main Client Script

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide icons if available
    if (window.lucide) {
        window.lucide.createIcons();
    }
});

// Mobile Drawer controls
function openMobileDrawer() {
    const drawer = document.getElementById('mobileDrawer');
    if (drawer) {
        drawer.classList.remove('hidden');
    }
}

function closeMobileDrawer() {
    const drawer = document.getElementById('mobileDrawer');
    if (drawer) {
        drawer.classList.add('hidden');
    }
}
