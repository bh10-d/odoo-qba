/** @odoo-module **/

(function () {
    let viewer = null;
    let bigImg = null;
    let captionEl = null;
    let counterEl = null;
    let prevBtn = null;
    let nextBtn = null;
    let filmstripWrap = null;
    let filmstripEl = null;
    let galleryItems = [];
    let currentIndex = 0;
    let currentZoom = 1;
    let currentRotation = 0;
    let isDragging = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let panX = 0;
    let panY = 0;

    function getHighResUrl(src) {
        if (!src) return '';
        let highRes = src;
        if (highRes.includes('/image_128')) {
            highRes = highRes.replace('/image_128', '/image_1920');
        } else if (highRes.includes('/image_256')) {
            highRes = highRes.replace('/image_256', '/image_1920');
        } else if (highRes.includes('/image_512')) {
            highRes = highRes.replace('/image_512', '/image_1920');
        } else if (highRes.includes('/image_1024')) {
            highRes = highRes.replace('/image_1024', '/image_1920');
        }
        return highRes;
    }

    function applyTransform() {
        if (!bigImg) return;
        if (currentZoom > 1) {
            bigImg.classList.add('zoomed');
            bigImg.style.transform = `translate(${panX}px, ${panY}px) scale(${currentZoom}) rotate(${currentRotation}deg)`;
        } else {
            bigImg.classList.remove('zoomed');
            panX = 0;
            panY = 0;
            bigImg.style.transform = `rotate(${currentRotation}deg)`;
        }
    }

    function resetZoomAndRotation() {
        currentZoom = 1;
        currentRotation = 0;
        panX = 0;
        panY = 0;
        applyTransform();
    }

    // =========================================================================
    // 1. LIGHTBOX MODAL & GALLERY (LUXURY GLASSMORPHISM VIEWER)
    // =========================================================================
    function getOrCreateViewer() {
        if (viewer) return viewer;

        viewer = document.createElement('div');
        viewer.className = 'qba-lightbox-viewer';

        // 1. Top Bar
        const topBar = document.createElement('div');
        topBar.className = 'qba-lightbox-topbar';

        const titleWrap = document.createElement('div');
        titleWrap.className = 'qba-lightbox-title-wrap';

        counterEl = document.createElement('div');
        counterEl.className = 'qba-lightbox-counter';
        counterEl.textContent = '1 / 1';
        titleWrap.appendChild(counterEl);

        captionEl = document.createElement('div');
        captionEl.className = 'qba-lightbox-caption';
        captionEl.textContent = '';
        titleWrap.appendChild(captionEl);

        topBar.appendChild(titleWrap);

        // Toolbar Buttons
        const toolbar = document.createElement('div');
        toolbar.className = 'qba-lightbox-toolbar';

        // Nút Zoom In
        const btnZoomIn = document.createElement('button');
        btnZoomIn.className = 'qba-lightbox-btn';
        btnZoomIn.title = 'Phóng to (+)';
        btnZoomIn.innerHTML = '<i class="fa fa-search-plus"></i>';
        btnZoomIn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (currentZoom < 3.5) {
                currentZoom = Math.min(3.5, currentZoom + 0.35);
                applyTransform();
            }
        });
        toolbar.appendChild(btnZoomIn);

        // Nút Zoom Out
        const btnZoomOut = document.createElement('button');
        btnZoomOut.className = 'qba-lightbox-btn';
        btnZoomOut.title = 'Thu nhỏ (-)';
        btnZoomOut.innerHTML = '<i class="fa fa-search-minus"></i>';
        btnZoomOut.addEventListener('click', (e) => {
            e.stopPropagation();
            if (currentZoom > 1) {
                currentZoom = Math.max(1, currentZoom - 0.35);
                applyTransform();
            }
        });
        toolbar.appendChild(btnZoomOut);

        // Nút Xoay 90 độ
        const btnRotate = document.createElement('button');
        btnRotate.className = 'qba-lightbox-btn';
        btnRotate.title = 'Xoay ảnh 90° (R)';
        btnRotate.innerHTML = '<i class="fa fa-repeat"></i>';
        btnRotate.addEventListener('click', (e) => {
            e.stopPropagation();
            currentRotation = (currentRotation + 90) % 360;
            applyTransform();
        });
        toolbar.appendChild(btnRotate);

        // Nút Tải ảnh về
        const btnDownload = document.createElement('button');
        btnDownload.className = 'qba-lightbox-btn';
        btnDownload.title = 'Tải ảnh về máy';
        btnDownload.innerHTML = '<i class="fa fa-download"></i>';
        btnDownload.addEventListener('click', (e) => {
            e.stopPropagation();
            if (bigImg && bigImg.src) {
                const a = document.createElement('a');
                a.href = bigImg.src;
                a.download = (captionEl.textContent || 'qba_image').replace(/\s+/g, '_') + '.jpg';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }
        });
        toolbar.appendChild(btnDownload);

        // Nút Đóng
        const btnClose = document.createElement('button');
        btnClose.className = 'qba-lightbox-btn btn-close-viewer';
        btnClose.title = 'Đóng (ESC)';
        btnClose.innerHTML = '<i class="fa fa-times"></i>';
        btnClose.addEventListener('click', (e) => {
            e.stopPropagation();
            closeViewer();
        });
        toolbar.appendChild(btnClose);

        topBar.appendChild(toolbar);
        viewer.appendChild(topBar);

        // 2. Stage (Vùng hiển thị ảnh chính)
        const stage = document.createElement('div');
        stage.className = 'qba-lightbox-stage';

        bigImg = document.createElement('img');
        bigImg.className = 'qba-lightbox-main-img';
        bigImg.alt = 'Phóng to ảnh';
        bigImg.draggable = false;

        let hasDragged = false;
        let dragInitialX = 0;
        let dragInitialY = 0;

        // Tương tác kéo rê ảnh (Pan) khi đang zoom trên cả stage và bigImg
        stage.addEventListener('mousedown', (e) => {
            if (currentZoom > 1 && (e.target === bigImg || e.target === stage)) {
                isDragging = true;
                hasDragged = false;
                dragInitialX = e.clientX;
                dragInitialY = e.clientY;
                dragStartX = e.clientX - panX;
                dragStartY = e.clientY - panY;
                bigImg.style.transition = 'none';
                e.preventDefault();
            }
        });

        window.addEventListener('mousemove', (e) => {
            if (isDragging && currentZoom > 1) {
                if (Math.hypot(e.clientX - dragInitialX, e.clientY - dragInitialY) > 4) {
                    hasDragged = true;
                }
                panX = e.clientX - dragStartX;
                panY = e.clientY - dragStartY;
                applyTransform();
            }
        });

        window.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                if (bigImg) {
                    bigImg.style.transition = 'transform 0.16s ease-out';
                }
            }
        });

        // Click ảnh: chỉ toggle zoom khi KHÔNG PHẢI là thao tác drag
        bigImg.addEventListener('click', (e) => {
            e.stopPropagation();
            if (hasDragged) {
                hasDragged = false;
                return;
            }
            if (currentZoom > 1) {
                resetZoomAndRotation();
            } else {
                currentZoom = 2;
                applyTransform();
            }
        });

        // Hỗ trợ lăn con lăn chuột để zoom mượt mà (Wheel Zoom)
        stage.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY < 0 ? 0.35 : -0.35;
            const newZoom = Math.min(4, Math.max(1, Math.round((currentZoom + delta) * 100) / 100));
            if (newZoom !== currentZoom) {
                currentZoom = newZoom;
                if (currentZoom === 1) {
                    panX = 0;
                    panY = 0;
                }
                applyTransform();
            }
        }, { passive: false });

        stage.appendChild(bigImg);

        // Nút Prev
        prevBtn = document.createElement('button');
        prevBtn.className = 'qba-lightbox-nav prev';
        prevBtn.title = 'Ảnh trước (←)';
        prevBtn.innerHTML = '<i class="fa fa-chevron-left"></i>';
        prevBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            navigateGallery(-1);
        });
        stage.appendChild(prevBtn);

        // Nút Next
        nextBtn = document.createElement('button');
        nextBtn.className = 'qba-lightbox-nav next';
        nextBtn.title = 'Ảnh tiếp theo (→)';
        nextBtn.innerHTML = '<i class="fa fa-chevron-right"></i>';
        nextBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            navigateGallery(1);
        });
        stage.appendChild(nextBtn);

        // Click vùng ngoài ảnh để đóng
        stage.addEventListener('click', (e) => {
            if (e.target === stage) {
                if (hasDragged) {
                    hasDragged = false;
                    return;
                }
                closeViewer();
            }
        });

        viewer.appendChild(stage);

        // 3. Filmstrip Thumbnails ở đáy màn hình
        filmstripWrap = document.createElement('div');
        filmstripWrap.className = 'qba-lightbox-filmstrip-wrap';
        filmstripEl = document.createElement('div');
        filmstripEl.className = 'qba-lightbox-filmstrip';
        filmstripWrap.appendChild(filmstripEl);
        viewer.appendChild(filmstripWrap);

        // Bắt phím tắt
        document.addEventListener('keydown', (e) => {
            if (viewer.classList.contains('active')) {
                if (e.key === 'Escape') {
                    closeViewer();
                } else if (e.key === 'ArrowLeft') {
                    navigateGallery(-1);
                } else if (e.key === 'ArrowRight') {
                    navigateGallery(1);
                } else if (e.key === '+' || e.key === '=') {
                    if (currentZoom < 3.5) {
                        currentZoom += 0.35;
                        applyTransform();
                    }
                } else if (e.key === '-' || e.key === '_') {
                    if (currentZoom > 1) {
                        currentZoom = Math.max(1, currentZoom - 0.35);
                        applyTransform();
                    }
                } else if (e.key === 'r' || e.key === 'R') {
                    currentRotation = (currentRotation + 90) % 360;
                    applyTransform();
                }
            }
        });

        document.body.appendChild(viewer);
        return viewer;
    }

    function renderFilmstrip() {
        if (!filmstripEl || !galleryItems) return;
        filmstripEl.innerHTML = '';
        if (galleryItems.length <= 1) {
            filmstripWrap.style.display = 'none';
            return;
        }
        filmstripWrap.style.display = 'flex';

        galleryItems.forEach((item, idx) => {
            const thumbBox = document.createElement('div');
            thumbBox.className = 'qba-lightbox-filmstrip-thumb' + (idx === currentIndex ? ' active' : '');
            thumbBox.title = item.title || `Ảnh ${idx + 1}`;
            const img = document.createElement('img');
            img.src = item.src;
            img.alt = item.title || `Ảnh ${idx + 1}`;
            thumbBox.appendChild(img);

            thumbBox.addEventListener('click', (e) => {
                e.stopPropagation();
                if (currentIndex !== idx) {
                    currentIndex = idx;
                    renderCurrentGalleryItem();
                }
            });

            filmstripEl.appendChild(thumbBox);
        });

        // Cuộn filmstrip tới vị trí thumb đang active
        const activeThumb = filmstripEl.querySelector('.active');
        if (activeThumb) {
            activeThumb.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
        }
    }

    function renderCurrentGalleryItem() {
        if (!galleryItems || galleryItems.length === 0) return;
        const item = galleryItems[currentIndex];
        resetZoomAndRotation();

        bigImg.src = getHighResUrl(item.src);

        if (captionEl) {
            captionEl.textContent = item.title || '';
        }

        const hasMultiple = galleryItems.length > 1;
        if (counterEl) {
            counterEl.textContent = `${currentIndex + 1} / ${galleryItems.length}`;
            counterEl.style.display = hasMultiple ? 'inline-block' : 'none';
        }
        if (prevBtn && nextBtn) {
            prevBtn.style.display = hasMultiple ? 'flex' : 'none';
            nextBtn.style.display = hasMultiple ? 'flex' : 'none';
        }

        renderFilmstrip();
    }

    function navigateGallery(direction) {
        if (!galleryItems || galleryItems.length <= 1) return;
        currentIndex = (currentIndex + direction + galleryItems.length) % galleryItems.length;
        renderCurrentGalleryItem();
    }

    function openViewer(itemsOrSrc, titleOrIndex = 0) {
        if (!itemsOrSrc) return;
        getOrCreateViewer();
        hideHoverPreview();

        if (Array.isArray(itemsOrSrc)) {
            galleryItems = itemsOrSrc;
            currentIndex = typeof titleOrIndex === 'number' ? titleOrIndex : 0;
        } else {
            galleryItems = [{
                src: itemsOrSrc,
                title: typeof titleOrIndex === 'string' ? titleOrIndex : ''
            }];
            currentIndex = 0;
        }

        renderCurrentGalleryItem();
        viewer.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeViewer() {
        if (!viewer) return;
        viewer.classList.remove('active');
        document.body.style.overflow = '';
        setTimeout(() => {
            if (bigImg) bigImg.src = '';
            resetZoomAndRotation();
            galleryItems = [];
            currentIndex = 0;
        }, 220);
    }

    // =========================================================================
    // 2. FLOATING HOVER PREVIEW (RÊ CHUỘT PHÓNG TO NÉT CĂNG HD)
    // =========================================================================
    let hoverPreview = null;
    let hoverPreviewImg = null;
    let currentHoverTarget = null;

    function getOrCreateHoverPreview() {
        if (hoverPreview) return hoverPreview;

        hoverPreview = document.createElement('div');
        hoverPreview.className = 'qba-hover-zoom-preview';
        hoverPreview.style.cssText = `
            position: fixed;
            width: 420px;
            height: 420px;
            z-index: 2147483647;
            background: #ffffff;
            border: 2px solid #3b82f6;
            border-radius: 12px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(0, 0, 0, 0.08);
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            padding: 8px;
            pointer-events: none;
            opacity: 0;
            visibility: hidden;
            transform: scale(0.95);
            transition: opacity 0.14s ease, transform 0.14s ease, visibility 0.14s ease;
        `;

        hoverPreviewImg = document.createElement('img');
        hoverPreviewImg.style.cssText = `
            max-width: 100%;
            max-height: 100%;
            width: auto;
            height: auto;
            object-fit: contain;
            border-radius: 6px;
            user-select: none;
            background: #ffffff;
        `;

        hoverPreview.appendChild(hoverPreviewImg);
        document.body.appendChild(hoverPreview);
        return hoverPreview;
    }

    function showHoverPreview(targetEl) {
        if (!targetEl || targetEl.closest('.modal, .modal-dialog, .o_dialog')) return;
        const imgEl = targetEl.tagName === 'IMG' ? targetEl : targetEl.querySelector('img');
        if (!imgEl) return;

        let src = imgEl.getAttribute('data-zoom-src') || imgEl.currentSrc || imgEl.src;
        if (!src || src.includes('placeholder')) return;

        currentHoverTarget = targetEl;

        getOrCreateHoverPreview();
        hoverPreviewImg.src = getHighResUrl(src);

        const rect = targetEl.getBoundingClientRect();
        const previewSize = 420;
        const margin = 16;

        let left = rect.right + margin;
        if (left + previewSize > window.innerWidth - 10) {
            left = rect.left - previewSize - margin;
            if (left < 10) {
                left = Math.max(10, (window.innerWidth - previewSize) / 2);
            }
        }

        let top = rect.top - 15;
        if (top + previewSize > window.innerHeight - 10) {
            top = Math.max(10, window.innerHeight - previewSize - 10);
        }
        if (top < 10) {
            top = 10;
        }

        hoverPreview.style.left = `${left}px`;
        hoverPreview.style.top = `${top}px`;
        hoverPreview.style.opacity = '1';
        hoverPreview.style.visibility = 'visible';
        hoverPreview.style.transform = 'scale(1)';
    }

    function hideHoverPreview() {
        if (!hoverPreview) return;
        currentHoverTarget = null;
        hoverPreview.style.opacity = '0';
        hoverPreview.style.visibility = 'hidden';
        hoverPreview.style.transform = 'scale(0.95)';
    }

    // =========================================================================
    // 3. XỬ LÝ SLIDER HÌNH ẢNH TRONG MODAL SO SÁNH
    // =========================================================================
    function switchSlide(slider, targetIndex) {
        if (!slider) return;
        const slides = slider.querySelectorAll('.qba-slide');
        const thumbs = slider.querySelectorAll('.qba-slider-thumb');
        const counter = slider.querySelector('.qba-slider-counter');
        const total = slides.length;
        if (total === 0) return;

        const newIndex = ((targetIndex % total) + total) % total;

        slides.forEach((slide, idx) => {
            if (idx === newIndex) {
                slide.classList.add('active');
                slide.style.opacity = '1';
                slide.style.zIndex = '2';
                slide.style.pointerEvents = 'auto';
            } else {
                slide.classList.remove('active');
                slide.style.opacity = '0';
                slide.style.zIndex = '1';
                slide.style.pointerEvents = 'none';
            }
        });

        thumbs.forEach((thumb, idx) => {
            if (idx === newIndex) {
                thumb.classList.add('active', 'border-primary', 'shadow-sm');
                thumb.style.opacity = '1';
                thumb.style.setProperty('border', '2px solid #0d6efd', 'important');
            } else {
                thumb.classList.remove('active', 'border-primary', 'shadow-sm');
                thumb.style.opacity = '0.6';
                thumb.style.setProperty('border', '1px solid #dee2e6', 'important');
            }
        });

        if (counter) {
            counter.textContent = `${newIndex + 1} / ${total}`;
        }

        slider.setAttribute('data-current-index', newIndex);
    }

    // =========================================================================
    // 4. MỞ RỘNG / THU GỌN MÔ TẢ KỸ THUẬT (TECHNICAL SPECS) TỐI ĐA 3 DÒNG
    // =========================================================================
    function checkTechSpecsOverflow(container) {
        if (!container) return;
        const lineEl = container.querySelector('.qba-tech-specs-line');
        const toggleWrapper = container.querySelector('.qba-tech-specs-toggle-wrapper');
        if (!lineEl || !toggleWrapper) return;

        // Nếu người dùng đã mở rộng thì luôn giữ nút "Thu gọn"
        if (lineEl.classList.contains('qba-tech-specs-expanded')) {
            toggleWrapper.classList.remove('d-none');
            return;
        }

        // Kiểm tra xem nội dung có bị tràn quá 3 dòng không
        if (lineEl.clientHeight > 0) {
            const isOverflowing = (lineEl.scrollHeight - lineEl.clientHeight) > 2;
            if (isOverflowing) {
                toggleWrapper.classList.remove('d-none');
            } else {
                toggleWrapper.classList.add('d-none');
            }
        }
    }

    function updateTechSpecsToggles() {
        const containers = document.querySelectorAll('.qba-tech-specs-container');
        containers.forEach(checkTechSpecsOverflow);
    }

    let techSpecsRaf = null;
    function scheduleTechSpecsCheck() {
        if (techSpecsRaf) cancelAnimationFrame(techSpecsRaf);
        techSpecsRaf = requestAnimationFrame(updateTechSpecsToggles);
    }

    // =========================================================================
    // 5. LẮNG NGHE SỰ KIỆN TƯƠNG TÁC
    // =========================================================================
    document.addEventListener('mouseover', function (e) {
        const techContainer = e.target.closest('.qba-tech-specs-container');
        if (techContainer) {
            checkTechSpecsOverflow(techContainer);
        }

        const trigger = e.target.closest('.qba-img-hover-scale, .qba-img-hover-box img, .qba-form-avatar-zoom img');
        if (trigger) {
            if (trigger.closest('.modal, .modal-dialog, .o_dialog')) {
                return;
            }
            showHoverPreview(trigger);
            return;
        }

        const thumb = e.target.closest('.qba-slider-thumb');
        if (thumb) {
            const slider = thumb.closest('.qba-product-slider');
            if (slider) {
                const targetIdx = parseInt(thumb.getAttribute('data-index') || '0', 10);
                switchSlide(slider, targetIdx);
            }
        }
    });

    document.addEventListener('mouseout', function (e) {
        const trigger = e.target.closest('.qba-img-hover-scale, .qba-img-hover-box img, .qba-form-avatar-zoom img');
        if (trigger) {
            hideHoverPreview();
        }
    });

    window.addEventListener('scroll', function () {
        hideHoverPreview();
    }, true);

    document.addEventListener('click', function (e) {
        hideHoverPreview();

        // Nút Xem thêm / Thu gọn mô tả kỹ thuật SP (Technical Specs) trong Kanban
        const techToggle = e.target.closest('.qba-tech-specs-toggle, .qba-tech-specs-toggle-wrapper');
        if (techToggle) {
            e.preventDefault();
            e.stopPropagation();
            const container = techToggle.closest('.qba-tech-specs-container');
            if (container) {
                const lineEl = container.querySelector('.qba-tech-specs-line');
                const moreBtn = container.querySelector('.qba-btn-more');
                const lessBtn = container.querySelector('.qba-btn-less');
                if (lineEl) {
                    const isExpanded = lineEl.classList.contains('qba-tech-specs-expanded');
                    if (isExpanded) {
                        lineEl.classList.remove('qba-tech-specs-expanded');
                        lineEl.classList.add('qba-tech-specs-collapsed');
                        if (moreBtn) moreBtn.classList.remove('d-none');
                        if (lessBtn) lessBtn.classList.add('d-none');
                    } else {
                        lineEl.classList.remove('qba-tech-specs-collapsed');
                        lineEl.classList.add('qba-tech-specs-expanded');
                        if (moreBtn) moreBtn.classList.add('d-none');
                        if (lessBtn) lessBtn.classList.remove('d-none');
                    }
                }
            }
            return;
        }

        // Nút Prev slider trong modal so sánh
        const sliderPrev = e.target.closest('.qba-slider-prev');
        if (sliderPrev) {
            e.preventDefault();
            e.stopPropagation();
            const slider = sliderPrev.closest('.qba-product-slider');
            if (slider) {
                const currentIdx = parseInt(slider.getAttribute('data-current-index') || '0', 10);
                switchSlide(slider, currentIdx - 1);
            }
            return;
        }

        // Nút Next slider trong modal so sánh
        const sliderNext = e.target.closest('.qba-slider-next');
        if (sliderNext) {
            e.preventDefault();
            e.stopPropagation();
            const slider = sliderNext.closest('.qba-product-slider');
            if (slider) {
                const currentIdx = parseInt(slider.getAttribute('data-current-index') || '0', 10);
                switchSlide(slider, currentIdx + 1);
            }
            return;
        }

        // Click thumbnail slider
        const thumb = e.target.closest('.qba-slider-thumb');
        if (thumb) {
            e.preventDefault();
            e.stopPropagation();
            const slider = thumb.closest('.qba-product-slider');
            if (slider) {
                const targetIdx = parseInt(thumb.getAttribute('data-index') || '0', 10);
                switchSlide(slider, targetIdx);
            }
            return;
        }

        // =====================================================================
        // Click ảnh xem Lightbox & Toàn bộ ảnh sản phẩm / danh mục
        // =====================================================================
        // Bỏ qua nếu người dùng click vào nút chỉnh sửa / tải lên / xóa ảnh của Odoo
        if (e.target.closest('.o_select_file_button, .o_clear_file_button, button, input[type="file"], .note-popover, .o-we-toolbar')) {
            return;
        }

        const targetEl = e.target.closest(
            '.qba-compare-wrapper img, .qba-lightbox-trigger, .qba-img-hover-box, .qba-img-hover-scale, ' +
            '.o_kanban_record .qba-img-container img, .o_list_table .qba-lightbox-trigger, ' +
            '.o_list_table [name="image_128"] img, [name="extra_image_ids"] img, [name="label_image"] img, ' +
            '.qba-category-large-img img, .qba-category-measure-img img, .qba-category-html-desc img, ' +
            '.qba-extra-badge'
        );
        if (!targetEl) return;

        if (targetEl.closest('.qba-simple-image-viewer') || targetEl.closest('.qba-slider-thumb')) return;

        // Không mở lightbox nếu đang sửa nội dung trực tiếp trong trình soạn thảo HTML
        const editableArea = targetEl.closest('.odoo-editor-editable');
        if (editableArea && editableArea.getAttribute('contenteditable') === 'true') {
            return;
        }

        // Nếu click vào container hoặc badge, lấy ảnh bên trong
        let img = targetEl.tagName === 'IMG' ? targetEl : targetEl.querySelector('img');
        if (!img && targetEl.classList.contains('qba-extra-badge')) {
            const box = targetEl.closest('.qba-img-hover-box');
            if (box) img = box.querySelector('img');
        }
        if (!img) return;

        const src = img.getAttribute('data-zoom-src') || img.currentSrc || img.src;
        if (!src || src.includes('placeholder')) return;

        const title = img.getAttribute('data-title') || img.getAttribute('alt') || targetEl.getAttribute('title') || '';

        e.preventDefault();
        e.stopPropagation();

        // 0. Nếu đang ở trong Form Danh mục (.qba-fullwidth-category-form) -> Gom tất cả ảnh sơ đồ đo & ảnh danh mục để xem dạng Gallery
        const categoryForm = targetEl.closest('.qba-fullwidth-category-form');
        if (categoryForm) {
            const catImgs = Array.from(categoryForm.querySelectorAll('.qba-category-measure-img img, .qba-category-large-img img, .qba-category-html-desc img, .qba-thumb-box img')).filter(i => {
                const s = i.getAttribute('data-zoom-src') || i.currentSrc || i.src;
                return s && !s.includes('placeholder');
            });
            if (catImgs.length > 0) {
                const catName = document.querySelector('.o_form_view .oe_title h1')?.textContent?.trim() || 'Danh mục';
                const items = catImgs.map(i => {
                    let itemTitle = catName;
                    if (i.closest('.qba-category-measure-img')) {
                        itemTitle = `${catName} - Sơ đồ cách đo`;
                    } else if (i.closest('.qba-category-large-img')) {
                        itemTitle = `${catName} - Hình ảnh chính`;
                    } else if (i.closest('.qba-thumb-box')) {
                        itemTitle = `${catName} - Ảnh phụ`;
                    }
                    return {
                        src: i.getAttribute('data-zoom-src') || i.currentSrc || i.src,
                        title: itemTitle
                    };
                });
                const clickedIdx = catImgs.indexOf(img);
                openViewer(items, clickedIdx >= 0 ? clickedIdx : 0);
                return;
            }
        }

        // 1. Nếu đang ở trong tab Ảnh Phụ (extra_image_ids) -> Gom toàn bộ ảnh trong tab thành album
        const extraContainer = targetEl.closest('[name="extra_image_ids"]');
        if (extraContainer) {
            const allExtraImgs = Array.from(extraContainer.querySelectorAll('img')).filter(i => {
                const s = i.getAttribute('data-zoom-src') || i.currentSrc || i.src;
                return s && !s.includes('placeholder');
            });
            if (allExtraImgs.length > 0) {
                const items = allExtraImgs.map(i => ({
                    src: i.getAttribute('data-zoom-src') || i.currentSrc || i.src,
                    title: i.getAttribute('data-title') || i.getAttribute('alt') || i.closest('.o_kanban_record')?.querySelector('[name="name"]')?.textContent?.trim() || ''
                }));
                const clickedIdx = allExtraImgs.indexOf(img);
                openViewer(items, clickedIdx >= 0 ? clickedIdx : 0);
                return;
            }
        }

        // 2. Mở ảnh hiện tại ngay lập tức để người dùng không phải chờ
        openViewer(src, title);

        // 3. Tìm ID sản phẩm qua nhiều nguồn (data-product-id, regex trên src, hoặc URL)
        let productId = null;
        const idHolder = targetEl.closest('[data-product-id]');
        if (idHolder) {
            productId = idHolder.getAttribute('data-product-id');
        }
        if (!productId) {
            const cardEl = targetEl.closest('.qba-product-card, .o_kanban_record');
            if (cardEl) {
                productId = cardEl.getAttribute('data-product-id');
            }
        }
        if (!productId && src) {
            const m = src.match(/product\.(?:template|product)\/(\d+)/i) || src.match(/[?&]id=(\d+)/i);
            if (m && m[1]) {
                productId = m[1];
            }
        }
        if (!productId) {
            const hashM = window.location.hash.match(/id=(\d+)/i) || window.location.href.match(/product\.(?:template|product)\/(\d+)/i);
            if (hashM && hashM[1]) {
                productId = hashM[1];
            }
        }

        // 4. Nếu xác định được productId, gọi API tải danh sách toàn bộ ảnh (ảnh chính + ảnh phụ)
        if (productId) {
            const isBadgeClick = !!targetEl.closest('.qba-extra-badge');
            fetch(`/qba/product_images/${productId}`)
                .then(res => res.json())
                .then(images => {
                    if (images && images.length > 0) {
                        galleryItems = images;
                        if (isBadgeClick && images.length > 1) {
                            currentIndex = 1;
                        } else {
                            const cleanCurrent = getHighResUrl(src).split('?')[0].split('#')[0];
                            const foundIdx = images.findIndex(item => getHighResUrl(item.src).split('?')[0].split('#')[0] === cleanCurrent);
                            currentIndex = foundIdx >= 0 ? foundIdx : 0;
                        }
                        renderCurrentGalleryItem();
                    }
                })
                .catch(err => {
                    console.error("Lỗi khi tải ảnh sản phẩm:", err);
                });
        }
    }, true);

    // =========================================================================
    // 6. KHỞI TẠO VÀ THEO DÕI NỘI DUNG DOM ĐỂ CẬP NHẬT NÚT XEM THÊM
    // =========================================================================
    try {
        const techSpecsObserver = new MutationObserver(function (mutations) {
            for (let i = 0; i < mutations.length; i++) {
                if (mutations[i].addedNodes.length > 0) {
                    scheduleTechSpecsCheck();
                    break;
                }
            }
        });
        if (document.body) {
            techSpecsObserver.observe(document.body, { childList: true, subtree: true });
        } else {
            document.addEventListener('DOMContentLoaded', () => {
                techSpecsObserver.observe(document.body, { childList: true, subtree: true });
                scheduleTechSpecsCheck();
            });
        }
    } catch (err) {
        console.warn("MutationObserver init error:", err);
    }

    window.addEventListener('resize', scheduleTechSpecsCheck);
    window.addEventListener('load', scheduleTechSpecsCheck);
    scheduleTechSpecsCheck();
})();
