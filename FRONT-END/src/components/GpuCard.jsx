import React from 'react';
import { BadgeCheck, XCircle, DollarSign } from 'lucide-react';

export default function GpuCard({ gpu, highlight = false }) {
  return (
    <div
      className={`rounded-2xl p-6 border shadow-md transition-transform duration-300 transform hover:scale-105 ${
        highlight ? 'bg-gradient-to-r from-indigo-100 to-indigo-50 border-indigo-500' : 'bg-white border-gray-200'
      }`}
    >
      <h2 className="text-2xl font-semibold text-gray-800 mb-2 flex items-center justify-between">
        {gpu.gpu_model}
        {gpu.is_available ? (
          <span className="text-green-600 flex items-center text-sm font-medium">
            <BadgeCheck className="w-5 h-5 mr-1" /> Available
          </span>
        ) : (
          <span className="text-red-500 flex items-center text-sm font-medium">
            <XCircle className="w-5 h-5 mr-1" /> Unavailable
          </span>
        )}
      </h2>

      <div className="mt-4 space-y-2 text-gray-700 text-base">
        <div className="flex items-center">
          <DollarSign className="w-4 h-4 mr-2 text-indigo-600" />
          <span><strong>Hourly:</strong> ${gpu.price_per_hour}</span>
        </div>
        <div className="flex items-center">
          <DollarSign className="w-4 h-4 mr-2 text-indigo-600" />
          <span><strong>Monthly:</strong> ${gpu.price_per_month}</span>
        </div>
        <div className="flex items-center">
          <DollarSign className="w-4 h-4 mr-2 text-indigo-600" />
          <span><strong>Spot Price:</strong> ${gpu.price_per_spot}</span>
        </div>
      </div>
    </div>
  );
}
