// Custom JavaScript for Korgen e-commerce template

// GSAP header animation (requires GSAP to be loaded before this script)
if (window.gsap) {
    const tl = gsap.timeline();
    tl.from("header.section-header nav", {
        y: -100,
        duration: 0.5,
        opacity: 0,
        ease: "power2.out"
    });

    // Animate header child groups sequentially
    tl.from([".nav1", ".nav2"], {
        y: -20,
        opacity: 0,
        duration: 0.2,
        stagger: 0.2,
        ease: "back.out(1.7)"
    });

    // After nav finishes, animate the order-complete check if present
    if (document.querySelector('#orderCompleteTitle')) {
        tl.from(".fa-check-circle", {
            scale: 0,
            opacity: 0,
            duration: 0.7,
            ease: "back.out(1.7)",
            delay: 0.1
        }, ">0.1");
    }
}


// jquery ready start (guarded so the rest of the script still runs without jQuery)
if (window.jQuery) {
    $(document).ready(function() {
        // jQuery code


        /* ///////////////////////////////////////

        THESE FOLLOWING SCRIPTS ONLY FOR BASIC USAGE, 
        For sliders, interactions and other

        */ ///////////////////////////////////////
        

        //////////////////////// Prevent closing from click inside dropdown
        $(document).on('click', '.dropdown-menu', function (e) {
          e.stopPropagation();
        });

        // Radio group highlighting (.js-check wrapper)
        document.querySelectorAll('.js-check input[type="radio"]').forEach(function (input) {
            input.addEventListener('change', function () {
                var name = input.name;
                document.querySelectorAll('input[name="' + name + '"]').forEach(function (sibling) {
                    var wrap = sibling.closest('.js-check');
                    if (wrap) wrap.classList.remove('active');
                });
                var container = input.closest('.js-check');
                if (container && input.checked) container.classList.add('active');
            });
        });

        // Checkbox highlighting
        document.querySelectorAll('.js-check input[type="checkbox"]').forEach(function (input) {
            input.addEventListener('change', function () {
                var container = input.closest('.js-check');
                if (!container) return;
                container.classList.toggle('active', input.checked);
            });
        });

        // Bootstrap tooltip init
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.forEach(function (tooltipTriggerEl) {
            new bootstrap.Tooltip(tooltipTriggerEl);
        });

        // Quantity buttons
        document.querySelectorAll('[data-qty-btn]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var input = btn.closest('.input-group')?.querySelector('input[type="number"]');
                if (!input) return;

                var step = btn.dataset.qtyBtn === 'inc' ? 1 : -1;
                var min = parseInt(input.getAttribute('min'), 10) || 1;
                var max = parseInt(input.getAttribute('max'), 10);
                if (isNaN(max)) max = Infinity;

                var current = parseInt(input.value, 10);
                if (isNaN(current)) current = min;

                var next = Math.min(max, Math.max(min, current + step));
                input.value = next;
                input.dispatchEvent(new Event('change', { bubbles: true }));
            });
        });
    });
}

// Update cart badge count and blink when there are items
function setCartCount(count) {
    const badge = document.getElementById('cartCount');
    if (!badge) return;

    badge.textContent = count;
    badge.classList.toggle('cart-badge-blink', Number(count) > 0);
}

// Keep the blink state in sync with whatever count is already rendered
document.addEventListener('DOMContentLoaded', () => {
    const badge = document.getElementById('cartCount');
    if (!badge) return;
    const initial = parseInt(badge.textContent, 10) || 0;
    setCartCount(initial);
});

// Expose globally so other scripts (or console) can update the count
window.setCartCount = setCartCount;


/* Responsive helper: set CSS variable --header-height to actual header height
   when the header is fixed. Works for either `.d-sm-fixed-top` (sm+ only)
   or the standard `.fixed-top` utility. This lets the CSS fallback push
   `main` down without hardcoding a value. */
function updateHeaderHeightCSSVar() {
    const header =
        document.querySelector('header.section-header.fixed-top') ||
        document.querySelector('header.section-header.d-sm-fixed-top') ||
        document.querySelector('.fixed-top') ||
        document.querySelector('.d-sm-fixed-top');

    // If there's no fixed header, clear the variable.
    if (!header) {
        document.documentElement.style.removeProperty('--header-height');
        return;
    }
    const h = Math.ceil(header.getBoundingClientRect().height);
    document.documentElement.style.setProperty('--header-height', h + 'px');
}

window.addEventListener('load', updateHeaderHeightCSSVar);
window.addEventListener('resize', updateHeaderHeightCSSVar);
document.addEventListener('DOMContentLoaded', updateHeaderHeightCSSVar);
