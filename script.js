gsap.registerPlugin(ScrollTrigger);

const progress = document.querySelector('.progress span');
const hero = document.querySelector('.hero');

// Page progress
ScrollTrigger.create({
  trigger: document.body,
  start: 'top top',
  end: 'bottom bottom',
  onUpdate: self => gsap.set(progress, { scaleX: self.progress })
});

// Hero: the artwork drifts while the headline leaves the scene.
gsap.to('.hero-content', {
  y: -170,
  opacity: .12,
  ease: 'none',
  scrollTrigger: { trigger: hero, start: 'top top', end: 'bottom top', scrub: 1 }
});

gsap.to('.hero-art', {
  y: -90,
  rotate: 5,
  scale: 1.08,
  ease: 'none',
  scrollTrigger: { trigger: hero, start: 'top top', end: 'bottom top', scrub: 1 }
});

gsap.to('.orbit-a', {
  rotate: 180,
  scale: 1.2,
  ease: 'none',
  scrollTrigger: { trigger: hero, start: 'top top', end: 'bottom top', scrub: true }
});

gsap.to('.orbit-b', {
  x: -180,
  y: 130,
  ease: 'none',
  scrollTrigger: { trigger: hero, start: 'top top', end: 'bottom top', scrub: true }
});

// Intro reveal
 gsap.from('.intro-copy, .intro-text', {
  y: 80,
  opacity: 0,
  stagger: .15,
  scrollTrigger: { trigger: '.intro', start: 'top 70%', end: 'top 30%', scrub: 1 }
});

// Gallery cards: scale + subtle horizontal drift.
gsap.utils.toArray('.gallery-card').forEach((card, i) => {
  gsap.fromTo(card,
    { y: 100, scale: .88, opacity: 0 },
    {
      y: 0, scale: 1, opacity: 1, ease: 'power3.out',
      scrollTrigger: { trigger: card, start: 'top 92%', end: 'top 55%', scrub: 1 }
    }
  );
  gsap.to(card, {
    backgroundPosition: `${50 + (i % 2 ? -8 : 8)}% ${50 + i * 3}%`,
    ease: 'none',
    scrollTrigger: { trigger: card, start: 'top bottom', end: 'bottom top', scrub: true }
  });
});

// Pinned process sequence. ScrollTrigger supports pin + scrub for this style of scrollytelling.
const process = gsap.timeline({
  scrollTrigger: {
    trigger: '.showcase',
    start: 'top top',
    end: 'bottom bottom',
    scrub: 1,
    pin: '.scene-window',
    anticipatePin: 1
  }
});

process
  .to('.scene-1', { opacity: 1, scale: 1, duration: 1 })
  .to('.scene-1', { opacity: 0, scale: 1.12, duration: 1 })
  .to('.scene-2', { opacity: 1, scale: 1, duration: 1 }, '<')
  .to('.scene-2', { opacity: 0, scale: .88, duration: 1 })
  .to('.scene-3', { opacity: 1, scale: 1, duration: 1 }, '<');

// Manifesto entrance
 gsap.from('.manifesto-word', {
  y: 180,
  opacity: 0,
  skewY: 7,
  scrollTrigger: { trigger: '.manifesto', start: 'top 75%', end: 'top 25%', scrub: 1 }
});

gsap.from('.manifesto-side', {
  x: 100,
  opacity: 0,
  scrollTrigger: { trigger: '.manifesto', start: 'top 65%', end: 'top 30%', scrub: 1 }
});

// Contact glow follows the scroll slightly.
gsap.to('.contact-glow', {
  x: -220,
  y: -100,
  scale: 1.3,
  ease: 'none',
  scrollTrigger: { trigger: '.contact', start: 'top bottom', end: 'bottom top', scrub: true }
});

// Magnetic-ish hover movement for desktop buttons.
document.querySelectorAll('.hero-button, .contact-button, .menu-pill').forEach(button => {
  button.addEventListener('pointermove', e => {
    const r = button.getBoundingClientRect();
    const x = (e.clientX - r.left - r.width / 2) * .12;
    const y = (e.clientY - r.top - r.height / 2) * .12;
    gsap.to(button, { x, y, duration: .25, overwrite: true });
  });
  button.addEventListener('pointerleave', () => gsap.to(button, { x: 0, y: 0, duration: .4 }));
});

// Refresh after images/fonts have settled.
window.addEventListener('load', () => ScrollTrigger.refresh());
