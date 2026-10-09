/** @odoo-module **/

(function () {
    let viewer = null;
    let bigImg = null;
    let captionEl = null;
    let counterEl = null;
    let prevBtn = null;
    let nextBtn = null;
    let galleryItems = [];
    let currentIndex = 0;
    let isZoomed = false;

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

    // =========================================================================
    // 1. LIGHTBOX MODAL & GALLERY (CLICK VÀO ẢNH ĐỂ XEM ĐẦY ĐỦ CÁC HÌNH ẢNH)
    // =========================================================================
    function getOrCreateViewer() {
        if (viewer) return viewer;

        viewer = document.createElement('div');
        viewer.className = 'qba-simple-image-viewer';
        viewer.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: 2147483640;
            background: rgba(0, 0, 0, 0.88);
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.18s ease, visibility 0.18s ease;
            backdrop-filter: blur(4px);
        `;

        const imgContainer = document.createElement('div');
        imgContainer.className = 'qba-viewer-img-container';
        imgContainer.style.cssText = `
            position: relative;
            max-width: 90vw;
            max-height: 85vh;
            display: flex;
            align-items: center;
            justify-content: center;
        `;

        bigImg = document.createElement('img');
        bigImg.style.cssText = `
            max-width: 90vw;
            max-height: 85vh;
            object-fit: contain;
            border-radius: 8px;
            box-shadow: 0 12px 48px rgba(0, 0, 0, 0.75);
            transition: transform 0.2s cubic-bezier(0.2, 0, 0.2, 1);
            cursor: zoom-in;
            user-select: none;
            background-color: #ffffff;
            transform-origin: center center;
        `;
        imgContainer.appendChild(bigImg);
        viewer.appendChild(imgContainer);

        // Chú thích ảnh (Caption)
        captionEl = document.createElement('div');
        captionEl.style.cssText = `
            position: absolute;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            color: #ffffff;
            background: rgba(0, 0, 0, 0.75);
            padding: 7px 22px;
            border-radius: 24px;
            font-size: 0.92rem;
            max-width: 80vw;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            pointer-events: none;
            display: none;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
            z-index: 10;
        `;
        viewer.appendChild(captionEl);

        // Số thứ tự ảnh (Counter: ví dụ 1 / 4)
        counterEl = document.createElement('div');
        counterEl.style.cssText = `
            position: absolute;
            top: 20px;
            left: 25px;
            color: #ffffff;
            background: rgba(0, 0, 0, 0.65);
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            pointer-events: none;
            display: none;
            border: 1px solid rgba(255, 255, 255, 0.15);
            z-index: 10;
        `;
        viewer.appendChild(counterEl);

        // Hướng dẫn phím tắt
        const tipEl = document.createElement('div');
        tipEl.style.cssText = `
            position: absolute;
            top: 20px;
            right: 75px;
            color: #ffffff;
            background: rgba(0, 0, 0, 0.6);
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.8rem;
            pointer-events: none;
            border: 1px solid rgba(255, 255, 255, 0.15);
            z-index: 10;
        `;
        tipEl.textContent = 'ESC: Đóng | Phím ← →: Chuyển ảnh | Click: Phóng to';
        viewer.appendChild(tipEl);

        // Nút đóng (X)
        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '&times;';
        closeBtn.title = 'Đóng (ESC)';
        closeBtn.style.cssText = `
            position: absolute;
            top: 16px;
            right: 20px;
            width: 38px;
            height: 38px;
            background: rgba(255, 255, 255, 0.2);
            color: #ffffff;
            border: none;
            border-radius: 50%;
            font-size: 26px;
            line-height: 1;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.15s ease;
            z-index: 11;
        `;
        closeBtn.addEventListener('mouseenter', () => closeBtn.style.background = 'rgba(255, 255, 255, 0.4)');
        closeBtn.addEventListener('mouseleave', () => closeBtn.style.background = 'rgba(255, 255, 255, 0.2)');
        closeBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            closeViewer();
        });
        viewer.appendChild(closeBtn);

        // Nút ảnh trước (Prev)
        prevBtn = document.createElement('button');
        prevBtn.innerHTML = '&#10094;';
        prevBtn.title = 'Ảnh trước (←)';
        prevBtn.style.cssText = `
            position: absolute;
            left: 20px;
            top: 50%;
            transform: translateY(-50%);
            width: 50px;
            height: 50px;
            background: rgba(0, 0, 0, 0.6);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.25);
            border-radius: 50%;
            font-size: 24px;
            cursor: pointer;
            display: none;
            align-items: center;
            justify-content: center;
            transition: background 0.15s ease, transform 0.15s ease;
            z-index: 11;
        `;
        prevBtn.addEventListener('mouseenter', () => {
            prevBtn.style.background = 'rgba(0, 0, 0, 0.9)';
            prevBtn.style.transform = 'translateY(-50%) scale(1.08)';
        });
        prevBtn.addEventListener('mouseleave', () => {
            prevBtn.style.background = 'rgba(0, 0, 0, 0.6)';
            prevBtn.style.transform = 'translateY(-50%) scale(1)';
        });
        prevBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            navigateGallery(-1);
        });
        viewer.appendChild(prevBtn);

        // Nút ảnh sau (Next)
        nextBtn = document.createElement('button');
        nextBtn.innerHTML = '&#10095;';
        nextBtn.title = 'Ảnh tiếp theo (→)';
        nextBtn.style.cssText = `
            position: absolute;
            right: 20px;
            top: 50%;
            transform: translateY(-50%);
            width: 50px;
            height: 50px;
            background: rgba(0, 0, 0, 0.6);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.25);
            border-radius: 50%;
            font-size: 24px;
            cursor: pointer;
            display: none;
            align-items: center;
            justify-content: center;
            transition: background 0.15s ease, transform 0.15s ease;
            z-index: 11;
        `;
        nextBtn.addEventListener('mouseenter', () => {
            nextBtn.style.background = 'rgba(0, 0, 0, 0.9)';
            nextBtn.style.transform = 'translateY(-50%) scale(1.08)';
        });
        nextBtn.addEventListener('mouseleave', () => {
            nextBtn.style.background = 'rgba(0, 0, 0, 0.6)';
            nextBtn.style.transform = 'translateY(-50%) scale(1)';
        });
        nextBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            navigateGallery(1);
        });
        viewer.appendChild(nextBtn);

        // Click ảnh để phóng to thu nhỏ (Zoom 2x)
        bigImg.addEventListener('click', function (e) {
            e.stopPropagation();
            isZoomed = !isZoomed;
            if (isZoomed) {
                bigImg.style.transform = 'scale(2)';
                bigImg.style.cursor = 'zoom-out';
            } else {
                bigImg.style.transform = 'scale(1)';
                bigImg.style.cursor = 'zoom-in';
            }
        });

        // Click nền tối để đóng
        viewer.addEventListener('click', function (e) {
            if (e.target === viewer || e.target === imgContainer) {
                isZoomed = false;
                bigImg.style.transform = 'scale(1)';
                closeViewer();
            }
        });

        // Bắt phím ESC, mũi tên trái / phải
        document.addEventListener('keydown', function (e) {
            if (viewer.style.visibility === 'visible') {
                if (e.key === 'Escape') {
                    isZoomed = false;
                    bigImg.style.transform = 'scale(1)';
                    closeViewer();
                } else if (e.key === 'ArrowLeft') {
                    navigateGallery(-1);
                } else if (e.key === 'ArrowRight') {
                    navigateGallery(1);
                }
            }
        });

        document.body.appendChild(viewer);
        return viewer;
    }

    function renderCurrentGalleryItem() {
        if (!galleryItems || galleryItems.length === 0) return;
        const item = galleryItems[currentIndex];
        isZoomed = false;
        bigImg.src = getHighResUrl(item.src);
        bigImg.style.transform = 'scale(1)';
        bigImg.style.cursor = 'zoom-in';

        if (captionEl) {
            captionEl.textContent = item.title || '';
            captionEl.style.display = item.title ? 'block' : 'none';
        }

        const hasMultiple = galleryItems.length > 1;
        if (counterEl) {
            counterEl.textContent = `${currentIndex + 1} / ${galleryItems.length}`;
            counterEl.style.display = hasMultiple ? 'block' : 'none';
        }
        if (prevBtn && nextBtn) {
            prevBtn.style.display = hasMultiple ? 'flex' : 'none';
            nextBtn.style.display = hasMultiple ? 'flex' : 'none';
        }
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
        viewer.style.visibility = 'visible';
        viewer.style.opacity = '1';
        document.body.style.overflow = 'hidden';
    }

    function closeViewer() {
        if (!viewer) return;
        viewer.style.opacity = '0';
        viewer.style.visibility = 'hidden';
        document.body.style.overflow = '';
        setTimeout(() => {
            if (bigImg) bigImg.src = '';
            galleryItems = [];
            currentIndex = 0;
        }, 180);
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
        if (!targetEl) return;
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
    // 4. LẮNG NGHE SỰ KIỆN TƯƠNG TÁC
    // =========================================================================
    document.addEventListener('mouseover', function (e) {
        const trigger = e.target.closest('.qba-img-hover-scale, .qba-img-hover-box img, .qba-form-avatar-zoom img');
        if (trigger) {
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
        // Click ảnh xem Lightbox & Toàn bộ ảnh sản phẩm
        // =====================================================================
        const targetEl = e.target.closest(
            '.qba-compare-wrapper img, .qba-lightbox-trigger, .qba-img-hover-box, .qba-img-hover-scale, ' +
            '.o_kanban_record .qba-img-container img, .o_list_table .qba-lightbox-trigger, ' +
            '.o_list_table [name="image_128"] img, [name="extra_image_ids"] img, [name="label_image"] img, ' +
            '.qba-extra-badge'
        );
        if (!targetEl) return;

        if (targetEl.closest('.qba-simple-image-viewer') || targetEl.closest('.qba-slider-thumb')) return;

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
})();
