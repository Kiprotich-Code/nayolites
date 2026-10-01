/* ================================================================
   home.js — Nayolites College
   Vanilla. IntersectionObserver reveals, counters, sticky header,
   mobile nav. All motion respects prefers-reduced-motion.
   ================================================================ */

(() => {
  'use strict';

  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- 1. Sticky header state ---------- */
  const header = document.querySelector('[data-header]');
  if (header) {
    const onScroll = () => {
      header.classList.toggle('is-stuck', window.scrollY > 8);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  /* ---------- 2. Mobile nav toggle ---------- */
  const toggle = document.querySelector('[data-menu-toggle]');
  const menu = document.querySelector('.nav-menu');
  if (toggle && menu) {
    toggle.addEventListener('click', () => {
      const open = menu.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', String(open));
    });
    menu.querySelectorAll('a').forEach(a => {
      a.addEventListener('click', () => {
        menu.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  /* ---------- 3. Scroll reveals ---------- */
  const revealEls = document.querySelectorAll('[data-reveal]');

  if (prefersReduced) {
    revealEls.forEach(el => el.classList.add('in-view'));
  } else {
    // Group siblings for a subtle stagger
    const stagger = new Map();
    revealEls.forEach(el => {
      const parent = el.parentElement;
      const idx = stagger.get(parent) ?? 0;
      el.style.setProperty('--reveal-delay', `${Math.min(idx * 60, 360)}ms`);
      stagger.set(parent, idx + 1);
    });

    const io = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in-view');
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });

    revealEls.forEach(el => io.observe(el));
  }

  /* ---------- 4. Statement highlight trigger ---------- */
  const statement = document.querySelector('.statement');
  if (statement && !prefersReduced) {
    const sIo = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        statement.classList.add('in-view');
        sIo.disconnect();
      }
    }, { threshold: 0.35 });
    sIo.observe(statement);
  } else if (statement) {
    statement.classList.add('in-view');
  }

  /* ---------- 5. Animated counters ---------- */
  const counters = document.querySelectorAll('[data-count]');
  if (counters.length && !prefersReduced) {
    const animate = (el) => {
      const target = parseFloat(el.dataset.count);
      const suffix = el.dataset.suffix ?? '';
      const duration = 1400;
      const start = performance.now();

      const tick = (now) => {
        const t = Math.min((now - start) / duration, 1);
        // easeOutExpo
        const eased = t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
        const value = Math.round(target * eased);
        el.textContent = value.toLocaleString() + suffix;
        if (t < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    };

    const cIo = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          animate(entry.target);
          cIo.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });

    counters.forEach(el => cIo.observe(el));
  } else {
    counters.forEach(el => {
      el.textContent = parseFloat(el.dataset.count).toLocaleString() + (el.dataset.suffix ?? '');
    });
  }

  /* ---------- 6. Filmstrip — drag to scroll (desktop) ---------- */
  const strip = document.querySelector('[data-strip]');
  if (strip) {
    let isDown = false, startX = 0, scrollLeft = 0;

    strip.addEventListener('mousedown', (e) => {
      isDown = true;
      strip.style.cursor = 'grabbing';
      startX = e.pageX - strip.offsetLeft;
      scrollLeft = strip.scrollLeft;
    });
    const stop = () => { isDown = false; strip.style.cursor = ''; };
    strip.addEventListener('mouseleave', stop);
    strip.addEventListener('mouseup', stop);
    strip.addEventListener('mousemove', (e) => {
      if (!isDown) return;
      e.preventDefault();
      const walk = (e.pageX - strip.offsetLeft - startX) * 1.4;
      strip.scrollLeft = scrollLeft - walk;
    });
  }

  /* ---------- 7. Marquee — pause on hover (a11y courtesy) ---------- */
  const marquee = document.querySelector('[data-marquee]');
  if (marquee && !prefersReduced) {
    marquee.addEventListener('mouseenter', () => marquee.style.animationPlayState = 'paused');
    marquee.addEventListener('mouseleave', () => marquee.style.animationPlayState = 'running');
  }

})();