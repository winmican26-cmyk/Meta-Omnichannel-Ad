(function () {
  'use strict';

  var CONTACT_EMAIL = 'contact@your-domain.example';
  var LEGAL_NAME = '[LEGAL_ENTITY_NAME]';
  var YEAR = new Date().getFullYear();

  // ---------- Persistent footer ----------
  function injectFooter() {
    if (document.querySelector('.site-foot')) return;

    var footer = document.createElement('footer');
    footer.className = 'site-foot';
    footer.innerHTML = [
      '<div class="site-foot-inner">',
      '  <div class="site-foot-brand">',
      '    <a href="/" aria-label="Meta Omni Channel Ad — home"><img src="/logo-light.svg" alt="Meta Omni Channel Ad" /></a>',
      '    <p class="site-foot-copy">Cross-channel conversion optimization for Meta. Omnichannel campaigns, AI optimization, and live insights in one engine.</p>',
      '  </div>',
      '  <div class="site-foot-cols">',
      '    <div class="site-foot-col">',
      '      <h4>Company</h4>',
      '      <ul>',
      '        <li><a href="/about">About us</a></li>',
      '        <li><a href="/help">Help & Tutorial</a></li>',
      '        <li><a href="mailto:' + CONTACT_EMAIL + '">Contact</a></li>',
      '        <li><a href="/login">Sign in</a></li>',
      '        <li><a href="/login?mode=signup">Get Started</a></li>',
      '      </ul>',
      '    </div>',
      '    <div class="site-foot-col">',
      '      <h4>Legal</h4>',
      '      <ul>',
      '        <li><a href="/terms">Terms of Service</a></li>',
      '        <li><a href="/privacy-policy">Privacy Policy</a></li>',
      '        <li><a href="/#privacy">Submit DSR</a></li>',
      '        <li><a href="#" data-action="reopen-cookies">Cookie preferences</a></li>',
      '      </ul>',
      '    </div>',
      '  </div>',
      '</div>',
      '<div class="site-foot-bottom">',
      '  <span>© ' + YEAR + ' ' + LEGAL_NAME + '. All rights reserved.</span>',
      '  <span>Independent product — not affiliated with or endorsed by Meta Platforms, Inc.</span>',
      '</div>',
    ].join('');
    document.body.appendChild(footer);

    footer.addEventListener('click', function (e) {
      var target = e.target.closest('[data-action="reopen-cookies"]');
      if (!target) return;
      e.preventDefault();
      try { localStorage.removeItem('ccco.cookieConsent'); } catch (_) {}
      showCookieBanner();
    });
  }

  // ---------- Cookie consent banner with granular toggles ----------
  function showCookieBanner() {
    if (document.querySelector('.cookie-banner')) return;

    var stored = readCookieConsent();
    var prevAnalytics = stored && stored.categories && stored.categories.analytics === true;
    var prevMarketing = stored && stored.categories && stored.categories.marketing === true;

    var banner = document.createElement('div');
    banner.className = 'cookie-banner';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-live', 'polite');
    banner.setAttribute('aria-label', 'Cookie preferences');
    banner.innerHTML = [
      '<div class="cookie-banner-inner">',
      '  <p class="cookie-banner-msg">',
      '    <strong>We value your privacy.</strong> ',
      '    We use strictly necessary cookies to keep you signed in. With your consent we may also use analytics and marketing cookies. ',
      '    Toggle each category below, or use the buttons. See our <a href="/privacy-policy">Privacy Policy</a> for details.',
      '  </p>',
      '  <div class="cookie-toggles">',
      '    <label class="cookie-toggle" data-locked="true" title="Required for the service to function — cannot be disabled">',
      '      <input type="checkbox" checked disabled data-cat="necessary" />',
      '      <span class="cookie-toggle-track"></span>',
      '      <span class="cookie-toggle-label"><strong>Necessary</strong><span>Always on</span></span>',
      '    </label>',
      '    <label class="cookie-toggle">',
      '      <input type="checkbox" data-cat="analytics"' + (prevAnalytics ? ' checked' : '') + ' />',
      '      <span class="cookie-toggle-track"></span>',
      '      <span class="cookie-toggle-label"><strong>Analytics</strong><span>Usage stats</span></span>',
      '    </label>',
      '    <label class="cookie-toggle">',
      '      <input type="checkbox" data-cat="marketing"' + (prevMarketing ? ' checked' : '') + ' />',
      '      <span class="cookie-toggle-track"></span>',
      '      <span class="cookie-toggle-label"><strong>Marketing</strong><span>Personalisation</span></span>',
      '    </label>',
      '  </div>',
      '  <div class="cookie-banner-actions">',
      '    <button type="button" data-consent="necessary">Reject optional</button>',
      '    <button type="button" data-consent="save">Save preferences</button>',
      '    <button type="button" data-consent="all">Accept all</button>',
      '  </div>',
      '</div>',
    ].join('');
    document.body.appendChild(banner);

    banner.addEventListener('click', function (e) {
      var choice = e.target.getAttribute && e.target.getAttribute('data-consent');
      if (!choice) return;

      var analytics, marketing;
      if (choice === 'all') {
        analytics = true; marketing = true;
      } else if (choice === 'necessary') {
        analytics = false; marketing = false;
      } else { // save
        analytics = banner.querySelector('input[data-cat="analytics"]').checked;
        marketing = banner.querySelector('input[data-cat="marketing"]').checked;
      }

      try {
        localStorage.setItem('ccco.cookieConsent', JSON.stringify({
          choice: choice,
          categories: { necessary: true, analytics: analytics, marketing: marketing },
          timestamp: new Date().toISOString(),
          version: 2,
        }));
      } catch (_) {}
      banner.remove();
    });
  }

  function readCookieConsent() {
    try {
      var raw = localStorage.getItem('ccco.cookieConsent');
      return raw ? JSON.parse(raw) : null;
    } catch (_) { return null; }
  }

  function maybeShowCookieBanner() {
    var stored = null;
    try { stored = localStorage.getItem('ccco.cookieConsent'); } catch (_) {}
    if (!stored) showCookieBanner();
  }

  function shouldShowFooter() {
    // Footer only on the homepage and the sign-in / sign-up page.
    // Other pages (Privacy, Terms, About) have their own dedicated layouts.
    var p = window.location.pathname.replace(/\/$/, '') || '/';
    return p === '/' || p === '/login' || p === '/signup';
  }

  // ---------- First-time onboarding bubble ----------
  var ONBOARDING_KEY = 'ccco.onboardingSeen';
  var ONBOARDING_STEPS = [
    {
      title: 'Welcome 👋',
      body: 'Meta Omni Channel Ad is the engine for cross-channel Meta campaigns. Want a 30-second tour?',
      cta: 'Start tour',
      skip: 'No thanks',
    },
    {
      title: 'One campaign, every channel',
      body: 'Create CCCO ad sets that span web, app, and offline events. Meta optimises the channel mix for you on a single conversion goal.',
      cta: 'Next',
      skip: 'Skip',
    },
    {
      title: 'AI Optimizer & Creative Studio',
      body: 'Get budget splits, predicted CPA, bid caps, deep-link routing, and Meta-ready creative variants without leaving the dashboard.',
      cta: 'Next',
      skip: 'Skip',
    },
    {
      title: 'Live insights, decisions ready',
      body: 'Pull the last 30 days from Meta with one click. See channel splits, CCCO lift, and the next budget move — not just a chart.',
      cta: 'Next',
      skip: 'Skip',
    },
    {
      title: 'Privacy & data rights',
      body: 'Tokens are encrypted at rest. GDPR data subject requests are one form away. We never see your Meta password — we use Business Login.',
      cta: 'Next',
      skip: 'Skip',
    },
    {
      title: 'Ready to ship?',
      body: 'Connect your Meta Business account and create your first campaign. The full tutorial is on the Help page if you want a deeper read.',
      cta: 'Get Started →',
      ctaHref: '/login?mode=signup',
      secondary: 'Open Help',
      secondaryHref: '/help',
      skip: 'Close',
    },
  ];

  function shouldShowOnboarding() {
    var p = window.location.pathname.replace(/\/$/, '') || '/';
    if (p !== '/') return false;
    var seen = null;
    try { seen = localStorage.getItem(ONBOARDING_KEY); } catch (_) {}
    return !seen;
  }

  function markOnboardingSeen() {
    try {
      localStorage.setItem(ONBOARDING_KEY, JSON.stringify({
        timestamp: new Date().toISOString(),
        version: 1,
      }));
    } catch (_) {}
  }

  function showOnboardingBubble() {
    if (document.querySelector('.onb-bubble') || document.querySelector('.onb-panel')) return;

    var bubble = document.createElement('button');
    bubble.type = 'button';
    bubble.className = 'onb-bubble';
    bubble.setAttribute('aria-label', 'Open welcome tour');
    bubble.innerHTML = [
      '<span class="onb-bubble-pulse" aria-hidden="true"></span>',
      '<span class="onb-bubble-icon" aria-hidden="true">👋</span>',
      '<span class="onb-bubble-label">New here? Take a tour</span>',
    ].join('');
    document.body.appendChild(bubble);

    bubble.addEventListener('click', function () {
      bubble.remove();
      openOnboardingPanel(0);
    });
  }

  function openOnboardingPanel(stepIndex) {
    var existing = document.querySelector('.onb-panel');
    if (existing) existing.remove();

    var step = ONBOARDING_STEPS[stepIndex];
    var totalSteps = ONBOARDING_STEPS.length;

    var panel = document.createElement('div');
    panel.className = 'onb-panel';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-labelledby', 'onb-title');
    panel.setAttribute('aria-modal', 'false');

    var dotsHtml = '';
    for (var i = 0; i < totalSteps; i++) {
      dotsHtml += '<span class="onb-dot' + (i === stepIndex ? ' onb-dot-active' : '') + '"></span>';
    }

    var secondaryHtml = step.secondary
      ? '<a class="onb-secondary" href="' + step.secondaryHref + '">' + step.secondary + '</a>'
      : '';

    var ctaHtml = step.ctaHref
      ? '<a class="onb-cta" href="' + step.ctaHref + '" data-action="finish">' + step.cta + '</a>'
      : '<button type="button" class="onb-cta" data-action="next">' + step.cta + '</button>';

    panel.innerHTML = [
      '<div class="onb-panel-head">',
      '  <span class="onb-step-count">Step ' + (stepIndex + 1) + ' of ' + totalSteps + '</span>',
      '  <button type="button" class="onb-close" data-action="dismiss" aria-label="Close tour">✕</button>',
      '</div>',
      '<h3 id="onb-title">' + step.title + '</h3>',
      '<p>' + step.body + '</p>',
      '<div class="onb-dots">' + dotsHtml + '</div>',
      '<div class="onb-actions">',
      '  <button type="button" class="onb-skip" data-action="dismiss">' + step.skip + '</button>',
      '  ' + secondaryHtml,
      '  ' + ctaHtml,
      '</div>',
    ].join('');
    document.body.appendChild(panel);

    panel.addEventListener('click', function (e) {
      var action = e.target.getAttribute && e.target.getAttribute('data-action');
      if (action === 'next') {
        if (stepIndex + 1 < totalSteps) {
          openOnboardingPanel(stepIndex + 1);
        } else {
          markOnboardingSeen();
          panel.remove();
        }
      } else if (action === 'dismiss') {
        markOnboardingSeen();
        panel.remove();
      } else if (action === 'finish') {
        markOnboardingSeen();
        // navigation proceeds naturally because it's an <a>
      }
    });
  }

  function maybeShowOnboarding() {
    if (!shouldShowOnboarding()) return;
    // Don't pile two banners; wait until the cookie banner is dismissed.
    var hasConsent = null;
    try { hasConsent = localStorage.getItem('ccco.cookieConsent'); } catch (_) {}
    if (!hasConsent) return;
    // small delay so it feels intentional, not jumpy
    setTimeout(showOnboardingBubble, 600);
  }

  // ---------- AI chat assistant ----------
  function injectChatWidget() {
    if (document.querySelector('.chat-launcher')) return;

    var launcher = document.createElement('button');
    launcher.type = 'button';
    launcher.className = 'chat-launcher';
    launcher.setAttribute('aria-label', 'Open assistant chat');
    launcher.innerHTML = [
      '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">',
      '  <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>',
      '</svg>',
    ].join('');
    document.body.appendChild(launcher);

    var panel = document.createElement('div');
    panel.className = 'chat-panel chat-hidden';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Assistant chat');
    panel.innerHTML = [
      '<div class="chat-head">',
      '  <div class="chat-head-title">',
      '    <span class="chat-head-dot"></span>',
      '    <div>',
      '      <strong>AI Assistant</strong>',
      '      <span class="chat-head-sub">Ask about CCCO, billing, privacy, or how to get started</span>',
      '    </div>',
      '  </div>',
      '  <button type="button" class="chat-close" aria-label="Close chat">✕</button>',
      '</div>',
      '<div class="chat-log" role="log" aria-live="polite"></div>',
      '<form class="chat-form" autocomplete="off">',
      '  <input type="text" name="message" placeholder="Ask anything…" maxlength="2000" required />',
      '  <button type="submit" aria-label="Send">',
      '    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">',
      '      <line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>',
      '    </svg>',
      '  </button>',
      '</form>',
      '<p class="chat-foot">AI may be inaccurate. For account-specific issues contact <a href="mailto:support@your-domain.example">support</a>.</p>',
    ].join('');
    document.body.appendChild(panel);

    var log = panel.querySelector('.chat-log');
    var form = panel.querySelector('.chat-form');
    var input = form.querySelector('input[name="message"]');
    var closeBtn = panel.querySelector('.chat-close');

    function appendBubble(role, text, actions) {
      var wrap = document.createElement('div');
      wrap.className = 'chat-msg chat-msg-' + role;
      var bubble = document.createElement('div');
      bubble.className = 'chat-bubble';
      bubble.textContent = text;
      wrap.appendChild(bubble);
      if (actions && actions.length) {
        var row = document.createElement('div');
        row.className = 'chat-actions';
        actions.forEach(function (a) {
          if (a.href) {
            var link = document.createElement('a');
            link.href = a.href;
            link.target = a.href.indexOf('http') === 0 ? '_blank' : '_self';
            if (link.target === '_blank') link.rel = 'noopener';
            link.textContent = a.label;
            link.className = 'chat-action-btn';
            row.appendChild(link);
          } else if (a.action) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'chat-action-btn';
            btn.textContent = a.label;
            btn.setAttribute('data-action', a.action);
            row.appendChild(btn);
          }
        });
        wrap.appendChild(row);
      }
      log.appendChild(wrap);
      log.scrollTop = log.scrollHeight;
    }

    function appendTyping() {
      var wrap = document.createElement('div');
      wrap.className = 'chat-msg chat-msg-assistant chat-typing';
      wrap.innerHTML = '<div class="chat-bubble"><span></span><span></span><span></span></div>';
      log.appendChild(wrap);
      log.scrollTop = log.scrollHeight;
      return wrap;
    }

    function performLocalAction(action) {
      switch (action) {
        case 'open_dsr_form':
          window.location.href = '/#privacy';
          break;
        case 'open_signup':
          window.location.href = '/login?mode=signup';
          break;
        case 'open_login':
          window.location.href = '/login';
          break;
        case 'open_help':
          window.location.href = '/help';
          break;
      }
    }

    panel.addEventListener('click', function (e) {
      var actionBtn = e.target.closest && e.target.closest('[data-action]');
      if (actionBtn) {
        performLocalAction(actionBtn.getAttribute('data-action'));
      }
    });

    var openedOnce = false;
    function showPanel() {
      panel.classList.remove('chat-hidden');
      launcher.classList.add('chat-launcher-active');
      input.focus();
      if (!openedOnce) {
        openedOnce = true;
        appendBubble('assistant',
          "Hi! I'm the Meta Omni Channel Ad assistant. Ask me anything about getting started, campaigns, billing, or your privacy rights.",
          [
            { label: 'Help & Tutorial', action: 'open_help' },
            { label: 'Get Started', action: 'open_signup' },
          ]);
      }
    }
    function hidePanel() {
      panel.classList.add('chat-hidden');
      launcher.classList.remove('chat-launcher-active');
    }

    launcher.addEventListener('click', function () {
      if (panel.classList.contains('chat-hidden')) showPanel(); else hidePanel();
    });
    closeBtn.addEventListener('click', hidePanel);

    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      var text = input.value.trim();
      if (!text) return;
      appendBubble('user', text);
      input.value = '';
      var typing = appendTyping();
      try {
        var res = await fetch('/assistant/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text }),
        });
        var data = await res.json();
        typing.remove();
        if (res.ok) {
          appendBubble('assistant', data.message, data.actions || []);
        } else {
          appendBubble('assistant', 'Hmm, something went wrong on my end. Try again in a moment.');
        }
      } catch (_) {
        typing.remove();
        appendBubble('assistant', "I couldn't reach the server. Check your connection and try again.");
      }
    });
  }

  function init() {
    if (shouldShowFooter()) injectFooter();
    maybeShowCookieBanner();
    maybeShowOnboarding();
    injectChatWidget();

    // If the user just dismissed the cookie banner, surface the onboarding next.
    document.addEventListener('click', function (e) {
      var t = e.target;
      if (!t || !t.hasAttribute) return;
      if (t.hasAttribute('data-consent')) {
        // After cookie choice the banner removes itself; trigger onboarding shortly after.
        setTimeout(maybeShowOnboarding, 200);
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
