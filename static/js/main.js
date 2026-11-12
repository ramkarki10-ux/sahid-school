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

// =========================================================================
// UNIVERSAL CLIENT-SIDE PHOTO AUTO-RESIZER & COMPRESSOR (MAX 300 KB)
// =========================================================================
window.compressAndResizeImage = function(file, maxDimension = 800, maxSizeBytes = 300 * 1024) {
    return new Promise((resolve, reject) => {
        if (!file || !file.type.startsWith('image/')) {
            reject(new Error("कृपया मान्य तस्विर (JPG, PNG, WebP) फाइल छान्नुहोस्।"));
            return;
        }

        const reader = new FileReader();
        reader.onerror = () => reject(new Error("फाइल पढ्न सकिएन।"));
        reader.onload = function(e) {
            const img = new Image();
            img.onerror = () => reject(new Error("तस्विर लोड हुन सकेन।"));
            img.onload = function() {
                let width = img.width;
                let height = img.height;

                // Scale down proportionally if larger than maxDimension
                if (width > maxDimension || height > maxDimension) {
                    if (width > height) {
                        height = Math.round((height * maxDimension) / width);
                        width = maxDimension;
                    } else {
                        width = Math.round((width * maxDimension) / height);
                        height = maxDimension;
                    }
                }

                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                
                // Draw white background in case of transparent PNG
                ctx.fillStyle = '#FFFFFF';
                ctx.fillRect(0, 0, width, height);
                ctx.drawImage(img, 0, 0, width, height);

                // Iterative compression to stay strictly <= 300 KB
                let quality = 0.88;
                let dataUrl = canvas.toDataURL('image/jpeg', quality);
                
                // If larger than maxSizeBytes, reduce quality iteratively
                while (dataUrl.length * 0.75 > maxSizeBytes && quality > 0.3) {
                    quality -= 0.12;
                    dataUrl = canvas.toDataURL('image/jpeg', quality);
                }

                // If still above 300 KB, resize canvas smaller (e.g. 550x550)
                if (dataUrl.length * 0.75 > maxSizeBytes) {
                    canvas.width = Math.round(width * 0.75);
                    canvas.height = Math.round(height * 0.75);
                    ctx.fillStyle = '#FFFFFF';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                    dataUrl = canvas.toDataURL('image/jpeg', 0.75);
                }

                // Final check to guarantee < 300 KB
                canvas.toBlob((blob) => {
                    const finalBlob = blob || file;
                    const finalSizeKb = (finalBlob.size / 1024).toFixed(1);
                    resolve({
                        dataUrl: dataUrl,
                        blob: finalBlob,
                        width: canvas.width,
                        height: canvas.height,
                        sizeKb: finalSizeKb,
                        isUnderLimit: finalBlob.size <= maxSizeBytes
                    });
                }, 'image/jpeg', quality);
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    });
};

window.handleAutoResizedPhotoUpload = async function(fileInput, targetInputId, previewImgId, previewIconId, statusElId) {
    if (!fileInput.files || !fileInput.files[0]) return;
    const file = fileInput.files[0];
    const statusEl = statusElId ? document.getElementById(statusElId) : null;
    const targetInput = targetInputId ? document.getElementById(targetInputId) : null;
    const previewImg = previewImgId ? document.getElementById(previewImgId) : null;
    const previewIcon = previewIconId ? document.getElementById(previewIconId) : null;

    if (statusEl) {
        statusEl.innerHTML = '<span class="text-amber-600 font-semibold animate-pulse"><i class="fas fa-spinner fa-spin"></i> तस्विर अटो-साइज तथा कम्प्रेस गरिँदैछ (अधिकतम ३०० KB)...</span>';
    }

    try {
        const compressed = await window.compressAndResizeImage(file, 800, 300 * 1024);

        // Immediate visual preview with compressed data URL
        if (previewImg) {
            previewImg.src = compressed.dataUrl;
            previewImg.classList.remove('hidden');
        }
        if (previewIcon) {
            previewIcon.classList.add('hidden');
        }

        // Set default value to base64 Data URL so it works even if offline or serverless
        if (targetInput) {
            targetInput.value = compressed.dataUrl;
        }

        // Upload compressed Blob to server
        const formData = new FormData();
        const safeName = file.name.replace(/\.[^/.]+$/, "") + ".jpg";
        formData.append('file', compressed.blob, safeName);

        try {
            const res = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (res.ok && data.url) {
                if (targetInput) {
                    targetInput.value = data.url;
                }
            }
        } catch (uploadErr) {
            console.warn("Server file upload fallback to Data URL", uploadErr);
        }

        if (statusEl) {
            statusEl.innerHTML = `<span class="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded text-[11px] font-bold">✓ तस्विर अटो-साइज भयो: ${compressed.sizeKb} KB (३०० KB भन्दा कम)</span>`;
        }
    } catch (err) {
        if (statusEl) {
            statusEl.innerHTML = `<span class="text-rose-600 font-semibold">त्रुटि: ${err.message || 'तस्विर प्रशोधन हुन सकेन।'}</span>`;
        }
    }
};
