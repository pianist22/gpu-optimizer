'use client';

import { useState } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import GpuCard from './GpuCard';
import Link from 'next/link';

export default function OptionsForm() {
  const [form, setForm] = useState({
    modelType: '',
    datasetSize: '',
    taskType: '',
    budget: '',
    region: ''
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [recommendations, setRecommendations] = useState([]);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setRecommendations([]);

    try {
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
      console.log(response);

      if (response.data && response.data.recommendations) {
        setRecommendations(response.data.recommendations);
        console.log(recommendations[0]);
      } else {
        setError('No recommendations found.');
      }
    } catch (err) {
      console.error(err);
      setError('Server error. Please try again later.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="max-w-4xl mx-auto px-6 py-16"
    >
      <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-xl p-8 space-y-8">
        <h3 className="text-2xl font-bold text-gray-800">Customize Your Optimization</h3>

        {/* Model Type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Model Type</label>
          <select
            name="modelType"
            value={form.modelType}
            onChange={handleChange}
            className="w-full border-2 border-gray-900 rounded-lg px-4 py-2 outline-none text-gray-800 focus:border-indigo-500 transition"
            required
          >
            <option value="">Select a model</option>
            <option value="GPT-3.5">GPT-3.5</option>
            <option value="Claude">Claude</option>
            <option value="Sonenet">Sonenet</option>
            <option value="Gemini Pro">Gemini Pro</option>
            <option value="Mistral-7B">Mistral-7B</option>
            <option value="LLaMA-2">LLaMA-2</option>
          </select>
        </div>

        {/* Dataset Size */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Dataset Size (in GB)</label>
          <input
            type="number"
            name="datasetSize"
            placeholder="e.g., 100"
            value={form.datasetSize}
            onChange={handleChange}
            className="w-full border-2 border-gray-900 rounded-lg px-4 py-2 outline-none text-gray-800 focus:border-indigo-500 transition"
            required
          />
        </div>

        {/* Task Type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Task Type</label>
          <div className="flex gap-6">
            {['training', 'inference'].map((type) => (
              <label
                key={type}
                className={`flex items-center gap-2 p-3 border-2 rounded-lg cursor-pointer transition-all
                  ${form.taskType === type ? 'border-indigo-600 bg-indigo-50' : 'border-gray-200 hover:border-indigo-300'}`}
              >
                <span className={form.taskType === type ? 'text-indigo-600 font-medium' : 'text-gray-600'}>
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </span>
                <input
                  type="radio"
                  name="taskType"
                  value={type}
                  checked={form.taskType === type}
                  onChange={handleChange}
                  className="sr-only"
                />
              </label>
            ))}
          </div>
        </div>

        {/* Budget */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Budget ($)</label>
          <input
            type="number"
            name="budget"
            placeholder="e.g., 200"
            value={form.budget}
            onChange={handleChange}
            className="w-full border-2 border-gray-900 rounded-lg px-4 py-2 outline-none text-gray-800 focus:border-indigo-500 transition"
            required
          />
        </div>

        {/* Preferred Region */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Preferred Region</label>
          <select
            name="region"
            value={form.region}
            onChange={handleChange}
            className="w-full border-2 border-gray-900 rounded-lg px-4 py-2 outline-none text-gray-700 focus:border-indigo-500 transition"
            required
          >
            <option value="">Select region</option>
            <option value="us-east-at-1">US East (Atlanta)</option>
            <option value="ap-south-mum-1">Asia Pacific South (Mumbai)</option>
            <option value="ap-south-del-1">Asia Pacific South (Delhi)</option>
          </select>
        </div>

        <button
          type="submit"
          className="w-full bg-indigo-600 text-white py-3 px-6 rounded-xl text-lg font-semibold shadow hover:bg-indigo-700 transition duration-300"
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Recommending...' : 'Get Recommendation'}
        </button>
      </form>

      {/* Recommendations */}
      {error && <p className="mt-4 text-red-500 text-center">{error}</p>}
      {recommendations.length > 0 && (
        <div className="mt-10 space-y-6">
          <h4 className="text-xl font-semibold text-white ">Top Recommendation:</h4>
          <GpuCard gpu={recommendations[0]} isTop={true} />
          {recommendations.length > 1 && (
            <div className="text-center mt-6">
              <Link href="/recommendations">
                <button className="bg-indigo-500 text-white px-5 py-2 rounded-xl hover:bg-indigo-600 transition">
                  View All Recommended GPUs
                </button>
              </Link>
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}
