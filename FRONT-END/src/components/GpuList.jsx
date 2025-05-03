// components/GpuList.jsx
import GpuCard from './GpuCard';
import gpuData from '../data/gpu.js';

export default function GpuList() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
      {gpuData.map((gpu, index) => (
        <GpuCard key={index} gpu={gpu} />
      ))}
    </div>
  );
}