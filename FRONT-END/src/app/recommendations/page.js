'use client';

import React, { useEffect, useState } from 'react';
import axios from 'axios';
import GpuCard from '@/components/GpuCard'; // Make sure this is the correct path

export default function RecommendationsPage() {
  const [recommendedGpus, setRecommendedGpus] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchRecommendations = async () => {
      try {
        const form = {
          modelType: 'Mistrel-7B',         // You can replace these with real values from context or URL params
          datasetSize: 50,
          taskType: 'Training',
          budget: 10000,
          region: 'ap-south-mum-1'
        };

        const response = await axios.post(
          'http://localhost:5000/recommend',
          {
            modelType: form.modelType,
            datasetSizeGB: parseInt(form.datasetSize),
            taskType: form.taskType.charAt(0).toUpperCase() + form.taskType.slice(1),
            budget: parseFloat(form.budget),
            preferredRegion: form.region
          },
          {
            headers: {
              'Content-Type': 'application/json'
            }
          }
        );

        setRecommendedGpus(response.data);
      } catch (err) {
        console.error('Error fetching recommendations:', err);
        setError('Failed to load recommended GPUs.');
      } finally {
        setLoading(false);
      }
    };

    fetchRecommendations();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-lg text-gray-500">
        Loading recommended GPUs...
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center text-red-500">
        {error}
      </div>
    );
  }

  const otherGpus = recommendedGpus.slice(1); // All recommendations except the first one

  return (
    <div className="min-h-screen bg-gradient-to-tr from-white to-gray-100 py-12 px-6">
      <h1 className="text-3xl font-semibold text-indigo-700 text-center mb-10">
        Explore More GPU Options
      </h1>

      {otherGpus.length === 0 ? (
        <p className="text-center text-gray-600">No additional recommendations available.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {otherGpus.map((gpu, index) => (
            <GpuCard key={gpu.flavor_id || index} gpu={gpu} />
          ))}
        </div>
      )}
    </div>
  );
}
