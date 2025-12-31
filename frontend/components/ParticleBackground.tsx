import React, { useRef, useEffect } from 'react';

interface ParticleBackgroundProps {
  audioLevel: number;
  bassLevel: number;
}

// A simple particle object structure
interface Particle {
  x: number;
  y: number;
  size: number;
  speedX: number;
  speedY: number;
  baseColor: [number, number, number];
}

export const ParticleBackground: React.FC<ParticleBackgroundProps> = ({ audioLevel, bassLevel }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const particlesRef = useRef<Particle[]>([]);
  // Use refs to hold the latest prop values to avoid stale closures in the animation loop
  const audioLevelRef = useRef(audioLevel);
  audioLevelRef.current = audioLevel;
  const bassLevelRef = useRef(bassLevel);
  bassLevelRef.current = bassLevel;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;

    const createParticles = () => {
      const particleCount = 150;
      const particlesArray: Particle[] = [];
      const { width, height } = canvas;
      for (let i = 0; i < particleCount; i++) {
        particlesArray.push({
          x: Math.random() * width,
          y: Math.random() * height,
          size: Math.random() * 2 + 1,
          speedX: (Math.random() - 0.5) * 0.5,
          speedY: (Math.random() - 0.5) * 0.5,
          // Bluish/purplish colors to match the theme
          baseColor: [
            Math.floor(Math.random() * 50 + 150), 
            Math.floor(Math.random() * 50 + 100), 
            255
          ],
        });
      }
      particlesRef.current = particlesArray;
    };

    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      createParticles();
    };

    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const particles = particlesRef.current;
      const currentAudioLevel = audioLevelRef.current;
      const currentBassLevel = bassLevelRef.current;

      particles.forEach(p => {
        // Update position based on speed and audio level
        const velocityMultiplier = 1 + currentAudioLevel * 4;
        p.x += p.speedX * velocityMultiplier;
        p.y += p.speedY * velocityMultiplier;

        // Wrap particles around the screen
        if (p.x > canvas.width + p.size) p.x = -p.size;
        else if (p.x < -p.size) p.x = canvas.width + p.size;
        if (p.y > canvas.height + p.size) p.y = -p.size;
        else if (p.y < -p.size) p.y = canvas.height + p.size;
        
        // Calculate size based on bass level
        const bassEffect = 1 + currentBassLevel * 1.5;
        const finalSize = p.size * bassEffect;
        
        // Calculate opacity based on audio level
        const opacity = Math.min(1, 0.3 + currentAudioLevel * 0.7);
        const [r, g, b] = p.baseColor;
        const color = `rgba(${r}, ${g}, ${b}, ${opacity})`;

        // Draw particle
        ctx.beginPath();
        ctx.arc(p.x, p.y, finalSize, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
      });

      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      cancelAnimationFrame(animationFrameId);
    };
  }, []); // This effect should run only once to set up the animation.

  return (
    <canvas
      ref={canvasRef}
      className="absolute top-0 left-0 w-full h-full z-0 bg-gradient-to-br from-blue-950 to-black"
      style={{ touchAction: 'none' }}
    />
  );
};