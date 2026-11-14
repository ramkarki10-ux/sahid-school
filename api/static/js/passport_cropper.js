/**
 * Shahid Smriti School - Universal Interactive Passport Photo Cropper & Positioner
 * Supports: Dragging (up/down/left/right), Zooming, Auto-compression <= 300 KB, Cancel, Delete.
 */
(function() {
    let currentOptions = null;
    let imgElement = null;
    let canvas = null;
    let ctx = null;
    let scale = 1.0;
    let minScale = 0.5;
    let maxScale = 3.5;
    let offsetX = 0;
    let offsetY = 0;
    let isDragging = false;
    let startX = 0;
    let startY = 0;
    let pinchStartDist = 0;
    let pinchStartScale = 1.0;

    const FRAME_W = 270; // 3:4 aspect ratio passport frame
    const FRAME_H = 360;

    function buildCropperModalHTML() {
        if (document.getElementById('passportCropperModal')) return;

        const modalDiv = document.createElement('div');
        modalDiv.id = 'passportCropperModal';
        modalDiv.className = 'fixed inset-0 z-[9999] bg-slate-950/80 backdrop-blur-sm hidden flex items-center justify-center p-3 sm:p-4 select-none';
        modalDiv.innerHTML = `
            <div class="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[95vh] animate-in fade-in zoom-in-95 duration-150">
                <!-- Header -->
                <div class="bg-gradient-to-r from-instBlue to-slate-900 text-white p-4 flex items-center justify-between">
                    <div class="flex items-center gap-2.5">
                        <span class="p-1.5 bg-amber-400 text-slate-900 rounded-lg">
                            <i data-lucide="crop" class="w-4 h-4"></i>
                        </span>
                        <div>
                            <h3 class="font-bold text-sm text-amber-300">पासपोर्ट साइज फोटो समायोजन</h3>
                            <p class="text-[11px] text-slate-300">फोटो तानेर (Drag) तल, माथि, दायाँ वा बायाँ मिलाउनुहोस्</p>
                        </div>
                    </div>
                    <button type="button" onclick="window.closePassportCropper()" class="p-1.5 text-slate-300 hover:text-white rounded-lg hover:bg-white/10 transition">
                        <i data-lucide="x" class="w-5 h-5"></i>
                    </button>
                </div>

                <!-- Cropper Viewport Container -->
                <div class="p-4 bg-slate-900 flex flex-col items-center justify-center space-y-3">
                    <div class="relative rounded-xl overflow-hidden shadow-2xl border-4 border-amber-400/90 cursor-grab active:cursor-grabbing bg-slate-950" 
                         id="cropCanvasWrapper" 
                         style="width: ${FRAME_W}px; height: ${FRAME_H}px; touch-action: none;">
                        <canvas id="passportCanvas" width="${FRAME_W}" height="${FRAME_H}" class="block"></canvas>
                        
                        <!-- Passport Oval Face Guide Overlay -->
                        <div class="absolute inset-0 pointer-events-none flex flex-col items-center justify-center">
                            <div class="w-[180px] h-[230px] rounded-[50%] border border-dashed border-amber-300/60 shadow-[0_0_0_9999px_rgba(0,0,0,0.35)]"></div>
                            <span class="text-[10px] text-amber-200 bg-black/60 px-2 py-0.5 rounded-full mt-2 font-medium tracking-wide">
                                मुख/अनुहार यहाँ बीचमा मिलाउनुहोस्
                            </span>
                        </div>
                    </div>

                    <div class="flex items-center justify-between w-full max-w-[270px] text-[11px] text-slate-300">
                        <span class="flex items-center gap-1 text-amber-300">
                            <i data-lucide="move" class="w-3.5 h-3.5"></i>
                            <span>माउस/औंलाले सार्नुहोस्</span>
                        </span>
                        <span id="cropperSizeEstimate" class="font-mono text-emerald-400">अधिकतम ३०० KB</span>
                    </div>

                    <!-- Zoom Controls -->
                    <div class="w-full max-w-[280px] bg-slate-800/90 p-2.5 rounded-xl border border-slate-700 space-y-1.5 text-white">
                        <div class="flex items-center justify-between text-[11px] text-slate-300 font-medium">
                            <span>जुम / साइज (Scale)</span>
                            <span id="zoomPercentLabel" class="font-mono text-amber-300">१००%</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <button type="button" onclick="window.adjustCropperZoom(-0.15)" class="p-1 rounded bg-slate-700 hover:bg-slate-600 text-xs font-bold w-6 h-6 flex items-center justify-center">-</button>
                            <input type="range" id="cropperZoomSlider" min="50" max="300" value="100" class="flex-1 accent-amber-400 h-1.5 bg-slate-600 rounded-lg cursor-pointer">
                            <button type="button" onclick="window.adjustCropperZoom(0.15)" class="p-1 rounded bg-slate-700 hover:bg-slate-600 text-xs font-bold w-6 h-6 flex items-center justify-center">+</button>
                            <button type="button" onclick="window.resetCropperPosition()" class="p-1 px-1.5 rounded bg-slate-700 hover:bg-slate-600 text-[10px] text-slate-300" title="रिसेट गर्नुहोस्">
                                ⟲ बीचमा
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Footer Actions -->
                <div class="p-3.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between gap-2">
                    <button type="button" onclick="window.deleteCropperPhoto()" class="inline-flex items-center gap-1.5 px-3 py-2 text-rose-600 hover:bg-rose-50 border border-rose-200 rounded-xl font-bold text-xs transition" title="फोटो मेटाउनुहोस्">
                        <i data-lucide="trash-2" class="w-4 h-4 text-rose-500"></i>
                        <span>फोटो हटाउनुहोस्</span>
                    </button>

                    <div class="flex items-center gap-2">
                        <button type="button" onclick="window.closePassportCropper()" class="px-3.5 py-2 text-slate-600 hover:bg-slate-200 border border-slate-300 rounded-xl font-semibold text-xs transition">
                            रद्द गर्नुहोस्
                        </button>
                        <button type="button" onclick="window.savePassportCroppedPhoto()" id="saveCroppedBtn" class="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-xs shadow-md transition">
                            <i data-lucide="check" class="w-4 h-4 text-emerald-200"></i>
                            <span>क्रप गरी सेभ गर्नुहोस्</span>
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modalDiv);
        attachCanvasEvents();
        if (window.lucide) lucide.createIcons();
    }

    function drawImage() {
        if (!canvas || !ctx || !imgElement) return;

        ctx.clearRect(0, 0, FRAME_W, FRAME_H);
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, FRAME_W, FRAME_H);

        const drawW = imgElement.naturalWidth * scale;
        const drawH = imgElement.naturalHeight * scale;

        ctx.save();
        ctx.drawImage(imgElement, offsetX, offsetY, drawW, drawH);
        ctx.restore();
    }

    function fitImageInitial() {
        if (!imgElement || !imgElement.naturalWidth) return;
        const imgW = imgElement.naturalWidth;
        const imgH = imgElement.naturalHeight;

        // Cover the 270x360 frame
        const scaleW = FRAME_W / imgW;
        const scaleH = FRAME_H / imgH;
        scale = Math.max(scaleW, scaleH);
        minScale = scale * 0.5;
        maxScale = scale * 4.0;

        // Center initially
        const drawW = imgW * scale;
        const drawH = imgH * scale;
        offsetX = (FRAME_W - drawW) / 2;
        offsetY = (FRAME_H - drawH) / 2;

        updateSliderUI();
        drawImage();
    }

    function updateSliderUI() {
        const slider = document.getElementById('cropperZoomSlider');
        const label = document.getElementById('zoomPercentLabel');
        if (slider) {
            const pct = Math.round((scale / (minScale * 2)) * 100);
            slider.value = pct;
            if (label) label.innerText = pct + '%';
        }
    }

    function attachCanvasEvents() {
        const wrapper = document.getElementById('cropCanvasWrapper');
        canvas = document.getElementById('passportCanvas');
        if (!canvas || !wrapper) return;
        ctx = canvas.getContext('2d');

        // Mouse Events
        wrapper.addEventListener('mousedown', function(e) {
            isDragging = true;
            startX = e.clientX - offsetX;
            startY = e.clientY - offsetY;
            wrapper.style.cursor = 'grabbing';
            e.preventDefault();
        });

        window.addEventListener('mousemove', function(e) {
            if (!isDragging) return;
            offsetX = e.clientX - startX;
            offsetY = e.clientY - startY;
            drawImage();
        });

        window.addEventListener('mouseup', function() {
            if (isDragging) {
                isDragging = false;
                if (wrapper) wrapper.style.cursor = 'grab';
            }
        });

        // Touch Events (Mobile/Tablet Drag & Pinch)
        wrapper.addEventListener('touchstart', function(e) {
            if (e.touches.length === 1) {
                isDragging = true;
                startX = e.touches[0].clientX - offsetX;
                startY = e.touches[0].clientY - offsetY;
            } else if (e.touches.length === 2) {
                isDragging = false;
                const dx = e.touches[0].clientX - e.touches[1].clientX;
                const dy = e.touches[0].clientY - e.touches[1].clientY;
                pinchStartDist = Math.hypot(dx, dy);
                pinchStartScale = scale;
            }
            e.preventDefault();
        }, { passive: false });

        wrapper.addEventListener('touchmove', function(e) {
            if (e.touches.length === 1 && isDragging) {
                offsetX = e.touches[0].clientX - startX;
                offsetY = e.touches[0].clientY - startY;
                drawImage();
            } else if (e.touches.length === 2 && pinchStartDist > 0) {
                const dx = e.touches[0].clientX - e.touches[1].clientX;
                const dy = e.touches[0].clientY - e.touches[1].clientY;
                const dist = Math.hypot(dx, dy);
                const factor = dist / pinchStartDist;
                scale = Math.min(Math.max(pinchStartScale * factor, minScale), maxScale);
                updateSliderUI();
                drawImage();
            }
            e.preventDefault();
        }, { passive: false });

        wrapper.addEventListener('touchend', function() {
            isDragging = false;
            pinchStartDist = 0;
        });

        // Mouse Wheel Zoom
        wrapper.addEventListener('wheel', function(e) {
            e.preventDefault();
            const delta = e.deltaY < 0 ? 0.08 : -0.08;
            window.adjustCropperZoom(delta);
        }, { passive: false });

        // Slider Change
        const slider = document.getElementById('cropperZoomSlider');
        if (slider) {
            slider.addEventListener('input', function() {
                const pct = parseInt(this.value);
                scale = (minScale * 2) * (pct / 100);
                const label = document.getElementById('zoomPercentLabel');
                if (label) label.innerText = pct + '%';
                drawImage();
            });
        }
    }

    window.adjustCropperZoom = function(delta) {
        const oldScale = scale;
        scale = Math.min(Math.max(scale + delta * scale, minScale), maxScale);
        
        // Zoom centered on canvas
        const factor = scale / oldScale;
        offsetX = FRAME_W / 2 - (FRAME_W / 2 - offsetX) * factor;
        offsetY = FRAME_H / 2 - (FRAME_H / 2 - offsetY) * factor;

        updateSliderUI();
        drawImage();
    };

    window.resetCropperPosition = function() {
        fitImageInitial();
    };

    window.openPassportCropper = function(options) {
        buildCropperModalHTML();
        currentOptions = options || {};

        const modal = document.getElementById('passportCropperModal');
        if (!modal) return;

        const src = options.imageSrc;
        if (!src) {
            alert('कृपया पहिले फोटो छान्नुहोस्।');
            return;
        }

        modal.classList.remove('hidden');
        if (window.lucide) lucide.createIcons();

        imgElement = new Image();
        imgElement.crossOrigin = 'anonymous';
        imgElement.onload = function() {
            fitImageInitial();
        };
        imgElement.onerror = function() {
            alert('फोटो लोड हुन सकेन। कृपया अन्य फोटो छान्नुहोस्।');
            window.closePassportCropper();
        };
        imgElement.src = src;
    };

    window.closePassportCropper = function() {
        const modal = document.getElementById('passportCropperModal');
        if (modal) modal.classList.add('hidden');
        if (currentOptions && currentOptions.onCancel) {
            currentOptions.onCancel();
        }
        currentOptions = null;
    };

    window.deleteCropperPhoto = function() {
        if (!confirm('के तपाईं निश्चित रूपमा यो फोटो हटाउन चाहनुहुन्छ?')) return;
        
        if (currentOptions) {
            const targetInput = currentOptions.targetInputId ? document.getElementById(currentOptions.targetInputId) : null;
            const previewImg = currentOptions.previewImgId ? document.getElementById(currentOptions.previewImgId) : null;
            const previewIcon = currentOptions.previewIconId ? document.getElementById(currentOptions.previewIconId) : null;
            const statusEl = currentOptions.statusElId ? document.getElementById(currentOptions.statusElId) : null;

            if (targetInput) targetInput.value = 'REMOVE';
            if (previewImg) {
                previewImg.src = '';
                previewImg.classList.add('hidden');
            }
            if (previewIcon) previewIcon.classList.remove('hidden');
            if (statusEl) {
                statusEl.innerHTML = '<span class="text-rose-600 font-semibold text-[11px]">फोटो हटाइयो। सुरक्षित गर्न सेभ गर्नुहोस्।</span>';
            }

            if (currentOptions.onDelete) {
                currentOptions.onDelete();
            }
        }

        window.closePassportCropper();
    };

    window.savePassportCroppedPhoto = async function() {
        if (!canvas || !imgElement || !currentOptions) return;

        const saveBtn = document.getElementById('saveCroppedBtn');
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i data-lucide="loader" class="w-4 h-4 animate-spin"></i><span>कम्प्रेस हुँदैछ...</span>';
        if (window.lucide) lucide.createIcons();

        try {
            // Render at high passport resolution: 600x800 px (3:4 ratio)
            const targetW = 600;
            const targetH = 800;
            const exportCanvas = document.createElement('canvas');
            exportCanvas.width = targetW;
            exportCanvas.height = targetH;
            const expCtx = exportCanvas.getContext('2d');

            expCtx.fillStyle = '#FFFFFF';
            expCtx.fillRect(0, 0, targetW, targetH);

            // Ratio from preview frame (270x360) to export (600x800)
            const ratio = targetW / FRAME_W;
            const drawW = (imgElement.naturalWidth * scale) * ratio;
            const drawH = (imgElement.naturalHeight * scale) * ratio;
            const drawX = offsetX * ratio;
            const drawY = offsetY * ratio;

            expCtx.drawImage(imgElement, drawX, drawY, drawW, drawH);

            // Compress to JPEG <= 300 KB (307,200 bytes)
            const MAX_BYTES = 300 * 1024;
            let quality = 0.88;
            let dataUrl = exportCanvas.toDataURL('image/jpeg', quality);

            while (dataUrl.length * 0.75 > MAX_BYTES && quality > 0.25) {
                quality -= 0.10;
                dataUrl = exportCanvas.toDataURL('image/jpeg', quality);
            }

            if (dataUrl.length * 0.75 > MAX_BYTES) {
                const downCanvas = document.createElement('canvas');
                downCanvas.width = 450;
                downCanvas.height = 600;
                const downCtx = downCanvas.getContext('2d');
                downCtx.drawImage(exportCanvas, 0, 0, 450, 600);
                dataUrl = downCanvas.toDataURL('image/jpeg', 0.80);
            }

            // Export as Blob for server upload
            const blob = await new Promise(resolve => exportCanvas.toBlob(resolve, 'image/jpeg', quality));
            const finalSizeKb = (blob.size / 1024).toFixed(1);

            const targetInput = currentOptions.targetInputId ? document.getElementById(currentOptions.targetInputId) : null;
            const previewImg = currentOptions.previewImgId ? document.getElementById(currentOptions.previewImgId) : null;
            const previewIcon = currentOptions.previewIconId ? document.getElementById(currentOptions.previewIconId) : null;
            const statusEl = currentOptions.statusElId ? document.getElementById(currentOptions.statusElId) : null;

            // Set Data URL immediately so image displays anywhere and persists reliably across serverless instances
            if (targetInput) {
                targetInput.value = dataUrl;
                targetInput.dispatchEvent(new Event('input', { bubbles: true }));
                targetInput.dispatchEvent(new Event('change', { bubbles: true }));
            }
            if (previewImg) {
                previewImg.src = dataUrl;
                previewImg.classList.remove('hidden');
            }
            if (previewIcon) previewIcon.classList.add('hidden');

            // Also upload compressed blob to server in background
            try {
                const formData = new FormData();
                formData.append('file', blob, `passport_${Date.now()}.jpg`);
                fetch('/api/upload', { method: 'POST', body: formData }).catch(() => {});
            } catch (err) {
                // Background upload ignore
            }

            if (statusEl) {
                statusEl.innerHTML = `<span class="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-lg text-xs font-bold">✓ पासपोर्ट फोटो तयार: ${finalSizeKb} KB (३०० KB भित्र सुरक्षित)</span>`;
            }

            if (currentOptions.onSave) {
                currentOptions.onSave({ dataUrl, blob, sizeKb: finalSizeKb, targetInputId: currentOptions.targetInputId });
            }

            window.closePassportCropper();
        } catch (err) {
            alert('फोटो सेभ गर्दा त्रुटि भयो: ' + err.message);
        } finally {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i data-lucide="check" class="w-4 h-4 text-emerald-200"></i><span>क्रप गरी सेभ गर्नुहोस्</span>';
            if (window.lucide) lucide.createIcons();
        }
    };

    // Global launcher triggered from file inputs
    window.handlePassportFileInput = function(input, targetInputId, previewImgId, previewIconId, statusElId) {
        if (!input.files || !input.files[0]) return;
        const file = input.files[0];
        if (!file.type.startsWith('image/')) {
            alert('कृपया मान्य फोटो (JPG, PNG, WebP) फाइल छान्नुहोस्।');
            return;
        }

        const reader = new FileReader();
        reader.onload = function(e) {
            window.openPassportCropper({
                imageSrc: e.target.result,
                targetInputId,
                previewImgId,
                previewIconId,
                statusElId
            });
        };
        reader.readAsDataURL(file);
    };

    // Re-adjust already uploaded photo
    window.reopenPassportCropper = function(targetInputId, previewImgId, previewIconId, statusElId) {
        const input = document.getElementById(targetInputId);
        const preview = document.getElementById(previewImgId);
        const src = (input && input.value) || (preview && preview.src);
        if (!src) {
            alert('अहिलेसम्म कुनै फोटो छानिएको छैन। कृपया पहिले फोटो अपलोड गर्नुहोस्।');
            return;
        }
        window.openPassportCropper({
            imageSrc: src,
            targetInputId,
            previewImgId,
            previewIconId,
            statusElId
        });
    };

    // Delete photo directly from form
    window.clearPassportPhotoDirect = function(targetInputId, previewImgId, previewIconId, statusElId) {
        if (!confirm('के तपाईं फोटो हटाउन चाहनुहुन्छ?')) return;
        const input = document.getElementById(targetInputId);
        const preview = document.getElementById(previewImgId);
        const icon = document.getElementById(previewIconId);
        const status = document.getElementById(statusElId);

        if (input) input.value = 'REMOVE';
        if (preview) {
            preview.src = '';
            preview.classList.add('hidden');
        }
        if (icon) icon.classList.remove('hidden');
        if (status) status.innerHTML = '<span class="text-rose-600 font-semibold text-[11px]">फोटो हटाइयो। सुरक्षित गर्न सेभ गर्नुहोस्।</span>';
    };

    // Auto-initialize on DOMContentLoaded
    document.addEventListener('DOMContentLoaded', function() {
        buildCropperModalHTML();
    });
})();

