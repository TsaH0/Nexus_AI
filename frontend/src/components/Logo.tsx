import logoGif from '../_.gif';

interface LogoProps {
  size?: number;
  showText?: boolean;
}

const Logo = ({ size = 40, showText = true }: LogoProps) => {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
      <div style={{ 
        width: `${size}px`, 
        height: `${size}px`, 
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden',
        borderRadius: '4px'
      }}>
        <img 
          src={logoGif}
          alt="Nexus Logo"
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            mixBlendMode: 'screen',
            filter: 'contrast(1.2)'
          }}
        />
      </div>
      
      {showText && (
        <span style={{ 
          fontWeight: '700', 
          letterSpacing: '3px', 
          fontSize: `${size * 0.5}px`,
          color: 'white',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
        }}>
          NEXUS
        </span>
      )}
    </div>
  );
};

export default Logo;
