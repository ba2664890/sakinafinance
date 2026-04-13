(function (window, document) {
    'use strict';

    var STORAGE_KEY = 'sf_cookie_preferences_v1';
    var CONSENT_COOKIE_NAME = 'sf_cookie_consent';
    var ONE_YEAR_IN_SECONDS = 60 * 60 * 24 * 365;

    function defaultConsent() {
        return {
            essential: true,
            analytics: false,
            marketing: false,
            updatedAt: null,
        };
    }

    function normalizeConsent(value) {
        var consent = defaultConsent();
        if (!value || typeof value !== 'object') {
            return consent;
        }

        consent.analytics = Boolean(value.analytics);
        consent.marketing = Boolean(value.marketing);
        consent.updatedAt = value.updatedAt || null;
        return consent;
    }

    function parseJson(raw) {
        if (!raw) {
            return null;
        }

        try {
            return JSON.parse(raw);
        } catch (error) {
            return null;
        }
    }

    function escapeRegex(value) {
        return String(value || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    function getCookie(name) {
        var safeName = escapeRegex(name);
        var pattern = new RegExp('(?:^|; )' + safeName + '=([^;]*)');
        var match = document.cookie.match(pattern);
        return match ? decodeURIComponent(match[1]) : null;
    }

    function readConsent() {
        var storageValue = null;

        try {
            storageValue = window.localStorage.getItem(STORAGE_KEY);
        } catch (error) {
            storageValue = null;
        }

        var storageConsent = parseJson(storageValue);
        if (storageConsent) {
            return normalizeConsent(storageConsent);
        }

        var cookieConsent = parseJson(getCookie(CONSENT_COOKIE_NAME));
        if (cookieConsent) {
            return normalizeConsent(cookieConsent);
        }

        return defaultConsent();
    }

    function hasDecision(consent) {
        return Boolean(consent && consent.updatedAt);
    }

    function persistConsent(consent) {
        var normalized = normalizeConsent(consent);
        if (!normalized.updatedAt) {
            normalized.updatedAt = new Date().toISOString();
        }

        var serialized = JSON.stringify(normalized);

        try {
            window.localStorage.setItem(STORAGE_KEY, serialized);
        } catch (error) {
            // Storage can be blocked by browser settings; cookie remains fallback.
        }

        document.cookie = CONSENT_COOKIE_NAME + '=' + encodeURIComponent(serialized) + '; path=/; max-age=' + ONE_YEAR_IN_SECONDS + '; SameSite=Lax';
        updateBannerVisibility(normalized);

        window.dispatchEvent(new CustomEvent('sf:cookie-consent:changed', { detail: normalized }));
        return normalized;
    }

    function updateBannerVisibility(consent) {
        var banner = document.getElementById('cookie-consent-banner');
        if (!banner) {
            return;
        }

        if (hasDecision(consent)) {
            banner.classList.add('d-none');
            return;
        }

        banner.classList.remove('d-none');
    }

    function acceptAll() {
        return persistConsent({
            essential: true,
            analytics: true,
            marketing: true,
            updatedAt: new Date().toISOString(),
        });
    }

    function rejectNonEssential() {
        return persistConsent({
            essential: true,
            analytics: false,
            marketing: false,
            updatedAt: new Date().toISOString(),
        });
    }

    function saveCustom(analytics, marketing) {
        return persistConsent({
            essential: true,
            analytics: Boolean(analytics),
            marketing: Boolean(marketing),
            updatedAt: new Date().toISOString(),
        });
    }

    function bindBannerActions() {
        var banner = document.getElementById('cookie-consent-banner');
        if (!banner) {
            return;
        }

        var acceptButton = banner.querySelector('[data-cookie-action="accept-all"]');
        var rejectButton = banner.querySelector('[data-cookie-action="reject-non-essential"]');

        if (acceptButton) {
            acceptButton.addEventListener('click', function () {
                acceptAll();
            });
        }

        if (rejectButton) {
            rejectButton.addEventListener('click', function () {
                rejectNonEssential();
            });
        }
    }

    function setPreferencesStatus(type, message) {
        var alert = document.getElementById('cookie-preferences-status');
        if (!alert) {
            return;
        }

        alert.className = 'alert alert-' + type + ' mt-3 mb-0';
        alert.textContent = message;
        alert.classList.remove('d-none');
    }

    function hydratePreferencesForm(consent) {
        var analyticsInput = document.getElementById('consent-analytics');
        var marketingInput = document.getElementById('consent-marketing');

        if (analyticsInput) {
            analyticsInput.checked = Boolean(consent.analytics);
        }

        if (marketingInput) {
            marketingInput.checked = Boolean(consent.marketing);
        }
    }

    function bindPreferencesForm() {
        var form = document.getElementById('cookie-preferences-form');
        if (!form) {
            return;
        }

        hydratePreferencesForm(readConsent());

        var analyticsInput = document.getElementById('consent-analytics');
        var marketingInput = document.getElementById('consent-marketing');

        form.addEventListener('submit', function (event) {
            event.preventDefault();

            saveCustom(
                analyticsInput ? analyticsInput.checked : false,
                marketingInput ? marketingInput.checked : false
            );

            setPreferencesStatus('success', 'Vos préférences cookies ont été enregistrées.');
        });

        var acceptAllButton = document.getElementById('cookie-accept-all');
        if (acceptAllButton) {
            acceptAllButton.addEventListener('click', function () {
                acceptAll();
                hydratePreferencesForm(readConsent());
                setPreferencesStatus('success', 'Tous les cookies ont été activés.');
            });
        }

        var rejectOptionalButton = document.getElementById('cookie-reject-optional');
        if (rejectOptionalButton) {
            rejectOptionalButton.addEventListener('click', function () {
                rejectNonEssential();
                hydratePreferencesForm(readConsent());
                setPreferencesStatus('info', 'Les cookies non essentiels ont été désactivés.');
            });
        }
    }

    function initializeCookieConsent() {
        var consent = readConsent();
        updateBannerVisibility(consent);
        bindBannerActions();
        bindPreferencesForm();
    }

    window.SFCookieConsent = {
        getConsent: readConsent,
        hasDecision: function () {
            return hasDecision(readConsent());
        },
        acceptAll: acceptAll,
        rejectNonEssential: rejectNonEssential,
        saveCustom: saveCustom,
    };

    document.addEventListener('DOMContentLoaded', initializeCookieConsent);
})(window, document);
