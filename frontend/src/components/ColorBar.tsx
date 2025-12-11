interface ColorBarProps {
  width?: number;
  height?: number;
  leftLabel?: string;
  rightLabel?: string;
  showValues?: boolean;
}

const ColorBar = ({ 
  width = 300, 
  height = 40,
  leftLabel = 'Steel',
  rightLabel = 'Copper',
  showValues = true
}: ColorBarProps) => {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
      alignItems: 'center'
    }}>
      {/* Color gradient bar */}
      <div style={{
        width: `${width}px`,
        height: `${height}px`,
        background: 'linear-gradient(to right, #3b82f6, #60a5fa, #34d399, #fbbf24, #fb923c, #ef4444)',
        border: '1px solid rgba(255,255,255,0.3)',
        borderRadius: '4px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
        position: 'relative'
      }}>
        {/* Optional tick marks */}
        {showValues && (
          <>
            <div style={{
              position: 'absolute',
              bottom: '-20px',
              left: '0%',
              fontSize: '0.7rem',
              color: 'rgba(255,255,255,0.5)',
              transform: 'translateX(-50%)'
            }}>0</div>
            <div style={{
              position: 'absolute',
              bottom: '-20px',
              left: '25%',
              fontSize: '0.7rem',
              color: 'rgba(255,255,255,0.5)',
              transform: 'translateX(-50%)'
            }}>25</div>
            <div style={{
              position: 'absolute',
              bottom: '-20px',
              left: '50%',
              fontSize: '0.7rem',
              color: 'rgba(255,255,255,0.5)',
              transform: 'translateX(-50%)'
            }}>50</div>
            <div style={{
              position: 'absolute',
              bottom: '-20px',
              left: '75%',
              fontSize: '0.7rem',
              color: 'rgba(255,255,255,0.5)',
              transform: 'translateX(-50%)'
            }}>75</div>
            <div style={{
              position: 'absolute',
              bottom: '-20px',
              left: '100%',
              fontSize: '0.7rem',
              color: 'rgba(255,255,255,0.5)',
              transform: 'translateX(-50%)'
            }}>100</div>
          </>
        )}
      </div>

      {/* Labels */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        width: `${width}px`,
        marginTop: showValues ? '20px' : '0px'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '0.85rem',
          fontWeight: '600',
          color: '#3b82f6'
        }}>
          <div style={{
            width: '12px',
            height: '12px',
            background: '#3b82f6',
            border: '1px solid rgba(255,255,255,0.5)',
            borderRadius: '2px'
          }} />
          {leftLabel}
        </div>
        
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '0.85rem',
          fontWeight: '600',
          color: '#ef4444'
        }}>
          {rightLabel}
          <div style={{
            width: '12px',
            height: '12px',
            background: '#ef4444',
            border: '1px solid rgba(255,255,255,0.5)',
            borderRadius: '2px'
          }} />
        </div>
      </div>
    </div>
  );
};

export default ColorBar;
