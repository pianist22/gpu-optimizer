// app/gpus/page.jsx
import GpuList from '@/components/GpuList';

export default function GpuPage() {
  return (
    <main className="min-h-screen bg-gray-50 py-10">
      <h1 className="text-3xl font-bold text-center text-gray-800 mb-8">Available GPUs</h1>
      <GpuList />
    </main>
  );
}