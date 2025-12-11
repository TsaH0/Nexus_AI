import { Canvas } from '@react-three/fiber';
import { Stars } from '@react-three/drei';

const DotsBackground = () => {
  return (
    <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', zIndex: 0 }}>
      <Canvas camera={{ position: [0, 0, 8] }}>
        <fog attach="fog" args={['#000000', 5, 20]} />
        <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
      </Canvas>
    </div>
  );
};

export default DotsBackground;
