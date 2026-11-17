// CapCut Video Text Studio - Main Application Logic
document.addEventListener("DOMContentLoaded", () => {
    // State
    const state = {
        clips: [],
        activeClipIndex: 0,
        showText: true,
        textOverlay: {
            text: "helo helo",
            font_family: "BeVietnamPro",
            font_size: 42,
            align: "center",
            text_color: "#000000",
            bg_color: "#FFFFFF",
            bg_opacity: 1.0,
            border_radius: 14,
            pad_x: 26,
            pad_y: 14,
            max_width_pct: 85,
            shadow: true,
            x_pct: 50.0,
            y_pct: 80.0,
            full_duration: true,
            start: 0.0,
            end: 10.0
        },
        canvasMode: "custom",
        videoWidth: 720,
        videoHeight: 1280,
        fitMode: "contain",
        qualityCrf: 0,
        upscaleMode: "none",
        volumePct: 100,
        speed: 1.0,
        mergeMode: "single", // "single" or "batch"
        chunkSize: 2,
        handleRemainder: "merge", // "merge" or "skip"
        isPlaying: false,
        exportTaskId: null,
        pollInterval: null
    };

    // DOM Elements
    const elements = {
        // Nav
        btnExportVideo: document.getElementById("btnExportVideo"),
        btnOpenFolder: document.getElementById("btnOpenFolder"),
        clipCountText: document.getElementById("clipCountText"),
        totalDurationText: document.getElementById("totalDurationText"),
        canvasSummaryText: document.getElementById("canvasSummaryText"),

        // Left Panel Tabs
        tabBtnClips: document.getElementById("tabBtnClips"),
        tabBtnSettings: document.getElementById("tabBtnSettings"),
        tabPanelClips: document.getElementById("tabPanelClips"),
        tabPanelSettings: document.getElementById("tabPanelSettings"),
        tabBadgeClips: document.getElementById("tabBadgeClips"),
        clipsStatsText: document.getElementById("clipsStatsText"),
        clipsTotalDurText: document.getElementById("clipsTotalDurText"),

        // Left Panel - Video & Custom Dimensions
        btnBrowseFiles: document.getElementById("btnBrowseFiles"),
        fileUploadInput: document.getElementById("fileUploadInput"),
        dropzone: document.getElementById("dropzone"),
        clipsList: document.getElementById("clipsList"),
        emptyState: document.getElementById("emptyState"),
        inputVideoWidth: document.getElementById("inputVideoWidth"),
        inputVideoHeight: document.getElementById("inputVideoHeight"),
        resChips: document.querySelectorAll(".res-chip"),
        chipResOriginal: document.getElementById("chipResOriginal"),
        selectFitMode: document.getElementById("selectFitMode"),
        selectQuality: document.getElementById("selectQuality"),
        selectUpscaleMode: document.getElementById("selectUpscaleMode"),
        upscaleModeHint: document.getElementById("upscaleModeHint"),
        optUpscaleAi: document.getElementById("optUpscaleAi"),
        sliderVolume: document.getElementById("sliderVolume"),
        volumeValue: document.getElementById("volumeValue"),
        btnVolumeReset: document.getElementById("btnVolumeReset"),
        sliderSpeed: document.getElementById("sliderSpeed"),
        speedValue: document.getElementById("speedValue"),
        btnSpeedReset: document.getElementById("btnSpeedReset"),
        speedChips: document.querySelectorAll(".speed-chip"),
        inputFilePrefix: document.getElementById("inputFilePrefix"),
        filePrefixHint: document.getElementById("filePrefixHint"),

        // Batch Merge Controls
        mergeModeRadios: document.querySelectorAll("input[name='mergeMode']"),
        batchSettingsBox: document.getElementById("batchSettingsBox"),
        chunkSizeInput: document.getElementById("chunkSizeInput"),
        chunkSizeDisplay: document.getElementById("chunkSizeDisplay"),
        btnChunkMinus: document.getElementById("btnChunkMinus"),
        btnChunkPlus: document.getElementById("btnChunkPlus"),
        chunkChips: document.querySelectorAll(".chunk-chip"),
        selectRemainder: document.getElementById("selectRemainder"),
        batchSummaryPill: document.getElementById("batchSummaryPill"),

        // Center Panel
        viewportWrapper: document.getElementById("viewportWrapper"),
        videoContainer: document.getElementById("videoContainer"),
        previewVideo: document.getElementById("previewVideo"),
        playerPlaceholder: document.getElementById("playerPlaceholder"),
        btnEmptyBrowse: document.getElementById("btnEmptyBrowse"),
        currentClipName: document.getElementById("currentClipName"),
        btnSnapCenter: document.getElementById("btnSnapCenter"),
        btnResetPosition: document.getElementById("btnResetPosition"),
        guideH: document.getElementById("guideH"),
        guideV: document.getElementById("guideV"),

        // Draggable Badge
        draggableBadge: document.getElementById("draggableBadge"),
        badgeTextContent: document.getElementById("badgeTextContent"),
        badgeCoordsTag: document.getElementById("badgeCoordsTag"),

        // Controls Bar
        btnPlayPause: document.getElementById("btnPlayPause"),
        playIcon: document.getElementById("playIcon"),
        currentTimeDisplay: document.getElementById("currentTimeDisplay"),
        totalDurationDisplay: document.getElementById("totalDurationDisplay"),
        timelineBar: document.getElementById("timelineBar"),
        timelineFill: document.getElementById("timelineFill"),
        timelineThumb: document.getElementById("timelineThumb"),
        btnMuteToggle: document.getElementById("btnMuteToggle"),
        muteIcon: document.getElementById("muteIcon"),
        mediaStripTray: document.getElementById("mediaStripTray"),
        mediaStripList: document.getElementById("mediaStripList"),
        trayClipCount: document.getElementById("trayClipCount"),

        // Right Panel Text Customizer
        inputText: document.getElementById("inputText"),
        selectFont: document.getElementById("selectFont"),
        sliderFontSize: document.getElementById("sliderFontSize"),
        valFontSize: document.getElementById("valFontSize"),
        alignButtons: document.querySelectorAll(".toggle-btn[data-align]"),
        inputBgColor: document.getElementById("inputBgColor"),
        valBgColor: document.getElementById("valBgColor"),
        inputTextColor: document.getElementById("inputTextColor"),
        valTextColor: document.getElementById("valTextColor"),
        sliderBgOpacity: document.getElementById("sliderBgOpacity"),
        valBgOpacity: document.getElementById("valBgOpacity"),
        sliderBorderRadius: document.getElementById("sliderBorderRadius"),
        valBorderRadius: document.getElementById("valBorderRadius"),
        sliderPadX: document.getElementById("sliderPadX"),
        valPadX: document.getElementById("valPadX"),
        sliderPadY: document.getElementById("sliderPadY"),
        valPadY: document.getElementById("valPadY"),
        sliderMaxWidth: document.getElementById("sliderMaxWidth"),
        valMaxWidth: document.getElementById("valMaxWidth"),
        checkShadow: document.getElementById("checkShadow"),
        presetButtons: document.querySelectorAll(".preset-btn"),
        // Position Controls
        checkEnableDrag: document.getElementById("checkEnableDrag"),
        checkShowText: document.getElementById("checkShowText"),
        sliderPosX: document.getElementById("sliderPosX"),
        inputPosX: document.getElementById("inputPosX"),
        sliderPosY: document.getElementById("sliderPosY"),
        inputPosY: document.getElementById("inputPosY"),
        btnPosTop: document.getElementById("btnPosTop"),
        btnPosCenter: document.getElementById("btnPosCenter"),
        btnPosBottom: document.getElementById("btnPosBottom"),
        btnPosCenterX: document.getElementById("btnPosCenterX"),

        timingRadios: document.querySelectorAll("input[name='timingMode']"),
        timingCustomFields: document.getElementById("timingCustomFields"),
        inputStartTime: document.getElementById("inputStartTime"),
        inputEndTime: document.getElementById("inputEndTime"),
        btnSetStartCurrent: document.getElementById("btnSetStartCurrent"),
        btnSetEndCurrent: document.getElementById("btnSetEndCurrent"),

        // Import Modal
        importModal: document.getElementById("importModal"),
        importCountTag: document.getElementById("importCountTag"),
        importPercentTag: document.getElementById("importPercentTag"),
        importProgressFill: document.getElementById("importProgressFill"),
        importCurrentFilename: document.getElementById("importCurrentFilename"),
        importStatusText: document.getElementById("importStatusText"),

        // Export Modal
        exportModal: document.getElementById("exportModal"),
        btnModalClose: document.getElementById("btnModalClose"),
        modalProgressView: document.getElementById("modalProgressView"),
        modalFinishedView: document.getElementById("modalFinishedView"),
        progressCircle: document.getElementById("progressCircle"),
        progressPercentage: document.getElementById("progressPercentage"),
        progressMessage: document.getElementById("progressMessage"),
        finishedVideoPlayer: document.getElementById("finishedVideoPlayer"),
        btnOpenSingleFile: document.getElementById("btnOpenSingleFile"),
        btnOpenFinishedFolder: document.getElementById("btnOpenFinishedFolder"),
        finishedBadgeText: document.getElementById("finishedBadgeText"),
        singleFinishedActions: document.getElementById("singleFinishedActions"),
        batchOutputsContainer: document.getElementById("batchOutputsContainer"),
        batchOutputsList: document.getElementById("batchOutputsList"),
        batchOutputCountTag: document.getElementById("batchOutputCountTag"),

        toastContainer: document.getElementById("toastContainer")
    };

    // Helper: Toast notification
    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast ${type === "error" ? "toast-error" : type === "success" ? "toast-success" : ""}`;
        toast.innerHTML = `<span>${type === "error" ? "⚠️" : type === "success" ? "✅" : "ℹ️"}</span> <span>${message}</span>`;
        elements.toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(10px)";
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    // Helper: Format seconds to MM:SS
    function formatTime(seconds) {
        if (isNaN(seconds) || seconds < 0) return "00:00";
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
    }

    // Helper: Hex to RGBA
    function hexToRgba(hex, alpha = 1.0) {
        hex = hex.replace("#", "");
        if (hex.length === 3) hex = hex.split("").map(c => c + c).join("");
        const num = parseInt(hex, 16);
        const r = (num >> 16) & 255;
        const g = (num >> 8) & 255;
        const b = num & 255;
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }

    // Update UI badge styling directly on the interactive element
    function updateBadgeVisuals() {
        const ov = state.textOverlay;
        const textContent = elements.badgeTextContent;

        // Show / hide the whole overlay
        elements.draggableBadge.style.display = state.showText ? "" : "none";

        // Text
        textContent.textContent = ov.text || "Nhập nội dung text...";

        // Font Family
        let fontCss = "'Be Vietnam Pro', sans-serif";
        if (ov.font_family === "Montserrat") fontCss = "'Montserrat', sans-serif";
        else if (ov.font_family === "Arial") fontCss = "Arial, sans-serif";
        else if (ov.font_family === "SegoeUI") fontCss = "'Segoe UI', sans-serif";
        else if (ov.font_family === "Times") fontCss = "'Times New Roman', serif";
        textContent.style.fontFamily = fontCss;

        // Colors & Background
        const bgRgba = hexToRgba(ov.bg_color, ov.bg_opacity);
        textContent.style.backgroundColor = bgRgba;
        textContent.style.color = ov.text_color;

        // Proportional scale factor between player viewport and target video dimensions
        const containerH = elements.videoContainer.clientHeight || 540;
        const targetH = state.videoHeight || 1280;
        const previewScale = Math.max(0.05, containerH / targetH);

        // Padding & Radius proportional to preview
        const displayPadX = Math.max(2, Math.round(ov.pad_x * previewScale));
        const displayPadY = Math.max(2, Math.round(ov.pad_y * previewScale));
        const displayRadius = Math.max(0, Math.round(ov.border_radius * previewScale));

        textContent.style.padding = `${displayPadY}px ${displayPadX}px`;
        textContent.style.borderRadius = `${displayRadius}px`;

        // Alignment & Natural Width
        textContent.style.textAlign = ov.align;
        elements.draggableBadge.style.width = "max-content";
        elements.draggableBadge.style.maxWidth = "96%";

        // Shadow
        if (ov.shadow && ov.bg_opacity > 0.05) {
            textContent.style.boxShadow = "0 6px 20px rgba(0,0,0,0.55)";
        } else {
            textContent.style.boxShadow = "none";
        }

        // Position
        elements.draggableBadge.style.left = `${ov.x_pct}%`;
        elements.draggableBadge.style.top = `${ov.y_pct}%`;
        elements.badgeCoordsTag.textContent = `X: ${Math.round(ov.x_pct)}% | Y: ${Math.round(ov.y_pct)}%`;

        // Sync manual position controls in Right Panel
        if (elements.sliderPosX) elements.sliderPosX.value = Math.round(ov.x_pct);
        if (elements.inputPosX && document.activeElement !== elements.inputPosX) {
            elements.inputPosX.value = Math.round(ov.x_pct);
        }
        if (elements.sliderPosY) elements.sliderPosY.value = Math.round(ov.y_pct);
        if (elements.inputPosY && document.activeElement !== elements.inputPosY) {
            elements.inputPosY.value = Math.round(ov.y_pct);
        }

        // Exact font size chosen by user without any auto-shrinking or word breaking
        const displayFontSize = Math.max(8, Math.round(ov.font_size * previewScale));
        textContent.style.fontSize = `${displayFontSize}px`;
    }

    // Drag and Drop Text Badge Implementation
    let isDragging = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let initialXPct = 50;
    let initialYPct = 80;

    function initBadgeDragging() {
        const badge = elements.draggableBadge;
        const container = elements.videoContainer;

        badge.addEventListener("pointerdown", (e) => {
            if (elements.checkEnableDrag && !elements.checkEnableDrag.checked) return;
            if (e.target.classList.contains("resize-handle")) return; // Handle resize separately
            isDragging = true;
            dragStartX = e.clientX;
            dragStartY = e.clientY;
            initialXPct = state.textOverlay.x_pct;
            initialYPct = state.textOverlay.y_pct;
            badge.classList.add("selected");
            badge.setPointerCapture(e.pointerId);
            e.stopPropagation();
        });

        badge.addEventListener("pointermove", (e) => {
            if (!isDragging) return;
            const containerRect = container.getBoundingClientRect();
            if (containerRect.width <= 0 || containerRect.height <= 0) return;

            const deltaX = e.clientX - dragStartX;
            const deltaY = e.clientY - dragStartY;

            let newXPct = initialXPct + (deltaX / containerRect.width) * 100;
            let newYPct = initialYPct + (deltaY / containerRect.height) * 100;

            // Axis Lock: Hold Shift to lock moving on a single straight axis (horizontal or vertical)
            if (e.shiftKey) {
                if (Math.abs(deltaX) > Math.abs(deltaY)) {
                    newYPct = initialYPct; // Lock Y when moving left/right
                } else {
                    newXPct = initialXPct; // Lock X when moving up/down
                }
            }

            // Clamping within video bounds
            newXPct = Math.max(5, Math.min(95, newXPct));
            newYPct = Math.max(5, Math.min(95, newYPct));

            // Visual guide lines when crossing center
            if (Math.abs(newXPct - 50) < 1.2) {
                elements.guideV.classList.add("active");
            } else {
                elements.guideV.classList.remove("active");
            }

            if (Math.abs(newYPct - 50) < 1.2) {
                elements.guideH.classList.add("active");
            } else {
                elements.guideH.classList.remove("active");
            }

            state.textOverlay.x_pct = Math.round(newXPct * 10) / 10;
            state.textOverlay.y_pct = Math.round(newYPct * 10) / 10;
            updateBadgeVisuals();
        });

        const stopDrag = (e) => {
            if (!isDragging) return;
            isDragging = false;
            elements.guideH.classList.remove("active");
            elements.guideV.classList.remove("active");
            badge.classList.remove("selected");
            try { badge.releasePointerCapture(e.pointerId); } catch (_) {}
        };

        badge.addEventListener("pointerup", stopDrag);
        badge.addEventListener("pointercancel", stopDrag);
    }

    // Presets handler
    elements.presetButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            elements.presetButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const preset = btn.dataset.preset;

            if (preset === "capcut-white") {
                state.textOverlay.bg_color = "#FFFFFF";
                state.textOverlay.text_color = "#000000";
                state.textOverlay.bg_opacity = 1.0;
                state.textOverlay.border_radius = 14;
            } else if (preset === "capcut-black") {
                state.textOverlay.bg_color = "#000000";
                state.textOverlay.text_color = "#FFFFFF";
                state.textOverlay.bg_opacity = 1.0;
                state.textOverlay.border_radius = 14;
            } else if (preset === "capcut-yellow") {
                state.textOverlay.bg_color = "#FACC15";
                state.textOverlay.text_color = "#000000";
                state.textOverlay.bg_opacity = 1.0;
                state.textOverlay.border_radius = 14;
            } else if (preset === "capcut-red") {
                state.textOverlay.bg_color = "#EF4444";
                state.textOverlay.text_color = "#FFFFFF";
                state.textOverlay.bg_opacity = 1.0;
                state.textOverlay.border_radius = 14;
            }

            // Sync inputs
            elements.inputBgColor.value = state.textOverlay.bg_color;
            elements.valBgColor.textContent = state.textOverlay.bg_color;
            elements.inputTextColor.value = state.textOverlay.text_color;
            elements.valTextColor.textContent = state.textOverlay.text_color;
            elements.sliderBgOpacity.value = Math.round(state.textOverlay.bg_opacity * 100);
            elements.valBgOpacity.textContent = `${Math.round(state.textOverlay.bg_opacity * 100)}%`;
            elements.sliderBorderRadius.value = state.textOverlay.border_radius;
            elements.valBorderRadius.textContent = `${state.textOverlay.border_radius} px`;

            updateBadgeVisuals();
        });
    });

    // Form Input Event Listeners
    elements.inputText.addEventListener("input", (e) => {
        state.textOverlay.text = e.target.value;
        updateBadgeVisuals();
    });

    elements.selectFont.addEventListener("change", (e) => {
        state.textOverlay.font_family = e.target.value;
        updateBadgeVisuals();
    });

    elements.sliderFontSize.addEventListener("input", (e) => {
        const val = parseInt(e.target.value);
        state.textOverlay.font_size = val;
        elements.valFontSize.textContent = `${val} px`;
        updateBadgeVisuals();
    });

    elements.alignButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            elements.alignButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            state.textOverlay.align = btn.dataset.align;
            updateBadgeVisuals();
        });
    });

    elements.inputBgColor.addEventListener("input", (e) => {
        state.textOverlay.bg_color = e.target.value;
        elements.valBgColor.textContent = e.target.value.toUpperCase();
        updateBadgeVisuals();
    });

    elements.inputTextColor.addEventListener("input", (e) => {
        state.textOverlay.text_color = e.target.value;
        elements.valTextColor.textContent = e.target.value.toUpperCase();
        updateBadgeVisuals();
    });

    elements.sliderBgOpacity.addEventListener("input", (e) => {
        const val = parseInt(e.target.value);
        state.textOverlay.bg_opacity = val / 100.0;
        elements.valBgOpacity.textContent = `${val}%`;
        updateBadgeVisuals();
    });

    elements.sliderBorderRadius.addEventListener("input", (e) => {
        const val = parseInt(e.target.value);
        state.textOverlay.border_radius = val;
        elements.valBorderRadius.textContent = `${val} px`;
        updateBadgeVisuals();
    });

    elements.sliderPadX.addEventListener("input", (e) => {
        const val = parseInt(e.target.value);
        state.textOverlay.pad_x = val;
        elements.valPadX.textContent = `${val} px`;
        updateBadgeVisuals();
    });

    elements.sliderPadY.addEventListener("input", (e) => {
        const val = parseInt(e.target.value);
        state.textOverlay.pad_y = val;
        elements.valPadY.textContent = `${val} px`;
        updateBadgeVisuals();
    });

    elements.sliderMaxWidth.addEventListener("input", (e) => {
        const val = parseInt(e.target.value);
        state.textOverlay.max_width_pct = val;
        elements.valMaxWidth.textContent = `${val}%`;
        updateBadgeVisuals();
    });

    elements.checkShadow.addEventListener("change", (e) => {
        state.textOverlay.shadow = e.target.checked;
        updateBadgeVisuals();
    });

    // Manual Position X & Y controls (Tự Chỉnh Tọa Độ X, Y)
    if (elements.sliderPosX) {
        elements.sliderPosX.addEventListener("input", (e) => {
            const val = parseFloat(e.target.value) || 0;
            state.textOverlay.x_pct = val;
            if (elements.inputPosX) elements.inputPosX.value = Math.round(val);
            updateBadgeVisuals();
        });
    }

    if (elements.inputPosX) {
        elements.inputPosX.addEventListener("input", (e) => {
            let val = parseFloat(e.target.value);
            if (isNaN(val)) val = 50;
            val = Math.max(0, Math.min(100, val));
            state.textOverlay.x_pct = val;
            if (elements.sliderPosX) elements.sliderPosX.value = Math.round(val);
            updateBadgeVisuals();
        });
    }

    if (elements.sliderPosY) {
        elements.sliderPosY.addEventListener("input", (e) => {
            const val = parseFloat(e.target.value) || 0;
            state.textOverlay.y_pct = val;
            if (elements.inputPosY) elements.inputPosY.value = Math.round(val);
            updateBadgeVisuals();
        });
    }

    if (elements.inputPosY) {
        elements.inputPosY.addEventListener("input", (e) => {
            let val = parseFloat(e.target.value);
            if (isNaN(val)) val = 80;
            val = Math.max(0, Math.min(100, val));
            state.textOverlay.y_pct = val;
            if (elements.sliderPosY) elements.sliderPosY.value = Math.round(val);
            updateBadgeVisuals();
        });
    }

    // Quick Position Buttons
    if (elements.btnPosTop) {
        elements.btnPosTop.addEventListener("click", () => {
            state.textOverlay.y_pct = 15.0;
            updateBadgeVisuals();
            showToast("Đã đặt vị trí phía trên (Y: 15%)", "info");
        });
    }

    if (elements.btnPosCenter) {
        elements.btnPosCenter.addEventListener("click", () => {
            state.textOverlay.x_pct = 50.0;
            state.textOverlay.y_pct = 50.0;
            updateBadgeVisuals();
            showToast("Đã căn chính giữa khung hình (50%, 50%)", "info");
        });
    }

    if (elements.btnPosBottom) {
        elements.btnPosBottom.addEventListener("click", () => {
            state.textOverlay.x_pct = 50.0;
            state.textOverlay.y_pct = 80.0;
            updateBadgeVisuals();
            showToast("Đã đặt vị trí dưới chuẩn CapCut (80%)", "info");
        });
    }

    if (elements.btnPosCenterX) {
        elements.btnPosCenterX.addEventListener("click", () => {
            state.textOverlay.x_pct = 50.0;
            updateBadgeVisuals();
            showToast("Đã căn giữa trục ngang (X: 50%)", "info");
        });
    }

    function setVolumePct(pct) {
        state.volumePct = pct;
        if (elements.sliderVolume) elements.sliderVolume.value = pct;
        if (elements.volumeValue) elements.volumeValue.textContent = pct === 100 ? "100% (gốc)" : `${pct}%`;
    }
    if (elements.sliderVolume) {
        elements.sliderVolume.addEventListener("input", (e) => setVolumePct(parseInt(e.target.value) || 0));
    }
    if (elements.btnVolumeReset) {
        elements.btnVolumeReset.addEventListener("click", () => setVolumePct(100));
    }

    function setVideoSpeed(val) {
        const speed = Math.max(0.25, Math.min(4.0, Math.round(parseFloat(val) * 100) / 100 || 1.0));
        state.speed = speed;
        if (elements.sliderSpeed) elements.sliderSpeed.value = speed;
        if (elements.speedValue) {
            elements.speedValue.textContent = Math.abs(speed - 1.0) < 0.001 ? "1.0x (gốc)" : `${speed}x`;
        }
        if (elements.speedChips) {
            elements.speedChips.forEach(chip => {
                const chipVal = parseFloat(chip.dataset.speed);
                chip.classList.toggle("active", Math.abs(chipVal - speed) < 0.001);
            });
        }
        if (elements.previewVideo) {
            elements.previewVideo.playbackRate = speed;
        }
    }
    if (elements.sliderSpeed) {
        elements.sliderSpeed.addEventListener("input", (e) => setVideoSpeed(e.target.value));
    }
    if (elements.btnSpeedReset) {
        elements.btnSpeedReset.addEventListener("click", () => setVideoSpeed(1.0));
    }
    if (elements.speedChips) {
        elements.speedChips.forEach(chip => {
            chip.addEventListener("click", () => setVideoSpeed(chip.dataset.speed));
        });
    }
    if (elements.previewVideo) {
        elements.previewVideo.addEventListener("loadedmetadata", () => {
            elements.previewVideo.playbackRate = state.speed;
        });
    }

    if (elements.selectQuality) {
        elements.selectQuality.addEventListener("change", (e) => {
            state.qualityCrf = parseInt(e.target.value) || 0;
        });
    }

    if (elements.selectUpscaleMode) {
        elements.selectUpscaleMode.addEventListener("change", (e) => {
            state.upscaleMode = e.target.value || "none";
            if (elements.upscaleModeHint) {
                if (state.upscaleMode === "ai") {
                    elements.upscaleModeHint.textContent = "AI sẽ phóng to 4x rồi đưa về kích thước xuất (chậm hơn nhưng nét nhất, cần GPU Vulkan).";
                } else if (state.upscaleMode === "fast") {
                    elements.upscaleModeHint.textContent = "Dùng bộ lọc Lanczos + Contrast Adaptive Sharpen (CAS), chạy nhanh trên mọi máy.";
                } else {
                    elements.upscaleModeHint.textContent = "Đang tắt: giữ nguyên xử lý gốc (nhanh nhất, không dùng AI làm nét).";
                }
            }
        });
        // Check whether embedded AI upscaler is available
        fetch("/api/capabilities")
            .then(r => r.json())
            .then(cap => {
                if (!cap.ai_upscale_available && elements.optUpscaleAi) {
                    elements.optUpscaleAi.textContent = "AI Super-Resolution (Chưa có realesrgan-ncnn-vulkan)";
                    elements.optUpscaleAi.disabled = true;
                }
            })
            .catch(() => {});
    }

    if (elements.checkShowText) {
        elements.checkShowText.addEventListener("change", (e) => {
            state.showText = e.target.checked;
            updateBadgeVisuals();
            showToast(state.showText ? "Đã hiện chữ trên video" : "Đã ẩn chữ trên video (sẽ không chèn khi xuất file)", "info");
        });
    }

    if (elements.checkEnableDrag) {
        elements.checkEnableDrag.addEventListener("change", (e) => {
            if (e.target.checked) {
                elements.draggableBadge.style.cursor = "grab";
                showToast("Đã bật chế độ kéo thả trên màn hình video", "info");
            } else {
                elements.draggableBadge.style.cursor = "default";
                showToast("Đã khóa kéo trên video (chỉ chỉnh tọa độ bằng ô nhập)", "info");
            }
        });
    }

    // Timing radios
    elements.timingRadios.forEach(radio => {
        radio.addEventListener("change", (e) => {
            if (e.target.value === "custom") {
                state.textOverlay.full_duration = false;
                elements.timingCustomFields.style.display = "block";
            } else {
                state.textOverlay.full_duration = true;
                elements.timingCustomFields.style.display = "none";
            }
        });
    });

    elements.inputStartTime.addEventListener("input", (e) => {
        state.textOverlay.start = parseFloat(e.target.value) || 0;
    });

    elements.inputEndTime.addEventListener("input", (e) => {
        state.textOverlay.end = parseFloat(e.target.value) || 0;
    });

    elements.btnSetStartCurrent.addEventListener("click", () => {
        const cur = elements.previewVideo.currentTime || 0;
        const val = Math.round(cur * 10) / 10;
        elements.inputStartTime.value = val;
        state.textOverlay.start = val;
        showToast(`Đã đặt mốc bắt đầu: ${val}s`, "info");
    });

    elements.btnSetEndCurrent.addEventListener("click", () => {
        const cur = elements.previewVideo.currentTime || 0;
        const val = Math.round(cur * 10) / 10;
        elements.inputEndTime.value = val;
        state.textOverlay.end = val;
        showToast(`Đã đặt mốc kết thúc: ${val}s`, "info");
    });

    // Quick snap tools
    elements.btnSnapCenter.addEventListener("click", () => {
        state.textOverlay.x_pct = 50.0;
        updateBadgeVisuals();
        showToast("Đã căn giữa ngang", "info");
    });

    elements.btnResetPosition.addEventListener("click", () => {
        state.textOverlay.x_pct = 50.0;
        state.textOverlay.y_pct = 80.0;
        state.textOverlay.max_width_pct = 85;
        elements.sliderMaxWidth.value = 85;
        elements.valMaxWidth.textContent = "85%";
        updateBadgeVisuals();
        showToast("Đã đặt lại vị trí tiêu chuẩn", "info");
    });

    // Custom Resolution X, Y & Fit Mode Change
    function updateCanvasDimensions() {
        let w = parseInt(elements.inputVideoWidth ? elements.inputVideoWidth.value : 720) || 720;
        let h = parseInt(elements.inputVideoHeight ? elements.inputVideoHeight.value : 1280) || 1280;
        if (w % 2 !== 0) w += 1;
        if (h % 2 !== 0) h += 1;
        state.videoWidth = w;
        state.videoHeight = h;

        elements.videoContainer.style.setProperty("--player-aspect-ratio", `${w} / ${h}`);
        elements.videoContainer.style.aspectRatio = `${w} / ${h}`;
        elements.canvasSummaryText.textContent = `${w} × ${h}`;

        // Fit mode visual on video preview
        if (state.fitMode === "stretch") {
            elements.previewVideo.style.objectFit = "fill";
        } else if (state.fitMode === "cover") {
            elements.previewVideo.style.objectFit = "cover";
        } else {
            elements.previewVideo.style.objectFit = "contain";
        }

        // Highlight matching chip if any
        elements.resChips.forEach(chip => {
            const chipW = parseInt(chip.dataset.w);
            const chipH = parseInt(chip.dataset.h);
            if (chipW === w && chipH === h) {
                chip.classList.add("active");
            } else if (chip.dataset.mode !== "original") {
                chip.classList.remove("active");
            }
        });

        updateBadgeVisuals();
    }

    if (elements.inputVideoWidth && elements.inputVideoHeight) {
        elements.inputVideoWidth.addEventListener("input", () => {
            elements.resChips.forEach(c => c.classList.remove("active"));
            updateCanvasDimensions();
        });
        elements.inputVideoHeight.addEventListener("input", () => {
            elements.resChips.forEach(c => c.classList.remove("active"));
            updateCanvasDimensions();
        });
    }

    elements.resChips.forEach(chip => {
        chip.addEventListener("click", () => {
            if (chip.dataset.mode === "original") {
                if (state.clips.length > 0) {
                    const c = state.clips[0];
                    elements.inputVideoWidth.value = c.width;
                    elements.inputVideoHeight.value = c.height;
                    elements.resChips.forEach(btn => btn.classList.remove("active"));
                    chip.classList.add("active");
                    updateCanvasDimensions();
                    showToast(`Đã áp dụng kích thước gốc: ${c.width} × ${c.height}`, "info");
                } else {
                    showToast("Chưa có video nào để lấy kích thước gốc", "info");
                }
                return;
            }
            const w = parseInt(chip.dataset.w);
            const h = parseInt(chip.dataset.h);
            if (w && h) {
                elements.inputVideoWidth.value = w;
                elements.inputVideoHeight.value = h;
                elements.resChips.forEach(btn => btn.classList.remove("active"));
                chip.classList.add("active");
                updateCanvasDimensions();
            }
        });
    });

    if (elements.selectFitMode) {
        elements.selectFitMode.addEventListener("change", (e) => {
            state.fitMode = e.target.value;
            if (state.fitMode === "stretch") {
                elements.previewVideo.style.objectFit = "fill";
            } else if (state.fitMode === "cover") {
                elements.previewVideo.style.objectFit = "cover";
            } else {
                elements.previewVideo.style.objectFit = "contain";
            }
        });
    }

    function updateCanvasAspectRatio() {
        updateCanvasDimensions();
    }

    // Video Player Timeline & Controls
    const video = elements.previewVideo;

    elements.btnPlayPause.addEventListener("click", togglePlay);
    document.addEventListener("keydown", (e) => {
        if (e.code === "Space" && e.target.tagName !== "INPUT" && e.target.tagName !== "TEXTAREA") {
            e.preventDefault();
            togglePlay();
        }
    });

    function togglePlay() {
        if (video.paused || video.ended) {
            video.play();
        } else {
            video.pause();
        }
    }

    video.addEventListener("play", () => {
        state.isPlaying = true;
        elements.playIcon.textContent = "⏸";
    });

    video.addEventListener("pause", () => {
        state.isPlaying = false;
        elements.playIcon.textContent = "▶";
    });

    video.addEventListener("timeupdate", () => {
        elements.currentTimeDisplay.textContent = formatTime(video.currentTime);
        if (video.duration) {
            const pct = (video.currentTime / video.duration) * 100;
            elements.timelineFill.style.width = `${pct}%`;
            elements.timelineThumb.style.left = `${pct}%`;
        }

        // Timing visibility check
        if (!state.textOverlay.full_duration) {
            const t = video.currentTime;
            if (t >= state.textOverlay.start && t <= state.textOverlay.end) {
                elements.draggableBadge.style.opacity = "1";
            } else {
                elements.draggableBadge.style.opacity = "0.2"; // Dim when out of range in editor
            }
        } else {
            elements.draggableBadge.style.opacity = "1";
        }
    });

    video.addEventListener("loadedmetadata", () => {
        elements.totalDurationDisplay.textContent = formatTime(video.duration);
        updateCanvasAspectRatio();
    });

    video.addEventListener("ended", () => {
        // Auto-play next clip if available
        if (state.activeClipIndex < state.clips.length - 1) {
            selectClip(state.activeClipIndex + 1);
            video.play();
        }
    });

    // Timeline Scrubber
    let isSeeking = false;
    elements.timelineBar.addEventListener("pointerdown", (e) => {
        isSeeking = true;
        seekTo(e);
        elements.timelineBar.setPointerCapture(e.pointerId);
    });

    elements.timelineBar.addEventListener("pointermove", (e) => {
        if (isSeeking) seekTo(e);
    });

    const stopSeek = (e) => {
        if (isSeeking) {
            isSeeking = false;
            try { elements.timelineBar.releasePointerCapture(e.pointerId); } catch (_) {}
        }
    };
    elements.timelineBar.addEventListener("pointerup", stopSeek);
    elements.timelineBar.addEventListener("pointercancel", stopSeek);

    function seekTo(e) {
        if (!video.duration) return;
        const rect = elements.timelineBar.getBoundingClientRect();
        const clickX = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
        const pct = clickX / rect.width;
        video.currentTime = pct * video.duration;
    }

    elements.btnMuteToggle.addEventListener("click", () => {
        video.muted = !video.muted;
        elements.muteIcon.textContent = video.muted ? "🔇" : "🔊";
    });

    // Clip Selection & Management
    function selectClip(index) {
        if (index < 0 || index >= state.clips.length) return;
        state.activeClipIndex = index;
        const clip = state.clips[index];

        elements.playerPlaceholder.style.display = "none";
        video.src = `/api/video-stream?path=${encodeURIComponent(clip.path)}`;
        video.load();
        elements.currentClipName.textContent = clip.name;

        // Render clip list active state
        renderClipsList();
    }

    function renderClipsList() {
        if (elements.tabBadgeClips) {
            elements.tabBadgeClips.textContent = state.clips.length;
        }
        if (elements.trayClipCount) {
            elements.trayClipCount.textContent = `${state.clips.length} clip`;
        }

        if (state.clips.length === 0) {
            elements.emptyState.style.display = "block";
            elements.clipsList.innerHTML = "";
            elements.clipsList.appendChild(elements.emptyState);
            elements.playerPlaceholder.style.display = "flex";
            elements.clipCountText.textContent = "0 video";
            elements.totalDurationText.textContent = "00:00";
            if (elements.clipsStatsText) elements.clipsStatsText.textContent = "Đang có 0 video";
            if (elements.clipsTotalDurText) elements.clipsTotalDurText.textContent = "00:00";
            if (elements.mediaStripList) {
                elements.mediaStripList.innerHTML = `<div class="empty-tray-msg">Chưa có video nào. Nhấn "Thêm Video Từ Máy Tính" ở cột trái để bắt đầu.</div>`;
            }
            return;
        }

        elements.emptyState.style.display = "none";
        elements.clipsList.innerHTML = "";
        if (elements.mediaStripList) {
            elements.mediaStripList.innerHTML = "";
        }

        let totalSeconds = 0;

        state.clips.forEach((clip, index) => {
            totalSeconds += clip.duration;

            // 1. Left Panel Playlist Card
            const card = document.createElement("div");
            card.className = `clip-card ${index === state.activeClipIndex ? "active" : ""}`;
            card.innerHTML = `
                <div class="clip-index">#${index + 1}</div>
                <div class="clip-thumb-box">
                    <img src="${clip.thumbnail_url}" alt="thumb" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'100\\' height=\\'100\\' fill=\\'%23333\\'><rect width=\\'100\\' height=\\'100\\'/></svg>'">
                    <span class="clip-thumb-badge">${formatTime(clip.duration)}</span>
                </div>
                <div class="clip-info">
                    <div class="clip-title" title="${clip.name}">${clip.name}</div>
                    <div class="clip-meta">
                        <span>${clip.width}x${clip.height}</span>
                        <span>•</span>
                        <span>${clip.has_audio ? "Có tiếng" : "Không tiếng"}</span>
                    </div>
                </div>
                <div class="clip-controls">
                    <button class="clip-btn btn-up" title="Di chuyển lên" ${index === 0 ? "disabled style='opacity:0.3'" : ""}>▲</button>
                    <button class="clip-btn btn-down" title="Di chuyển xuống" ${index === state.clips.length - 1 ? "disabled style='opacity:0.3'" : ""}>▼</button>
                    <button class="clip-btn btn-del" title="Xóa clip này">🗑️</button>
                </div>
            `;

            // Click card to select & play
            card.addEventListener("click", (e) => {
                if (e.target.closest(".clip-controls")) return;
                selectClip(index);
            });

            // Reorder & Delete buttons
            card.querySelector(".btn-up").addEventListener("click", (e) => {
                e.stopPropagation();
                if (index > 0) {
                    const temp = state.clips[index];
                    state.clips[index] = state.clips[index - 1];
                    state.clips[index - 1] = temp;
                    if (state.activeClipIndex === index) state.activeClipIndex = index - 1;
                    else if (state.activeClipIndex === index - 1) state.activeClipIndex = index;
                    renderClipsList();
                    updateCanvasAspectRatio();
                }
            });

            card.querySelector(".btn-down").addEventListener("click", (e) => {
                e.stopPropagation();
                if (index < state.clips.length - 1) {
                    const temp = state.clips[index];
                    state.clips[index] = state.clips[index + 1];
                    state.clips[index + 1] = temp;
                    if (state.activeClipIndex === index) state.activeClipIndex = index + 1;
                    else if (state.activeClipIndex === index + 1) state.activeClipIndex = index;
                    renderClipsList();
                    updateCanvasAspectRatio();
                }
            });

            card.querySelector(".btn-del").addEventListener("click", (e) => {
                e.stopPropagation();
                state.clips.splice(index, 1);
                if (state.activeClipIndex >= state.clips.length) {
                    state.activeClipIndex = Math.max(0, state.clips.length - 1);
                }
                renderClipsList();
                if (state.clips.length > 0) {
                    selectClip(state.activeClipIndex);
                } else {
                    elements.playerPlaceholder.style.display = "flex";
                    video.removeAttribute("src");
                    video.load();
                }
                updateCanvasAspectRatio();
            });

            elements.clipsList.appendChild(card);

            // 2. Center Panel Bottom Media Strip Card (Always-visible sequence)
            if (elements.mediaStripList) {
                const stripCard = document.createElement("div");
                stripCard.className = `strip-card ${index === state.activeClipIndex ? "active" : ""}`;
                stripCard.title = `${index + 1}. ${clip.name} (${formatTime(clip.duration)})`;
                stripCard.innerHTML = `
                    <span class="strip-num">#${index + 1}</span>
                    <img src="${clip.thumbnail_url}" class="strip-thumb" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'56\\' height=\\'56\\' fill=\\'%23333\\'><rect width=\\'56\\' height=\\'56\\'/></svg>'">
                    <div class="strip-info">
                        <span class="strip-name">${clip.name}</span>
                        <span class="strip-duration">${formatTime(clip.duration)}</span>
                    </div>
                `;
                stripCard.addEventListener("click", () => {
                    selectClip(index);
                });
                elements.mediaStripList.appendChild(stripCard);
            }
        });

        elements.clipCountText.textContent = `${state.clips.length} video`;
        elements.totalDurationText.textContent = formatTime(totalSeconds);
        if (elements.clipsStatsText) elements.clipsStatsText.textContent = `Đang có ${state.clips.length} video`;
        if (elements.clipsTotalDurText) elements.clipsTotalDurText.textContent = formatTime(totalSeconds);
        elements.inputEndTime.value = Math.round(totalSeconds * 10) / 10;
        state.textOverlay.end = Math.round(totalSeconds * 10) / 10;
        updateBatchSummary();
    }

    // Batch Merge Logic & Summary Calculation
    function updateBatchSummary() {
        const total = state.clips.length;
        const n = state.chunkSize;
        const full = Math.floor(total / n);
        const rem = total % n;
        const totalOutputs = full + (rem > 0 && state.handleRemainder === "merge" ? 1 : 0);

        elements.chunkSizeDisplay.textContent = `${n} clip / video`;
        elements.chunkSizeInput.value = n;

        elements.chunkChips.forEach(chip => {
            if (parseInt(chip.dataset.chunk) === n) {
                chip.classList.add("active");
            } else {
                chip.classList.remove("active");
            }
        });

        if (state.mergeMode === "single") {
            elements.batchSettingsBox.style.display = "none";
            elements.btnExportVideo.innerHTML = `<span class="btn-icon">🚀</span> Ghép & Xuất (${total > 0 ? "1 Video" : "Video"})`;
        } else {
            elements.batchSettingsBox.style.display = "flex";
            if (total > 0) {
                elements.batchSummaryPill.innerHTML = `📦 Dự kiến: <b>${total} clip</b> ➔ <b>${totalOutputs} video riêng</b> (mỗi video ${n} clip${rem > 0 ? `, video cuối ${rem} clip` : ""})`;
                elements.btnExportVideo.innerHTML = `<span class="btn-icon">🚀</span> Ghép Hàng Loạt (${totalOutputs} Video)`;
            } else {
                elements.batchSummaryPill.innerHTML = `📦 Dự kiến xuất: <span>0 video riêng biệt</span>`;
                elements.btnExportVideo.innerHTML = `<span class="btn-icon">🚀</span> Ghép Hàng Loạt (N Video)`;
            }
        }
    }

    // Batch Event Listeners
    elements.mergeModeRadios.forEach(radio => {
        radio.addEventListener("change", (e) => {
            state.mergeMode = e.target.value;
            updateBatchSummary();
        });
    });

    elements.chunkSizeInput.addEventListener("input", (e) => {
        const val = Math.max(1, parseInt(e.target.value) || 1);
        state.chunkSize = val;
        updateBatchSummary();
    });

    elements.btnChunkMinus.addEventListener("click", () => {
        state.chunkSize = Math.max(1, state.chunkSize - 1);
        updateBatchSummary();
    });

    elements.btnChunkPlus.addEventListener("click", () => {
        state.chunkSize += 1;
        updateBatchSummary();
    });

    elements.chunkChips.forEach(chip => {
        chip.addEventListener("click", () => {
            state.chunkSize = parseInt(chip.dataset.chunk);
            updateBatchSummary();
        });
    });

    elements.selectRemainder.addEventListener("change", (e) => {
        state.handleRemainder = e.target.value;
        updateBatchSummary();
    });

    // Left Panel Tabs Switching (Clips Playlist vs Export Settings)
    if (elements.tabBtnClips && elements.tabBtnSettings) {
        elements.tabBtnClips.addEventListener("click", () => {
            elements.tabBtnClips.classList.add("active");
            elements.tabBtnSettings.classList.remove("active");
            if (elements.tabPanelClips) elements.tabPanelClips.style.display = "flex";
            if (elements.tabPanelSettings) elements.tabPanelSettings.style.display = "none";
        });

        elements.tabBtnSettings.addEventListener("click", () => {
            elements.tabBtnSettings.classList.add("active");
            elements.tabBtnClips.classList.remove("active");
            if (elements.tabPanelClips) elements.tabPanelClips.style.display = "none";
            if (elements.tabPanelSettings) elements.tabPanelSettings.style.display = "flex";
        });
    }

    // Video Import Progress Dialog Helpers
    function showImportModal(total) {
        if (elements.importModal) {
            elements.importCountTag.textContent = `Đang xử lý 1 / ${total} video`;
            elements.importPercentTag.textContent = `0%`;
            elements.importProgressFill.style.width = `0%`;
            elements.importCurrentFilename.textContent = `Đang chuẩn bị...`;
            elements.importStatusText.textContent = `Đang phân tích khung hình & tạo ảnh đại diện...`;
            elements.importModal.classList.add("active");
        }
    }

    function updateImportProgress(current, total, filename) {
        if (elements.importModal) {
            const pct = Math.round((current / total) * 100);
            elements.importCountTag.textContent = `Đang xử lý ${current} / ${total} video`;
            elements.importPercentTag.textContent = `${pct}%`;
            elements.importProgressFill.style.width = `${pct}%`;
            elements.importCurrentFilename.textContent = filename || "";
            elements.importStatusText.textContent = `Đang phân tích khung hình & tạo ảnh đại diện...`;
        }
    }

    function hideImportModal() {
        if (elements.importModal) {
            elements.importModal.classList.remove("active");
        }
    }

    // Browse files via Native Windows Dialog (No CMD flashes + Real-time Progress Dialog)
    async function browseFiles() {
        try {
            // Step 1: Open file picker directly
            const resp = await fetch("/api/select-files", { method: "POST" });
            const data = await resp.json();
            if (!data.success || !data.files || data.files.length === 0) {
                return; // User canceled dialog
            }

            const filePaths = data.files;
            const total = filePaths.length;
            showImportModal(total);

            const newClips = [];
            const prevCount = state.clips.length;

            for (let i = 0; i < total; i++) {
                const fp = filePaths[i];
                const filename = fp.split(/[\\/]/).pop();
                updateImportProgress(i + 1, total, filename);

                try {
                    const fileResp = await fetch("/api/import-file-path", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ path: fp })
                    });
                    const fileData = await fileResp.json();
                    if (fileData.success && fileData.clip) {
                        newClips.push(fileData.clip);
                    }
                } catch (err) {
                    console.error("Import clip error:", err);
                }
            }

            hideImportModal();

            if (newClips.length > 0) {
                state.clips.push(...newClips);
                renderClipsList();
                if (prevCount === 0) {
                    selectClip(0);
                }
                showToast(`Đã thêm thành công ${newClips.length} video!`, "success");
            }
        } catch (err) {
            console.error("Browse files error:", err);
            hideImportModal();
            showToast("Lỗi khi chọn tập tin video", "error");
        }
    }

    elements.btnBrowseFiles.addEventListener("click", browseFiles);
    elements.btnEmptyBrowse.addEventListener("click", browseFiles);

    // Drag and Drop Uploads (No CMD flashes + Real-time Progress Dialog)
    const dropzone = elements.dropzone;

    ["dragenter", "dragover"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.add("dragover");
        });
    });

    ["dragleave", "drop"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.remove("dragover");
        });
    });

    dropzone.addEventListener("drop", (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            uploadFiles(files);
        }
    });

    dropzone.addEventListener("click", () => {
        elements.fileUploadInput.click();
    });

    elements.fileUploadInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            uploadFiles(e.target.files);
        }
    });

    async function uploadFiles(files) {
        const validFiles = [];
        for (let i = 0; i < files.length; i++) {
            if (files[i].type.startsWith("video/") || files[i].name.match(/\.(mp4|mov|avi|mkv|webm|m4v|flv|wmv)$/i)) {
                validFiles.push(files[i]);
            }
        }

        if (validFiles.length === 0) {
            showToast("Vui lòng chọn tập tin video hợp lệ", "error");
            return;
        }

        const total = validFiles.length;
        showImportModal(total);

        const newClips = [];
        const prevCount = state.clips.length;

        for (let i = 0; i < total; i++) {
            const f = validFiles[i];
            updateImportProgress(i + 1, total, f.name);

            try {
                const formData = new FormData();
                formData.append("file", f);
                const resp = await fetch("/api/upload-single", {
                    method: "POST",
                    body: formData
                });
                const data = await resp.json();
                if (data.success && data.clip) {
                    newClips.push(data.clip);
                }
            } catch (err) {
                console.error("Upload single error:", err);
            }
        }

        hideImportModal();

        if (newClips.length > 0) {
            state.clips.push(...newClips);
            renderClipsList();
            if (prevCount === 0) {
                selectClip(0);
            }
            showToast(`Đã tải lên và thêm thành công ${newClips.length} video!`, "success");
        }
    }

    // Open Output Folder in Explorer
    elements.btnOpenFolder.addEventListener("click", async () => {
        try {
            await fetch("/api/open-folder", { method: "POST" });
            showToast("Đã mở thư mục xuất trong File Explorer", "success");
        } catch (err) {
            showToast("Không thể mở thư mục", "error");
        }
    });

    elements.btnOpenFinishedFolder.addEventListener("click", async () => {
        try {
            const path = elements.btnOpenFinishedFolder.dataset.path;
            await fetch("/api/open-folder", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path: path })
            });
        } catch (err) {
            showToast("Không thể mở thư mục", "error");
        }
    });

    if (elements.btnOpenSingleFile) {
        elements.btnOpenSingleFile.addEventListener("click", async () => {
            try {
                const path = elements.btnOpenFinishedFolder.dataset.path;
                await fetch("/api/open-folder", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ path: path })
                });
            } catch (err) {
                showToast("Không thể mở file trong thư mục", "error");
            }
        });
    }

    // Export Processing & Modal Logic
    elements.btnExportVideo.addEventListener("click", async () => {
        if (state.clips.length === 0) {
            showToast("Vui lòng thêm ít nhất một video để ghép!", "error");
            return;
        }

        // Open modal
        elements.modalProgressView.style.display = "flex";
        elements.modalFinishedView.style.display = "none";
        elements.exportModal.classList.add("active");
        setProgress(5, "Đang chuẩn bị danh sách các video...");

        try {
            const payload = {
                clips: state.clips,
                overlays: state.showText ? [state.textOverlay] : [],
                canvas_mode: "custom",
                fit_mode: state.fitMode,
                custom_w: parseInt(elements.inputVideoWidth ? elements.inputVideoWidth.value : state.videoWidth) || 720,
                custom_h: parseInt(elements.inputVideoHeight ? elements.inputVideoHeight.value : state.videoHeight) || 1280,
                crf: state.qualityCrf,
                upscale_mode: state.upscaleMode,
                volume: state.volumePct / 100,
                speed: state.speed,
                merge_mode: state.mergeMode,
                chunk_size: state.chunkSize,
                handle_remainder: state.handleRemainder,
                file_prefix: (elements.inputFilePrefix && elements.inputFilePrefix.value.trim()) || "export_final"
            };

            const resp = await fetch("/api/export", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await resp.json();
            if (!data.success) {
                showToast(data.error || "Lỗi khởi tạo quá trình xuất", "error");
                elements.exportModal.classList.remove("active");
                return;
            }

            state.exportTaskId = data.task_id;
            startPollingProgress();

        } catch (err) {
            console.error("Export error:", err);
            showToast("Lỗi kết nối máy chủ", "error");
            elements.exportModal.classList.remove("active");
        }
    });

    function setProgress(pct, msg) {
        elements.progressPercentage.textContent = `${pct}%`;
        elements.progressMessage.textContent = msg;

        // SVG circle stroke-dashoffset (circumference is 2 * PI * 52 = 326.72)
        const circumference = 326.72;
        const offset = circumference - (pct / 100.0) * circumference;
        elements.progressCircle.style.strokeDashoffset = offset;
    }

    function startPollingProgress() {
        if (state.pollInterval) clearInterval(state.pollInterval);

        state.pollInterval = setInterval(async () => {
            if (!state.exportTaskId) return;

            try {
                const resp = await fetch(`/api/progress/${state.exportTaskId}`);
                const data = await resp.json();

                if (data.status === "processing") {
                    setProgress(data.progress || 10, data.message || "Đang xử lý...");
                } else if (data.status === "completed") {
                    clearInterval(state.pollInterval);
                    setProgress(100, "Hoàn tất!");
                    setTimeout(() => {
                        showFinishedModal(data);
                    }, 400);
                } else if (data.status === "failed") {
                    clearInterval(state.pollInterval);
                    showToast(data.error || "Quá trình xuất video thất bại", "error");
                    elements.exportModal.classList.remove("active");
                }
            } catch (err) {
                console.error("Poll error:", err);
            }
        }, 500);
    }

    function showFinishedModal(data) {
        elements.modalProgressView.style.display = "none";
        elements.modalFinishedView.style.display = "flex";

        const outputs = data.outputs || [];
        const firstUrl = data.output_url || (outputs[0] && outputs[0].url);
        const firstPath = data.output_path || (outputs[0] && outputs[0].path);

        elements.btnOpenFinishedFolder.dataset.path = firstPath;

        if (outputs.length > 1) {
            // Batch Mode results view
            elements.finishedBadgeText.textContent = `✅ Đã xuất thành công ${outputs.length} video riêng biệt!`;
            elements.singleFinishedActions.style.display = "none";
            elements.batchOutputsContainer.style.display = "flex";
            elements.batchOutputCountTag.textContent = `${outputs.length} video`;

            elements.batchOutputsList.innerHTML = "";
            outputs.forEach(out => {
                const item = document.createElement("div");
                item.className = "batch-output-item";
                item.innerHTML = `
                    <div class="batch-item-left">
                        <span class="batch-part-badge">Video #${out.part}</span>
                        <div>
                            <div class="batch-item-title">${out.name}</div>
                            <div class="batch-item-meta">${out.clip_count} clip • ${formatTime(out.duration)}</div>
                        </div>
                    </div>
                    <div class="batch-item-actions">
                        <button class="btn-batch-play" title="Xem trước video này">▶ Xem</button>
                        <button class="btn-batch-open" title="Định vị file trong thư mục Explorer">📁 Mở</button>
                    </div>
                `;

                item.querySelector(".btn-batch-play").addEventListener("click", () => {
                    elements.finishedVideoPlayer.src = out.url;
                    elements.finishedVideoPlayer.load();
                    elements.finishedVideoPlayer.play();
                });

                item.querySelector(".btn-batch-open").addEventListener("click", async () => {
                    try {
                        await fetch("/api/open-folder", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ path: out.path })
                        });
                    } catch (err) {
                        showToast("Không thể mở file trong thư mục", "error");
                    }
                });

                elements.batchOutputsList.appendChild(item);
            });
        } else {
            // Single Mode result view
            elements.finishedBadgeText.textContent = "✅ Xuất video thành công!";
            elements.singleFinishedActions.style.display = "block";
            elements.batchOutputsContainer.style.display = "none";
        }

        elements.finishedVideoPlayer.src = firstUrl;
        elements.finishedVideoPlayer.load();
    }

    elements.btnModalClose.addEventListener("click", () => {
        elements.exportModal.classList.remove("active");
        elements.finishedVideoPlayer.pause();
    });

    // Webhook API Modal Logic
    const btnWebhookApi = document.getElementById("btnWebhookApi");
    const webhookModal = document.getElementById("webhookModal");
    const btnWebhookModalClose = document.getElementById("btnWebhookModalClose");
    const webhookStatusBadge = document.getElementById("webhookStatusBadge");
    const webhookBaseUrl = document.getElementById("webhookBaseUrl");
    const btnCopyWebhookUrl = document.getElementById("btnCopyWebhookUrl");
    const btnToggleWebhook = document.getElementById("btnToggleWebhook");
    const webhookApiKey = document.getElementById("webhookApiKey");
    const webhookKeyHint = document.getElementById("webhookKeyHint");
    const btnCopyApiKey = document.getElementById("btnCopyApiKey");
    const btnRegenApiKey = document.getElementById("btnRegenApiKey");
    const webhookStorageInfo = document.getElementById("webhookStorageInfo");
    const btnRefreshWebhookInfo = document.getElementById("btnRefreshWebhookInfo");
    const btnCleanupOldOutputs = document.getElementById("btnCleanupOldOutputs");
    const btnOpenWebhookDocs = document.getElementById("btnOpenWebhookDocs");
    let currentWebhookEnabled = true;
    let lastRawApiKey = "";

    async function loadWebhookConfig(postBody = null) {
        try {
            const resp = await fetch("/api/webhook/config", postBody ? {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(postBody)
            } : {});
            const cfg = await resp.json();
            currentWebhookEnabled = !!cfg.api_enabled;
            if (webhookBaseUrl) webhookBaseUrl.value = cfg.base_url || "";
            if (cfg.new_api_key) {
                lastRawApiKey = cfg.new_api_key;
                if (webhookApiKey) webhookApiKey.value = cfg.new_api_key;
                if (webhookKeyHint) webhookKeyHint.innerHTML = "✅ <b>Đã tạo API Key mới!</b> Hãy bấm <b>Sao chép</b> ngay (lần sau mở lại app khóa sẽ được che bảo mật).";
            } else if (webhookApiKey) {
                webhookApiKey.value = lastRawApiKey || cfg.api_key_preview || "";
            }
            if (webhookStatusBadge) {
                webhookStatusBadge.textContent = currentWebhookEnabled ? "● API đang bật" : "○ API đang tắt";
                webhookStatusBadge.style.color = currentWebhookEnabled ? "#22c55e" : "#f87171";
            }
            if (btnToggleWebhook) {
                btnToggleWebhook.textContent = currentWebhookEnabled ? "Tạm tắt API" : "Bật lại API";
            }
            if (webhookStorageInfo && cfg.storage) {
                webhookStorageInfo.textContent = `${cfg.storage.file_count} file · ${cfg.storage.total_mb} MB (Hàng đợi: ${cfg.queue_size || 0})`;
            }
        } catch (err) {
            showToast("Không thể tải cấu hình Webhook API", "error");
        }
    }

    if (btnWebhookApi && webhookModal) {
        btnWebhookApi.addEventListener("click", () => {
            webhookModal.classList.add("active");
            loadWebhookConfig();
        });
    }
    if (btnWebhookModalClose && webhookModal) {
        btnWebhookModalClose.addEventListener("click", () => webhookModal.classList.remove("active"));
    }
    if (btnCopyWebhookUrl && webhookBaseUrl) {
        btnCopyWebhookUrl.addEventListener("click", () => {
            navigator.clipboard.writeText(webhookBaseUrl.value);
            showToast("Đã sao chép URL Webhook API", "success");
        });
    }
    if (btnCopyApiKey && webhookApiKey) {
        btnCopyApiKey.addEventListener("click", () => {
            if (!lastRawApiKey && webhookApiKey.value.includes("••••")) {
                showToast("Khóa cũ đã được mã hóa che bớt — hãy bấm 'Tạo API Key riêng' để lấy khóa mới!", "info");
                return;
            }
            navigator.clipboard.writeText(lastRawApiKey || webhookApiKey.value);
            showToast("Đã sao chép X-API-Key", "success");
        });
    }
    if (btnToggleWebhook) {
        btnToggleWebhook.addEventListener("click", () => loadWebhookConfig({ api_enabled: !currentWebhookEnabled }));
    }
    if (btnRegenApiKey) {
        btnRegenApiKey.addEventListener("click", async () => {
            await loadWebhookConfig({ regenerate_key: true });
            showToast("Đã tạo khóa X-API-Key mới!", "success");
        });
    }
    if (btnRefreshWebhookInfo) {
        btnRefreshWebhookInfo.addEventListener("click", () => loadWebhookConfig());
    }
    if (btnCleanupOldOutputs) {
        btnCleanupOldOutputs.addEventListener("click", async () => {
            const resp = await fetch("/api/webhook/cleanup", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ older_than_hours: 24 })
            });
            const data = await resp.json();
            showToast(`Đã xóa ${data.deleted || 0} file cũ hơn 24 giờ`, "info");
            loadWebhookConfig();
        });
    }
    if (btnOpenWebhookDocs) {
        btnOpenWebhookDocs.addEventListener("click", () => {
            window.open("/api/v1/docs", "_blank");
        });
    }

    // Initialize interactive modules
    initBadgeDragging();
    updateBadgeVisuals();
    updateCanvasAspectRatio();

    // Start with clean empty state (0 videos by default)
    renderClipsList();
});
