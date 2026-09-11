gsap.registerPlugin(ScrollTrigger);
gsap.config({ autoSleep: 60, force3D: true });

const progress = document.querySelector('.progress span');
const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

ScrollTrigger.create({
  trigger: document.body,
  start: 'top top',
  end: 'bottom bottom',
  onUpdate: self => gsap.set(progress, { scaleX: self.progress })
});

if (!prefersReduced) {
  // HERO — layered movement: text, artwork and orbits all move differently.
  const hero = document.querySelector('.hero');
  gsap.timeline({
    scrollTrigger: { trigger: hero, start: 'top top', end: 'bottom top', scrub: 1 }
  })
    .to('.hero-content', { y: -150, opacity: .08, duration: 1 }, 0)
    .to('.hero-art', { y: -85, x: -25, rotate: 4, scale: 1.1, duration: 1 }, 0)
    .to('.orbit-a', { rotate: 160, scale: 1.25, x: 40, duration: 1 }, 0)
    .to('.orbit-b', { x: -170, y: 150, scale: .65, duration: 1 }, 0);

  // INTRO — staggered reveal rather than the same slide-in everywhere.
  gsap.from('.section-number', {
    x: -80, opacity: 0, duration: 1,
    scrollTrigger: { trigger: '.intro', start: 'top 80%', end: 'top 45%', scrub: 1 }
  });
  gsap.from('.intro-copy', {
    y: 110, rotateX: 35, opacity: 0, transformOrigin: '50% 100%',
    scrollTrigger: { trigger: '.intro', start: 'top 75%', end: 'top 25%', scrub: 1 }
  });
  gsap.from('.intro-text', {
    x: 100, opacity: 0,
    scrollTrigger: { trigger: '.intro', start: 'top 65%', end: 'top 25%', scrub: 1 }
  });

  // GALLERY — every card gets a different entrance and tilt.
  const galleryEffects = [
    { y: 120, x: -80, r: -5, s: .86 },
    { y: 150, x: 80, r: 6, s: .9 },
    { y: -100, x: -70, r: 5, s: .88 },
    { y: 130, x: 70, r: -7, s: .84 }
  ];
  gsap.utils.toArray('.gallery-card').forEach((card, i) => {
    const e = galleryEffects[i % galleryEffects.length];
    gsap.fromTo(card,
      { x: e.x, y: e.y, rotate: e.r, scale: e.s, opacity: 0 },
      {
        x: 0, y: 0, rotate: 0, scale: 1, opacity: 1,
        ease: 'power3.out',
        scrollTrigger: { trigger: card, start: 'top 95%', end: 'top 52%', scrub: 1 }
      }
    );
    gsap.to(card, {
      yPercent: i % 2 ? -7 : 7,
      rotate: i % 2 ? 1.5 : -1.5,
      ease: 'none',
      scrollTrigger: { trigger: card, start: 'top bottom', end: 'bottom top', scrub: true }
    });
    gsap.from(card.querySelector('b'), {
      y: 70, opacity: 0,
      scrollTrigger: { trigger: card, start: 'top 75%', end: 'top 35%', scrub: 1 }
    });
  });

  // PROCESS — pinned cinematic scene with three completely different transformations.
  const process = gsap.timeline({
    scrollTrigger: {
      trigger: '.showcase',
      start: 'top top',
      end: 'bottom bottom',
      scrub: 1,
      pin: '.scene-window',
      anticipatePin: 1,
      fastScrollEnd: 2500
    }
  });

  process
    .set('.scene-1', { opacity: 1, scale: 1, rotation: 0 })
    .to('.scene-1', { scale: 1.16, xPercent: -7, rotation: -2, duration: 1.2 })
    .to('.scene-1', { opacity: 0, xPercent: -18, rotation: -7, duration: .8 })
    .fromTo('.scene-2',
      { opacity: 0, scale: .72, xPercent: 18, rotation: 8 },
      { opacity: 1, scale: 1, xPercent: 0, rotation: 0, duration: 1 }, '<'
    )
    .to('.scene-2', { scale: 1.2, yPercent: -6, rotation: 3, duration: 1.1 })
    .to('.scene-2', { opacity: 0, scale: .78, xPercent: -16, rotation: -8, duration: .8 })
    .fromTo('.scene-3',
      { opacity: 0, scale: 1.3, yPercent: 12, rotation: -6 },
      { opacity: 1, scale: 1, yPercent: 0, rotation: 0, duration: 1 }, '<'
    )
    .to('.scene-3', { scale: .94, xPercent: 5, rotation: 2, duration: 1 });

  // Manifesto — giant type sweeps across instead of moving vertically.
  gsap.from('.manifesto-word', {
    xPercent: -35, scale: .75, rotate: -5, opacity: 0,
    scrollTrigger: { trigger: '.manifesto', start: 'top 85%', end: 'top 20%', scrub: 1 }
  });
  gsap.from('.manifesto-side', {
    y: 120, rotate: 4, opacity: 0,
    scrollTrigger: { trigger: '.manifesto', start: 'top 65%', end: 'top 25%', scrub: 1 }
  });

  // Contact — glow travels in a different direction.
  gsap.to('.contact-glow', {
    x: -240, y: -120, scale: 1.35, rotation: 25, ease: 'none',
    scrollTrigger: { trigger: '.contact', start: 'top bottom', end: 'bottom top', scrub: true }
  });

  // Lightweight magnetic hover on desktop only.
  if (!ScrollTrigger.isTouch) {
    document.querySelectorAll('.hero-button, .contact-button, .menu-pill').forEach(button => {
      button.addEventListener('pointermove', e => {
        const r = button.getBoundingClientRect();
        gsap.to(button, {
          x: (e.clientX - r.left - r.width / 2) * .12,
          y: (e.clientY - r.top - r.height / 2) * .12,
          duration: .2, overwrite: true
        });
      });
      button.addEventListener('pointerleave', () => gsap.to(button, { x: 0, y: 0, duration: .35 }));
    });
  }
}

window.addEventListener('load', () => ScrollTrigger.refresh(), { once: true });
