/*global window, document, gsap, bootstrap, Event, Number, parseInt, isNaN, Math, setTimeout */

(function () {
    "use strict";

    // Reuse one helper for looping through DOM query results consistently.
    function forEachNode(selector, callback) {
        Array.prototype.forEach.call(
            document.querySelectorAll(selector),
            callback
        );
    }

    // Animate the site header and the order success icon when GSAP is available.
    function animateHeader() {
        var tl;

        if (!window.gsap) {
            return;
        }

        tl = gsap.timeline();
        tl.from("header.section-header nav", {
            "duration": 0.5,
            "ease": "power2.out",
            "opacity": 0,
            "y": -100
        });

        tl.from([".nav1", ".nav2"], {
            "duration": 0.2,
            "ease": "back.out(1.7)",
            "opacity": 0,
            "stagger": 0.2,
            "y": -20
        });

        if (document.querySelector("#orderCompleteTitle")) {
            tl.from(".fa-check-circle", {
                "delay": 0.1,
                "duration": 0.7,
                "ease": "back.out(1.7)",
                "opacity": 0,
                "scale": 0
            }, ">0.1");
        }
    }

    // Keep Bootstrap dropdown menus open when users interact inside them.
    function preventDropdownClose(event) {
        if (event.target.closest(".dropdown-menu")) {
            event.stopPropagation();
        }
    }

    // Mark the selected radio wrapper as active for custom checkout controls.
    function updateRadioHighlight(input) {
        forEachNode("input[name=\"" + input.name + "\"]", function (sibling) {
            var wrap = sibling.closest(".js-check");

            if (wrap) {
                wrap.classList.remove("active");
            }
        });

        if (input.checked && input.closest(".js-check")) {
            input.closest(".js-check").classList.add("active");
        }
    }

    // Attach active-state styling to custom radio and checkbox groups.
    function initChoiceHighlights() {
        forEachNode(".js-check input[type=\"radio\"]", function (input) {
            input.addEventListener("change", function () {
                updateRadioHighlight(input);
            });
        });

        forEachNode(".js-check input[type=\"checkbox\"]", function (input) {
            input.addEventListener("change", function () {
                var container = input.closest(".js-check");

                if (container) {
                    container.classList.toggle("active", input.checked);
                }
            });
        });
    }

    // Enable Bootstrap tooltips declared with data attributes.
    function initTooltips() {
        if (!window.bootstrap || !bootstrap.Tooltip) {
            return;
        }

        forEachNode("[data-bs-toggle=\"tooltip\"]", function (tooltipTriggerEl) {
            new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Apply plus/minus quantity changes while respecting min and max limits.
    function updateQuantity(btn) {
        var current;
        var group = btn.closest(".input-group");
        var input = group
            ? group.querySelector("input[type=\"number\"]")
            : null;
        var max;
        var min;
        var next;
        var step;

        if (!input) {
            return;
        }

        step = btn.getAttribute("data-qty-btn") === "inc"
            ? 1
            : -1;
        min = parseInt(input.getAttribute("min"), 10) || 1;
        max = parseInt(input.getAttribute("max"), 10);

        if (isNaN(max)) {
            max = Infinity;
        }

        current = parseInt(input.value, 10);

        if (isNaN(current)) {
            current = min;
        }

        next = Math.min(max, Math.max(min, current + step));
        input.value = next;
        input.dispatchEvent(new Event("change", {
            "bubbles": true
        }));
    }

    // Bind quantity controls used in cart and product forms.
    function initQuantityButtons() {
        forEachNode("[data-qty-btn]", function (btn) {
            btn.addEventListener("click", function () {
                updateQuantity(btn);
            });
        });
    }

    // Refresh the cart badge and only animate it when the cart has items.
    function setCartCount(count) {
        var badge = document.getElementById("cartCount");

        if (!badge) {
            return;
        }

        badge.textContent = count;
        badge.classList.toggle("cart-badge-blink", Number(count) > 0);
    }

    // Sync the cart badge animation with the server-rendered cart count.
    function initCartBadge() {
        var badge = document.getElementById("cartCount");
        var initial;

        if (!badge) {
            return;
        }

        initial = parseInt(badge.textContent, 10) || 0;
        setCartCount(initial);
    }

    // Build an accessible show/hide password button beside password fields.
    function buildPasswordToggle(input) {
        var button = document.createElement("button");
        var icon = document.createElement("i");
        var label = document.createElement("span");
        var wrapper = document.createElement("div");

        wrapper.className = "input-group password-toggle-group";
        button.type = "button";
        button.className = "btn btn-outline-secondary password-toggle-button";
        button.setAttribute("aria-controls", input.id || "");
        button.setAttribute("aria-label", "Show password");
        button.setAttribute("aria-pressed", "false");
        button.title = "Show password";

        icon.className = "fa fa-eye";
        icon.setAttribute("aria-hidden", "true");

        label.className = "visually-hidden";
        label.textContent = "Show password";

        button.appendChild(icon);
        button.appendChild(label);

        input.setAttribute("data-password-toggle-ready", "true");
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);
        wrapper.appendChild(button);

        button.addEventListener("click", function () {
            var isHidden = input.type === "password";

            input.type = isHidden
                ? "text"
                : "password";
            icon.className = isHidden
                ? "fa fa-eye-slash"
                : "fa fa-eye";
            label.textContent = isHidden
                ? "Hide password"
                : "Show password";
            button.setAttribute("aria-label", label.textContent);
            button.setAttribute("aria-pressed", String(isHidden));
            button.title = label.textContent;
        });
    }

    // Add password toggles once so repeated initialisation cannot duplicate them.
    function initPasswordToggles() {
        forEachNode("input[type=\"password\"]", function (input) {
            if (input.getAttribute("data-password-toggle-ready") !== "true") {
                buildPasswordToggle(input);
            }
        });
    }

    // Store the current fixed-header height for CSS spacing calculations.
    function updateHeaderHeightCssVar() {
        var header = (
            document.querySelector("header.section-header.fixed-top") ||
            document.querySelector("header.section-header.d-sm-fixed-top") ||
            document.querySelector(".fixed-top") ||
            document.querySelector(".d-sm-fixed-top")
        );
        var height;

        if (!header) {
            document.documentElement.style.removeProperty("--header-height");
            return;
        }

        height = Math.ceil(header.getBoundingClientRect().height);
        document.documentElement.style.setProperty(
            "--header-height",
            height + "px"
        );
    }

    // Close Django message alerts with Bootstrap when possible, otherwise hide them.
    function closeAlert(alertEl) {
        if (window.bootstrap && bootstrap.Alert) {
            bootstrap.Alert.getOrCreateInstance(alertEl).close();
            return;
        }

        alertEl.classList.remove("show");
        setTimeout(function () {
            alertEl.remove();
        }, 150);
    }

    // Let users read messages briefly before automatically dismissing them.
    function initAlertDismissal() {
        setTimeout(function () {
            forEachNode("#message .alert", closeAlert);
        }, 3000);
    }

    // Initialise every behaviour that depends on rendered page markup.
    function initDomBehaviors() {
        initChoiceHighlights();
        initTooltips();
        initQuantityButtons();
        initCartBadge();
        initPasswordToggles();
        updateHeaderHeightCssVar();
        initAlertDismissal();
    }

    // Register startup hooks and expose the cart updater for cart-related scripts.
    animateHeader();
    document.addEventListener("click", preventDropdownClose);
    document.addEventListener("DOMContentLoaded", initDomBehaviors);
    window.addEventListener("load", updateHeaderHeightCssVar);
    window.addEventListener("resize", updateHeaderHeightCssVar);
    window.setCartCount = setCartCount;
}());
