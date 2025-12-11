import { useRef, useEffect, useState } from 'react';

const VideoBackground = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoError, setVideoError] = useState(false);

  useEffect(() => {
    // Attempt to play video when component mounts
    if (videoRef.current) {
      videoRef.current.play().catch((err) => {
        console.log('Video autoplay failed:', err);
        setVideoError(true);
      });
    }
  }, []);

  return (
    <div style={{ 
      position: 'fixed', 
      top: 0, 
      left: 0, 
      width: '100%', 
      height: '100%', 
      zIndex: 0,
      overflow: 'hidden',
      background: videoError 
        ? 'linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #0a0a0a 100%)' 
        : 'black'
    }}>
      {!videoError && (
        <video
          ref={videoRef}
          autoPlay
          loop
          muted
          playsInline
          onError={() => setVideoError(true)}
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            minWidth: '100%',
            minHeight: '100%',
            width: 'auto',
            height: 'auto',
            transform: 'translate(-50%, -50%)',
            objectFit: 'cover',
            opacity: 0.4,
          }}
        >
          {/* Try multiple video sources for better compatibility */}
          <source 
            src="https://github.com/TsaH0/spectral/raw/refs/heads/main/Spectral_Imaging_of_Tower_Materials.mp4" 
            type="video/mp4" 
          />
          Your browser does not support the video tag.
        </video>
      )}
      {/* Animated gradient fallback when video fails */}
      {videoError && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '200%',
          height: '200%',
          background: 'radial-gradient(ellipse at center, rgba(60,60,100,0.3) 0%, transparent 70%)',
          animation: 'pulse-bg 8s ease-in-out infinite',
        }} />
      )}
      {/* Dark overlay to ensure text readability */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        background: 'rgba(0, 0, 0, 0.5)',
        pointerEvents: 'none'
      }} />
      <style>{`
        @keyframes pulse-bg {
          0%, 100% { opacity: 0.3; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(1.1); }
        }
      `}</style>
    </div>
  );
};

export default VideoBackground;
