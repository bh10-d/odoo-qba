/** @odoo-module **/

(function () {
    let viewer = null;
    let bigImg = null;

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
            z-index: 999999;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: zoom-out;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.15s ease, visibility 0.15s ease;
        `;

        bigImg = document.createElement('img');
        bigImg.style.cssText = `
            max-width: 92vw;
            max-height: 92vh;
            object-fit: contain;
            border-radius: 6px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
            transition: transform 0.15s ease;
            cursor: zoom-out;
            user-select: none;
            background-color: #fff;
        `;

        viewer.appendChild(bigImg);
        document.body.appendChild(viewer);

        // Bấm vào bất kỳ đâu (ảnh hoặc ngoài ảnh) đều tắt ngay
        viewer.addEventListener('click', closeViewer);

        // Nhấn phím Escape để tắt
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && viewer.style.visibility === 'visible') {
                closeViewer();
            }
        });

        return viewer;
    }

    function openViewer(src) {
        if (!src) return;
        getOrCreateViewer();

        // Tự động chuyển URL ảnh thumbnail sang ảnh gốc độ phân giải cao image_1920
        let highResSrc = src;
        if (highResSrc.includes('/image_128')) {
            highResSrc = highResSrc.replace('/image_128', '/image_1920');
        } else if (highResSrc.includes('/image_256')) {
            highResSrc = highResSrc.replace('/image_256', '/image_1920');
        } else if (highResSrc.includes('/image_512')) {
            highResSrc = highResSrc.replace('/image_512', '/image_1920');
        }

        bigImg.src = highResSrc;
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
        }, 150);
    }

    // =========================================================================
    // XỬ LÝ SLIDER HÌNH ẢNH TRONG MODAL SO SÁNH
    // =========================================================================
    function switchSlide(slider, targetIndex) {
        if (!slider) return;
        const slides = slider.querySelectorAll('.qba-slide');
        const thumbs = slider.querySelectorAll('.qba-slider-thumb');
        const counter = slider.querySelector('.qba-slider-counter');
        const total = slides.length;
        if (total === 0) return;

        // Vòng lặp chỉ số (Wrap-around index)
        const newIndex = ((targetIndex % total) + total) % total;

        // Cập nhật trạng thái hiển thị slide ảnh chính
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

        // Cập nhật viền nổi bật cho thumbnail tương ứng
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

        // Cập nhật số thứ tự ảnh
        if (counter) {
            counter.textContent = `${newIndex + 1} / ${total}`;
        }

        slider.setAttribute('data-current-index', newIndex);
    }

    // =========================================================================
    // LẮNG NGHE SỰ KIỆN TƯƠNG TÁC (CLICK & HOVER)
    // =========================================================================
    document.addEventListener('click', function (e) {
        // 1. Bấm nút lùi ảnh (Prev)
        const prevBtn = e.target.closest('.qba-slider-prev');
        if (prevBtn) {
            e.preventDefault();
            e.stopPropagation();
            const slider = prevBtn.closest('.qba-product-slider');
            if (slider) {
                const currentIdx = parseInt(slider.getAttribute('data-current-index') || '0', 10);
                switchSlide(slider, currentIdx - 1);
            }
            return;
        }

        // 2. Bấm nút tiến ảnh (Next)
        const nextBtn = e.target.closest('.qba-slider-next');
        if (nextBtn) {
            e.preventDefault();
            e.stopPropagation();
            const slider = nextBtn.closest('.qba-product-slider');
            if (slider) {
                const currentIdx = parseInt(slider.getAttribute('data-current-index') || '0', 10);
                switchSlide(slider, currentIdx + 1);
            }
            return;
        }

        // 3. Bấm trực tiếp vào thumbnail bên dưới
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

        // 4. Bấm vào ảnh chính để phóng to (Lightbox Zoom)
        const img = e.target.closest('.qba-compare-wrapper img, .qba-lightbox-trigger, .o_kanban_record aside img');
        if (!img) return;

        // Bỏ qua nếu đang click trong viewer hoặc click thumbnail
        if (img.closest('.qba-simple-image-viewer') || img.closest('.qba-slider-thumb')) return;

        const src = img.getAttribute('data-zoom-src') || img.currentSrc || img.src;
        if (!src || src.includes('placeholder')) return;

        // Ngăn chặn sự kiện mở form chi tiết của thẻ kanban
        e.preventDefault();
        e.stopPropagation();

        openViewer(src);
    }, true);

    // Khi rê chuột qua thumbnail -> chuyển ngay ảnh xem trước
    document.addEventListener('mouseover', function (e) {
        const thumb = e.target.closest('.qba-slider-thumb');
        if (thumb) {
            const slider = thumb.closest('.qba-product-slider');
            if (slider) {
                const targetIdx = parseInt(thumb.getAttribute('data-index') || '0', 10);
                switchSlide(slider, targetIdx);
            }
        }
    });
})();
