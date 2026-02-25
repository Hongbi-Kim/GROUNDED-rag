import { motion } from 'motion/react';

interface WaveSpaceLogoProps {
  size?: number;
  animated?: boolean;
}

export function WaveSpaceLogo({ size = 48, animated = false }: WaveSpaceLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Background Rounded Rectangle */}
      <rect x="4" y="4" width="92" height="92" rx="18" fill="url(#spaceGradient)" />
      
      {/* Building Structure - Left Side */}
      <motion.rect
        x="20"
        y="40"
        width="8"
        height="32"
        rx="1"
        fill="rgba(255, 255, 255, 0.5)"
        animate={animated ? {
          opacity: [0.5, 0.7, 0.5],
        } : undefined}
        transition={animated ? {
          duration: 3,
          repeat: Infinity,
          ease: 'easeInOut',
        } : undefined}
      />
      
      {/* Building Structure - Center */}
      <motion.rect
        x="31"
        y="32"
        width="8"
        height="40"
        rx="1"
        fill="rgba(255, 255, 255, 0.7)"
        animate={animated ? {
          opacity: [0.7, 0.9, 0.7],
        } : undefined}
        transition={animated ? {
          duration: 2.5,
          repeat: Infinity,
          ease: 'easeInOut',
          delay: 0.3,
        } : undefined}
      />
      
      {/* Building Structure - Right Side */}
      <motion.rect
        x="42"
        y="36"
        width="8"
        height="36"
        rx="1"
        fill="rgba(255, 255, 255, 0.6)"
        animate={animated ? {
          opacity: [0.6, 0.8, 0.6],
        } : undefined}
        transition={animated ? {
          duration: 2.8,
          repeat: Infinity,
          ease: 'easeInOut',
          delay: 0.6,
        } : undefined}
      />
      
      {/* Law Book - Single Book */}
      <motion.rect
        x="58"
        y="38"
        width="18"
        height="34"
        rx="1.5"
        fill="rgba(255, 255, 255, 0.6)"
        animate={animated ? {
          opacity: [0.6, 0.8, 0.6],
        } : undefined}
        transition={animated ? {
          duration: 3.5,
          repeat: Infinity,
          ease: 'easeInOut',
          delay: 0.9,
        } : undefined}
      />
      
      {/* Law Book Spine Detail */}
      <rect x="72" y="38" width="2" height="34" fill="rgba(0, 0, 0, 0.15)" />
      
      {/* Law Article Lines - Extended Through Design */}
      <line x1="15" y1="45" x2="85" y2="45" stroke="#2563eb" strokeWidth="1" />
      <line x1="15" y1="52" x2="85" y2="52" stroke="#3b82f6" strokeWidth="1" />
      <line x1="15" y1="59" x2="85" y2="59" stroke="#2563eb" strokeWidth="1" />
      <line x1="15" y1="66" x2="85" y2="66" stroke="#3b82f6" strokeWidth="1" />
      
      {/* Foundation Line */}
      <rect x="18" y="72" width="64" height="3" rx="1" fill="rgba(255, 255, 255, 0.85)" />
      
      {/* Decorative Corner Elements */}
      <circle cx="16" cy="16" r="2" fill="rgba(255, 255, 255, 0.5)" />
      <circle cx="84" cy="84" r="2" fill="rgba(255, 255, 255, 0.5)" />
      
      {/* Gradient Definition */}
      <defs>
        <linearGradient id="spaceGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#2a2a2a" />
          <stop offset="50%" stopColor="#3a3a3a" />
          <stop offset="100%" stopColor="#4a4a4a" />
        </linearGradient>
      </defs>
    </svg>
  );
}
