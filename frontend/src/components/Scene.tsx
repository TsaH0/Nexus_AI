import { Canvas, useFrame } from '@react-three/fiber';
import { Stars, Float } from '@react-three/drei';
import { useRef } from 'react';
import * as THREE from 'three';

const Geometries = () => {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    if (groupRef.current) {
        groupRef.current.rotation.y += 0.001;
        // Subtle mouse interaction
        const { x, y } = state.mouse;
        groupRef.current.rotation.x = THREE.MathUtils.lerp(groupRef.current.rotation.x, y * 0.2, 0.1);
        groupRef.current.rotation.y = THREE.MathUtils.lerp(groupRef.current.rotation.y, x * 0.2, 0.1);
    }
  });

  return (
    <group ref={groupRef}>
      <Float speed={2} rotationIntensity={1.5} floatIntensity={2}>
        <mesh position={[2.5, 0, 0]}>
          <icosahedronGeometry args={[1.2, 0]} />
          <meshBasicMaterial color="white" wireframe transparent opacity={0.3} />
        </mesh>
      </Float>
      
      <Float speed={1.5} rotationIntensity={2} floatIntensity={1}>
        <mesh position={[-2.5, 1.5, -1]}>
          <octahedronGeometry args={[1, 0]} />
          <meshBasicMaterial color="white" wireframe transparent opacity={0.3} />
        </mesh>
      </Float>

       <Float speed={3} rotationIntensity={1} floatIntensity={2}>
        <mesh position={[0, -2, 1]}>
          <torusGeometry args={[0.8, 0.2, 16, 50]} />
          <meshBasicMaterial color="white" wireframe transparent opacity={0.3} />
        </mesh>
      </Float>

      {/* Center piece */}
      <mesh position={[0, 0, 0]}>
         <sphereGeometry args={[1.5, 32, 32]} />
         <meshBasicMaterial color="black" />
         <meshBasicMaterial color="white" wireframe transparent opacity={0.1} attach="material" /> 
         {/* The above doesn't work like that in JSX for two materials easily without nesting, keeping simple wireframe */}
      </mesh>
      <mesh position={[0,0,0]}>
        <sphereGeometry args={[1.48, 32, 32]} />
        <meshBasicMaterial color="black" />
      </mesh>
       <mesh position={[0,0,0]}>
        <sphereGeometry args={[1.5, 16, 16]} />
        <meshBasicMaterial color="white" wireframe transparent opacity={0.15} />
      </mesh>

    </group>
  );
};

const Scene = () => {
  return (
    <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', zIndex: 0 }}>
      <Canvas camera={{ position: [0, 0, 8] }}>
        <fog attach="fog" args={['#000000', 5, 20]} />
        <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
        <Geometries />
      </Canvas>
    </div>
  );
};

export default Scene;
