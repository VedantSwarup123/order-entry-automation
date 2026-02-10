import { useState, useEffect, useRef } from 'react';

export function useAnimatedCounter(target: number, duration: number = 1200): number {
  const [current, setCurrent] = useState(0);
  const startTime = useRef<number | null>(null);
  const animationFrame = useRef<number>(0);

  useEffect(() => {
    if (target === 0) {
      setCurrent(0);
      return;
    }

    startTime.current = null;

    const animate = (timestamp: number) => {
      if (!startTime.current) startTime.current = timestamp;
      const elapsed = timestamp - startTime.current;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
      setCurrent(Math.round(eased * target));

      if (progress < 1) {
        animationFrame.current = requestAnimationFrame(animate);
      }
    };

    animationFrame.current = requestAnimationFrame(animate);

    return () => cancelAnimationFrame(animationFrame.current);
  }, [target, duration]);

  return current;
}
