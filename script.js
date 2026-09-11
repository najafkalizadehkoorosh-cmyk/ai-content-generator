gsap.registerPlugin(ScrollTrigger);

gsap.utils.toArray('.story').forEach((section) => {
  const copy = section.querySelector('.story-copy');
  const card = section.querySelector('.visual-card');

  gsap.from(copy, {
    x: section.classList.contains('reverse') ? 80 : -80,
    opacity: 0,
    duration: 1,
    ease: 'power3.out',
    scrollTrigger: {
      trigger: section,
      start: 'top 75%',
      end: 'top 30%',
      scrub: 1
    }
  });

  gsap.from(card, {
    y: 120,
    rotate: section.classList.contains('reverse') ? -7 : 7,
    scale: .82,
    opacity: 0,
    ease: 'power3.out',
    scrollTrigger: {
      trigger: section,
      start: 'top 90%',
      end: 'top 25%',
      scrub: 1
    }
  });

  gsap.to(card, {
    y: -35,
    ease: 'none',
    scrollTrigger: {
      trigger: section,
      start: 'top bottom',
      end: 'bottom top',
      scrub: true
    }
  });
});

gsap.to('.orb-one', {
  rotation: 360,
  scale: 1.15,
  ease: 'none',
  scrollTrigger: {
    trigger: '.hero',
    start: 'top top',
    end: 'bottom top',
    scrub: true
  }
});

gsap.to('.orb-two', {
  x: -180,
  y: 180,
  scale: .55,
  ease: 'none',
  scrollTrigger: {
    trigger: '.hero',
    start: 'top top',
    end: 'bottom top',
    scrub: true
  }
});

gsap.to('.hero-content', {
  y: -120,
  opacity: .25,
  ease: 'none',
  scrollTrigger: {
    trigger: '.hero',
    start: 'top top',
    end: 'bottom top',
    scrub: true
  }
});
